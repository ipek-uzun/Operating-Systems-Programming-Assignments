# CS307 - Operating Systems Assignments

This repository contains my solutions to programming assignments from the Operating Systems course (CS307), Spring 2025. The assignments cover core OS concepts such as process management, shell simulation, thread synchronization, and virtual memory.


### PA1 - TreePipe Shell Simulation

**Description:**  
Implements a custom shell command named `TreePipe` that simulates a binary tree of processes. Each process communicates with its parent and children via UNIX pipes and executes either an addition or multiplication program based on its position in the tree. Execution follows **in-order traversal**.

- System Calls: `fork`, `exec`, `wait`, `pipe`
- Root takes input from user, leaves use default values
- Binary tree traversal with IPC (inter-process communication)

### PA3 - Synchronization Slam Dunk 
**Description:**  
Simulates a basketball court where players (threads) must synchronize using semaphores. A match starts only when enough players are inside. If a referee is present, they must announce the end of the game before players leave. Synchronization ensures no over-capacity, proper entry/exit conditions, and ordered exits.

- Threads represent players and referees
- Semaphores used for thread coordination
- Only fixed number of players allowed inside
- Players cannot leave during a match
- Referee (if exists) announces end of match
- Last player notifies waiting threads after leaving
  
### PA4 - Virtual Memory with Paging
**Description:**  

Extends a basic LC-3 virtual machine to support paging-based address translation, along with yield and brk system calls. Implements a realistic separation between Virtual Address Space (VAS) and physical memory, allowing context switching and heap resizing.
- Adds page table translation to `vm.c`
- Separates physical memory from virtual address space
- Implements context switching via `yield`
- Allows heap growth via `brk`
- Enables multiple processes with isolated address spaces

# Tools & Technologies Used
- **Languages:** C, C++
- **Concurrency:** POSIX Threads (`pthread`)
- **Synchronization:** Semaphores (`sem_t`), Barriers


