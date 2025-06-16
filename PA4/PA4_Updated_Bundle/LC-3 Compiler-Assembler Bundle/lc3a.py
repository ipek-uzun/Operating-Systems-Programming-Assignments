# The LC-3 assembler for the assembly files generated from LC-3 Language source code

# Invocation on terminal: python3 lc3a.py <filename.asm>
# Going to generate filename_code.obj

import os
import sys
import struct
import re

# The maximum number of labels = Number of possible memory locations in a 16-bit address space
MAX_LABELS: int = pow(2, 16)

# Global variables
labels: dict[str, int] = {}
lines: list[str] = []
machine_code: list[int] = []
orig = 0  # .ORIG value

# Helper functions for the assembler:

# Parses the number from a numeric token such as #12 and x3000
def parse_number(s: str) -> tuple[int, bool]:
    if s.startswith('#'):
        return int(s[1:]), True
    elif s.lower().startswith('x'):
        return int(s[1:], 16), True
    else:
        return 0, False

# Finds the address of a label from the global label dictionary given its name
def lookup_label(name: str) -> int:
    global labels
    
    if name in labels:
        return labels[name]

    raise ValueError(f"Unknown label <{name}>")

# Adds a newly encountered label to the global dictionary of encountered labels
def add_label(name: str, address: int) -> None:
    global labels

    if len(labels) >= MAX_LABELS:
        raise MemoryError("Label dictionary overflow")
    
    labels[name] = address

# The actual functions to assemble the instructions
def assemble_ADD(tokens: list[str]) -> int:
    DR = int(tokens[1][1:])
    SR1 = int(tokens[2][1:])
    instr: int = 0x1000 | (DR << 9) | (SR1 << 6)
    if tokens[3].startswith('R'):
        SR2 = int(tokens[3][1:])
        instr |= SR2
    else:
        instr |= 0x20
        imm: int; is_num: bool
        imm, is_num = parse_number(tokens[3])
        if not is_num or imm < -16 or imm > 15:
            raise ValueError(f"Immediate {imm} out of range for ADD")
        instr |= (imm & 0x1F)
    return instr

def assemble_AND(tokens: list[str]) -> int:
    DR = int(tokens[1][1:])
    SR1 = int(tokens[2][1:])
    instr: int = 0x5000 | (DR << 9) | (SR1 << 6)
    if tokens[3].startswith('R'):
        SR2 = int(tokens[3][1:])
        instr |= SR2
    else:
        instr |= 0x20
        imm: int; is_num: bool
        imm, is_num = parse_number(tokens[3])
        if not is_num or imm < -16 or imm > 15:
            raise ValueError(f"Immediate {imm} out of range for AND")
        instr |= (imm & 0x1F)
    return instr

def assemble_NOT(tokens: list[str]) -> int:
    DR = int(tokens[1][1:])
    SR = int(tokens[2][1:])
    return 0x9000 | (DR << 9) | (SR << 6) | 0x3F

def assemble_LD(tokens: list[str], current_pc: int) -> int:
    DR = int(tokens[1][1:])
    value: int; is_num: bool
    value, is_num = parse_number(tokens[2])
    if is_num:
        offset: int = value
    else:
        value = lookup_label(tokens[2])
        offset = value - (current_pc + 1)

    if -256 <= offset <= 255:
        return 0x2000 | (DR << 9) | (offset & 0x1FF)
    else:
        raise ValueError(f"Offset {offset} out of range for LD")

def assemble_LDI(tokens: list[str], current_pc: int) -> int:
    DR = int(tokens[1][1:])
    value: int; is_num: bool
    value, is_num = parse_number(tokens[2])
    if is_num:
        offset: int = value
    else:
        value = lookup_label(tokens[2])
        offset = value - (current_pc + 1)

    if -256 <= offset <= 255:
        return 0xA000 | (DR << 9) | (offset & 0x1FF)
    else:
        raise ValueError(f"Offset {offset} out of range for LDI")

def assemble_LEA(tokens: list[str], current_pc: int) -> int:
    DR = int(tokens[1][1:])
    value: int = lookup_label(tokens[2])
    offset: int = value - current_pc + 1

    if -256 <= offset <= 255:
        return 0xE000 | (DR << 9) | (offset & 0x1FF)
    else:
        raise ValueError(f"Offset {offset} out of range for LEA")
    
def assemble_LDR(tokens: list[str]) -> int:
    DR = int(tokens[1][1:])
    BaseR = int(tokens[2][1:])
    offset: int; is_num: bool
    offset, is_num = parse_number(tokens[3])

    if not is_num or offset < -32 or offset > 31:
        raise ValueError(f"Invalid offset {offset} for LDR")
    
    return 0x6000 | (DR << 9) | (BaseR << 6) | (offset & 0x3F)

def assemble_ST(tokens: list[str], current_pc: int) -> int:
    SR = int(tokens[1][1:])
    value: int; is_num: bool
    value, is_num = parse_number(tokens[2])
    if is_num:
        offset: int = value
    else:
        value = lookup_label(tokens[2])
        offset = value - (current_pc + 1)

    if -256 <= offset <= 255:
        return 0x3000 | (SR << 9) | (offset & 0x1FF)
    else:
        raise ValueError(f"Offset {offset} out of range for ST")

def assemble_STI(tokens: list[str], current_pc: int) -> int:
    SR = int(tokens[1][1:])
    value: int; is_num: bool
    value, is_num = parse_number(tokens[2])
    if is_num:
        offset: int = value
    else:
        value = lookup_label(tokens[2])
        offset = value - (current_pc + 1)

    if -256 <= offset <= 255:
        return 0xB000 | (SR << 9) | (offset & 0x1FF)
    else:
        raise ValueError(f"Offset {offset} out of range for STI")

def assemble_STR(tokens: list[str]) -> int:
    SR = int(tokens[1][1:])
    BaseR = int(tokens[2][1:])
    offset: int; is_num: bool
    offset, is_num = parse_number(tokens[3])

    if not is_num or offset < -32 or offset > 31:
        raise ValueError(f"Offset {offset} out of range for STR")
    
    return 0x7000 | (SR << 9) | (BaseR << 6) | (offset & 0x3F)

def assemble_BR(tokens: list[str], current_pc: int, mnemonic: str) -> int:
    instr = 0
    n: int; z: int; p: int
    n = z = p = 0

    if len(mnemonic) == 2:  # BR (unconditional)
        n = z = p = 1
    else:
        for cond in mnemonic[2:]:
            if cond.lower() == 'n':
                n = 1
            elif cond.lower() == 'z':
                z = 1
            elif cond.lower() == 'p':
                p = 1
            else:
                raise ValueError(f"Invalid branch condition in mnemonic: {mnemonic}")
    
    instr |= (n << 11) | (z << 10) | (p << 9)
    
    label_addr: int = lookup_label(tokens[0])
    offset: int = label_addr - (current_pc + 1)

    if -256 <= offset <= 255:
        instr |= (offset & 0x1FF)
    else:
        raise ValueError(f"BR offset {offset} out of range")
    
    return instr

def assemble_HALT() -> int:
    return 0xF025

def assemble_YIELD() -> int:
    return 0xF028

def assemble_BRK() -> int:
    return 0xF029

def assemble_line(line: str, current_pc: int, mode: str = "assemble") -> int:
    global machine_code

    if (mode != "assemble") and (mode != "preassemble"):
        raise ValueError(f"Incorrect mode {mode}")

    line = line.replace('\u00A0', ' ').replace('\u202F', ' ')
    tokens: list[str] = [token for token in re.split(r'[ \t,]+', line) if token]
    if not tokens or tokens[0].startswith(';'):
        return 0  # Empty or comment line

    opcode: str = tokens[0].upper()
    if opcode == "ADD":
        if mode == "assemble":
            machine_code.append(assemble_ADD(tokens))

        return 1
    elif opcode == "AND":
        if mode == "assemble":
            machine_code.append(assemble_AND(tokens))
            
        return 1
    elif opcode == "NOT":
        if mode == "assemble":
            machine_code.append(assemble_NOT(tokens))

        return 1
    elif opcode == "LD":
        if mode == "assemble":
            machine_code.append(assemble_LD(tokens, current_pc))

        return 1
    elif opcode == "LDI":
        if mode == "assemble":
            machine_code.append(assemble_LDI(tokens, current_pc))

        return 1
    elif opcode == "LDR":
        if mode == "assemble":
            machine_code.append(assemble_LDR(tokens))

        return 1
    elif opcode == "LEA":
        if mode == "assemble":
            machine_code.append(assemble_LEA(tokens, current_pc))

        return 1
    elif opcode == "ST":
        if mode == "assemble":
            machine_code.append(assemble_ST(tokens, current_pc))

        return 1
    elif opcode == "STI":
        if mode == "assemble":
            machine_code.append(assemble_STI(tokens, current_pc))

        return 1
    elif opcode == "STR":
        if mode == "assemble":
            machine_code.append(assemble_STR(tokens))

        return 1
    elif opcode.startswith("BR") and opcode != "BRK":
        if mode == "assemble":
            machine_code.append(assemble_BR(tokens[1:], current_pc, opcode))

        return 1
    elif opcode == "HALT":
        if mode == "assemble":
            machine_code.append(assemble_HALT())

        return 1
    elif opcode == "YIELD":
        if mode == "assemble":
            machine_code.append(assemble_YIELD())

        return 1
    elif opcode == "BRK":
        if mode == "assemble":
            machine_code.append(assemble_BRK())

        return 1
    else:
        raise ValueError(f"Unsupported opcode: {opcode}")

def assemble(input_file: str) -> None:
    global machine_code

    try:
        with open(input_file, 'r') as f:
            for line in f:
                lines.append(line.strip())

        non_label_lines: list[str] = []

        # PASS 1: Locate .ORIG and record label addresses
        pc: int = 0
        started: bool = False
        for line in lines:
            if line.startswith(';') or not line:
                continue
            tokens: list[str] = [token for token in re.split(r'[ \t,]+', line) if token]
            if tokens[0].startswith('.'):
                if tokens[0].upper() == ".ORIG":
                    if len(tokens) < 2:
                        raise ValueError(".ORIG missing operand")
                    global orig
                    orig, is_num = parse_number(tokens[1])
                    if not is_num:
                        raise ValueError(f"Invalid .ORIG operand: {tokens[1]}")
                    pc = orig
                    started = True
                continue
            if not started:
                raise ValueError("Missing .ORIG before instructions")
            if tokens[0] not in {"ADD", "AND", "LD", "LDI", "LDR", "LEA", "ST", "STI", "STR", "BR", "BRnzp", "BRnz", "BRzp", "BRn", "BRz", "BRp", "NOT", "HALT", "YIELD", "BRK"}:
                add_label(tokens[0], pc)
            else:
                non_label_lines.append(line)
                pc += assemble_line(line, pc, "preassemble")

        # PASS 2: Assemble instructions
        pc = orig
        for line in lines:
            if line in non_label_lines:
                pc += assemble_line(line, pc)

        machine_code.append(0x4000)
        
    except Exception as err:
        print(f"Error: {err}")
        exit(os.EX_IOERR)

    try:
        output_file: str = input_file.rsplit('.', 1)[0] + "_code.obj"
        with open(output_file, 'wb') as f:
            for word in machine_code:
                f.write(struct.pack("<H", word))
        print(f"Assembly successful. {len(machine_code)} words written to {output_file}")
    except Exception as err:
        print(f"Error: {err}")
        exit(os.EX_CANTCREAT)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <assembly source file>")
        sys.exit(1)

    assemble(sys.argv[1])