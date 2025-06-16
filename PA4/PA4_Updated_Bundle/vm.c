#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "vm_dbg.h"

#define NOPS (16)

#define OPC(i) ((i) >> 12)
#define DR(i) (((i) >> 9) & 0x7)
#define SR1(i) (((i) >> 6) & 0x7)
#define SR2(i) ((i) & 0x7)
#define FIMM(i) ((i >> 5) & 01)
#define IMM(i) ((i) & 0x1F)
#define SEXTIMM(i) sext(IMM(i), 5)
#define FCND(i) (((i) >> 9) & 0x7)
#define POFF(i) sext((i) & 0x3F, 6)
#define POFF9(i) sext((i) & 0x1FF, 9)
#define POFF11(i) sext((i) & 0x7FF, 11)
#define FL(i) (((i) >> 11) & 1)
#define BR(i) (((i) >> 6) & 0x7)
#define TRP(i) ((i) & 0xFF)

/* New OS declarations */

// OS bookkeeping constants
#define PAGE_SIZE       (4096)  // Page size in bytes
#define OS_MEM_SIZE     (2)     // OS Region size. Also the start of the page tables' page
#define Cur_Proc_ID     (0)     // id of the current process
#define Proc_Count      (1)     // total number of processes, including ones that finished executing.
#define OS_STATUS       (2)     // Bit 0 shows whether the PCB list is full or not
#define OS_FREE_BITMAP  (3)     // Bitmap for free pages

// Process list and PCB related constants
#define PCB_SIZE  (3)  // Number of fields in a PCB
#define PID_PCB   (0)  // Holds the pid for a process
#define PC_PCB    (1)  // Value of the program counter for the process
#define PTBR_PCB  (2)  // Page table base register for the process

#define CODE_SIZE       (2)  // Number of pages for the code segment
#define HEAP_INIT_SIZE  (2)  // Number of pages for the heap segment initially

bool running = true;

typedef void (*op_ex_f)(uint16_t i);
typedef void (*trp_ex_f)();

enum { trp_offset = 0x20 };
enum regist { R0 = 0, R1, R2, R3, R4, R5, R6, R7, RPC, RCND, PTBR, RCNT };
enum flags { FP = 1 << 0, FZ = 1 << 1, FN = 1 << 2 };

uint16_t mem[UINT16_MAX] = {0};
uint16_t reg[RCNT] = {0};
uint16_t PC_START = 0x3000;

void initOS();
int createProc(char *fname, char *hname);
void loadProc(uint16_t pid);
uint16_t allocMem(uint16_t ptbr, uint16_t vpn, uint16_t read, uint16_t write);  // Can use 'bool' instead
int freeMem(uint16_t ptr, uint16_t ptbr);
static inline uint16_t mr(uint16_t address);
static inline void mw(uint16_t address, uint16_t val);
static inline void tbrk();
static inline void thalt();
static inline void tyld();
static inline void trap(uint16_t i);

static inline uint16_t sext(uint16_t n, int b) { return ((n >> (b - 1)) & 1) ? (n | (0xFFFF << b)) : n; }
static inline void uf(enum regist r) {
    if (reg[r] == 0)
        reg[RCND] = FZ;
    else if (reg[r] >> 15)
        reg[RCND] = FN;
    else
        reg[RCND] = FP;
}
static inline void add(uint16_t i)  { reg[DR(i)] = reg[SR1(i)] + (FIMM(i) ? SEXTIMM(i) : reg[SR2(i)]); uf(DR(i)); }
static inline void and(uint16_t i)  { reg[DR(i)] = reg[SR1(i)] & (FIMM(i) ? SEXTIMM(i) : reg[SR2(i)]); uf(DR(i)); }
static inline void ldi(uint16_t i)  { reg[DR(i)] = mr(mr(reg[RPC]+POFF9(i))); uf(DR(i)); }
static inline void not(uint16_t i)  { reg[DR(i)]=~reg[SR1(i)]; uf(DR(i)); }
static inline void br(uint16_t i)   { if (reg[RCND] & FCND(i)) { reg[RPC] += POFF9(i); } }
static inline void jsr(uint16_t i)  { reg[R7] = reg[RPC]; reg[RPC] = (FL(i)) ? reg[RPC] + POFF11(i) : reg[BR(i)]; }
static inline void jmp(uint16_t i)  { reg[RPC] = reg[BR(i)]; }
static inline void ld(uint16_t i)   { reg[DR(i)] = mr(reg[RPC] + POFF9(i)); uf(DR(i)); }
static inline void ldr(uint16_t i)  { reg[DR(i)] = mr(reg[SR1(i)] + POFF(i)); uf(DR(i)); }
static inline void lea(uint16_t i)  { reg[DR(i)] =reg[RPC] + POFF9(i); uf(DR(i)); }
static inline void st(uint16_t i)   { mw(reg[RPC] + POFF9(i), reg[DR(i)]); }
static inline void sti(uint16_t i)  { mw(mr(reg[RPC] + POFF9(i)), reg[DR(i)]); }
static inline void str(uint16_t i)  { mw(reg[SR1(i)] + POFF(i), reg[DR(i)]); }
static inline void rti(uint16_t i)  {} // unused
static inline void res(uint16_t i)  {} // unused
static inline void tgetc()        { reg[R0] = getchar(); }
static inline void tout()         { fprintf(stdout, "%c", (char)reg[R0]); }
static inline void tputs() {
  uint16_t *p = mem + reg[R0];
  while(*p) {
    fprintf(stdout, "%c", (char) *p);
    p++;
  }
}
static inline void tin()      { reg[R0] = getchar(); fprintf(stdout, "%c", reg[R0]); }
static inline void tputsp()   { /* Not Implemented */ }
static inline void tinu16()   { fscanf(stdin, "%hu", &reg[R0]); }
static inline void toutu16()  { fprintf(stdout, "%hu\n", reg[R0]); }

trp_ex_f trp_ex[10] = {tgetc, tout, tputs, tin, tputsp, thalt, tinu16, toutu16, tyld, tbrk};
static inline void trap(uint16_t i) { trp_ex[TRP(i) - trp_offset](); }
op_ex_f op_ex[NOPS] = {/*0*/ br, add, ld, st, jsr, and, ldr, str, rti, not, ldi, sti, jmp, res, lea, trap};

/**
  * Load an image file into memory.
  * @param fname the name of the file to load
  * @param offsets the offsets into memory to load the file
  * @param size the size of the file to load
*/
void ld_img(char *fname, uint16_t *offsets, uint16_t size) {
    FILE *in = fopen(fname, "rb");
    if (NULL == in) {
        fprintf(stderr, "Cannot open file %s.\n", fname);
        exit(1);
    }

    for (uint16_t s = 0; s < size; s += PAGE_SIZE) {
        uint16_t *p = mem + offsets[s / PAGE_SIZE];
        uint16_t writeSize = (size - s) > PAGE_SIZE ? PAGE_SIZE : (size - s);
        fread(p, sizeof(uint16_t), (writeSize), in);
    }
    
    fclose(in);
}

void run(char *code, char *heap) {
  while (running) {
    uint16_t i = mr(reg[RPC]++);
    op_ex[OPC(i)](i);
  }
}

// YOUR CODE STARTS HERE
static uint16_t get_file_size(const char *fname) {
    FILE *f = fopen(fname, "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    long bytes = ftell(f);
    fclose(f);
    return (uint16_t)(bytes / sizeof(uint16_t));
}



void initOS() {
mem[0] = 0xffff;
  mem[1] = 0x0000;
  mem[2] = 0x0000;
  mem[3] = 0b0001111111111111;
  mem[4] = 0b1111111111111111;

  return;
}
// Process functions to implement
int createProc(char *fname, char *hname) {
  uint16_t os_status = mem[2];
  if ((os_status & 0x1) == 1) {
    printf("The OS memory region is full. Cannot create a new PCB.\n");
    return 0;
  }

  uint16_t new_pid = mem[1];
 
  uint16_t pcb_addr = 12 + new_pid * 3;

  mem[pcb_addr] = new_pid;       // Initialize process id
  mem[pcb_addr + 1] = 0x3000; // Initialize PC
   uint16_t ptbr = 4096 + new_pid * 32;
  mem[pcb_addr + 2] = ptbr;      // PTBR

  int16_t c1 = allocMem(ptbr, 6, UINT16_MAX, 0);
    if (c1 < 0) {
        printf("Cannot create code segment.\n");
        return 0;
    }
    int16_t c2 = allocMem(ptbr, 7, UINT16_MAX, 0);
    if (c2 < 0) {
        freeMem(6, ptbr);
        printf("Cannot create code segment.\n");
        return 0;
    }


    int16_t h1 = allocMem(ptbr, 8, UINT16_MAX, UINT16_MAX);
    if (h1 < 0) {
        freeMem(7, ptbr);
        freeMem(6, ptbr);
        printf("Cannot create heap segment.\n");
        return 0;
    }
    int16_t h2 = allocMem(ptbr, 9, UINT16_MAX, UINT16_MAX);
    if (h2 < 0) {
        freeMem(8, ptbr);
        freeMem(7, ptbr);
        freeMem(6, ptbr);
        printf("Cannot create heap segment.\n");
        return 0;
    }

uint16_t code_offsets[2] = { (uint16_t)(c1 << 11), (uint16_t)(c2 << 11) };
uint16_t heap_offsets[2] = { (uint16_t)(h1 << 11), (uint16_t)(h2 << 11) };


uint16_t code_size  = get_file_size(fname);
uint16_t heap_size  = get_file_size(hname);


ld_img(fname, code_offsets,  code_size);
ld_img(hname, heap_offsets, heap_size);


 mem[1] += 1; 

    return 1;

  }


void loadProc(uint16_t pid) {
  uint16_t pcb_addr = 12 + pid * 3;
  uint16_t new_pc = mem[pcb_addr + 1];      
  uint16_t new_ptbr = mem[pcb_addr + 2]; 

  reg[RPC] = new_pc;
  reg[PTBR] = new_ptbr;
  mem[0] = pid; 
}
// code segmenr
 



// to allocate exactly one page frame.
// mem[ptbr + vpn]
uint16_t allocMem(uint16_t ptbr, uint16_t vpn, uint16_t read, uint16_t write) {
    uint16_t pte = mem[ptbr + vpn];
    if (pte & 0x1) { // Valid bit (bit 0) set ise
        return 0;
    }
for (uint16_t i = 3; i < 32; ++i) {
      uint16_t bit, idx;
      if (i < 16) {
          idx = 15 - i;     
          bit = (mem[3] >> idx) & 1;
      } else {
         idx = 31 - i;   
          bit = (mem[4] >> idx) & 1; // sadece en sağdaki bit 
}
    if (bit == 1) { // biti sıfırla 
//	  printf("allocMem: allocating PFN=%d\n", i);
       if (i < 16) {
            mem[3] &= ~(1 << idx);
        } else {
            mem[4] &= ~(1 << idx);
        }

        uint16_t newPTE = (i << 11); // PFN en üst 5 bit
        if (read == UINT16_MAX) {
          newPTE |= (1 << 1);
      }

      if (write == UINT16_MAX) {
       newPTE |= (1 << 2);
      }
      newPTE |= 1;
      mem[ptbr + vpn] = newPTE;
      return i;
    }
    }

  return -1;
}

int freeMem(uint16_t vpn, uint16_t ptbr) {
  uint16_t pte = mem[ptbr + vpn];
  if (!(pte & 0x1)) { // Valid bit (bit 0) set ise
      return 0;
    } else {
       uint16_t pfn = pte >> 11;
        if (pfn < 16) {
        // 15-i ters indeksleme: bitmap MSB'den tutuluyor
        mem[3] |= (1 << (15 - pfn));
    } else {
        mem[4] |= (1 << (31 - pfn));
    }
    // clear the valid bit 
     mem[ptbr + vpn] = pte & (~1);
     return 1;
    }

  return 0;
} 

// Instructions to implement
static inline void tbrk() {
  uint16_t address = reg[R0];
  uint16_t vpn = address >> 11;  // first 5 bits 
  uint16_t request = address & 0x0001;
  uint16_t read = (address >> 1) & 0x1;
  uint16_t write = (address >> 2) & 0x1;
  uint16_t ptbr = reg[PTBR];
  uint16_t current_Pid = mem[0];

  if (request == 1){
      printf("Heap increase requested by process %d.\n", current_Pid);
    // case 1
    uint16_t pte = mem[ptbr + vpn];
    if (pte & 0x1) { // Valid bit (bit 0) set ise
        printf("Cannot allocate memory for page %d of pid %d since it is already allocated.\n", vpn, current_Pid);
        return ;
    }
    // case 2 
    int16_t pfn = allocMem(ptbr, vpn, read ? UINT16_MAX : 0, write ? UINT16_MAX : 0);
    if (pfn < 0) {
      printf("Cannot allocate more space for pid %d since there is no free page frames.\n", current_Pid);
      return;
    } 
    
    }else {
      printf("Heap decrease requested by process %d.\n", current_Pid);
      if (!(mem[ptbr + vpn] & 0x1)) {
      printf("Cannot free memory of page %d of pid %d since it is not allocated.\n", vpn, current_Pid);
      return;
    }
    freeMem(vpn, ptbr);
    }


}


static inline void tyld() {
    uint16_t old = mem[0];            // aktif PID
    // Eğer sadece bir proses varsa çık
    if (mem[1] <= 1) return;

    // Sıradaki prosesi bul
    uint16_t current = (old + 1) % mem[1];
    while ((mem[12 + current*3] == 0xFFFF) && (current != old)) {
        current = (current + 1) % mem[1];
    }
    // Hiç başka proses yoksa çık
    if (current == old) return;

    // Gerçek bir switch varsa önce eski prosesi kaydet
    mem[12 + old*3 + 1] = reg[RPC];
    mem[12 + old*3 + 2] = reg[PTBR];

    // Yeni prosese geç
    reg[RPC]   = mem[12 + current*3 + 1];
    reg[PTBR]  = mem[12 + current*3 + 2];
    mem[0]     = current;

    printf("We are switching from process %d to %d.\n", old, current);
}

static inline void thalt() {
  uint16_t current = mem[0];
  uint16_t ptbr = reg[PTBR];

  // Sayfa tablolarındaki valid page'leri serbest bırak
  for (int i = 0; i < 32; i++) {
    uint16_t pte = mem[ptbr + i];
    if (pte & 0x1) {
      freeMem(i, ptbr);
    }
  }

  // PCB’yi 0xFFFF yap (terminated)
  mem[12 + current * 3] = 0xFFFF;

  // Yeni proses kalmış mı kontrol et
  uint16_t next = (current + 1) % mem[1];
  while ((mem[12 + next * 3] == 0xFFFF) && (next != current)) {
    next = (next + 1) % mem[1];
  }

  if (mem[12 + next * 3] == 0xFFFF) {
    // Hiç proses kalmamış
    running = false;
    return;
  }

  // Yeni prosese geçiş yap
  reg[RPC] = mem[12 + next * 3 + 1];
  reg[PTBR] = mem[12 + next * 3 + 2];
  mem[0] = next;
}


static inline uint16_t mr(uint16_t address) {
 uint16_t vpn = address >> 11; // first 5 bits
    uint16_t offset = address & 0x07FF; 

    if (vpn == 0) {
      printf("Segmentation fault.\n");
      return -1;
    }
  
    uint16_t pte  = mem[reg[PTBR] + vpn];
    // last bit is valid bit 
    if (!(pte & 0x1)) {
        printf("Segmentation fault inside free space.\n");
exit(1);
     }
     if (!(pte & (1 << 1))) {
       printf("Cannot read from a write-only page.\n");
	exit(1);
     }
    
     uint16_t pfn = (pte >> 11) & 0x1F; // ilk 5 bit

  return mem[(pfn <<11) + offset];

}

static inline void mw(uint16_t address, uint16_t val) {
 uint16_t vpn = address >> 11; // first 5 bits
   uint16_t offset = address & 0x07FF; 

   if (vpn == 0) {
      printf("Segmentation fault.\n");
      return;
    }
     uint16_t pte  = mem[reg[PTBR] + vpn];
      // last bit is valid bit 
     if (!(pte & 0x1)) {
        printf("Segmentation fault inside free space.\n");
        exit(1);
     }
     if (!(pte & (1 << 2))) {
       printf("Cannot write from a read-only page.\n"); // ilk 5 bit
	exit(1);    
 }
     uint16_t pfn = (pte >> 11) & 0x1F;
     
  mem[(pfn <<11) + offset] = val;



}

// YOUR CODE ENDS HERE
