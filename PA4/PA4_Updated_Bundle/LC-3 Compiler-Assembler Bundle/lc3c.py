# The compiler for LC-3 Language

# Invocation on terminal: python3 lc3c.py <filename.lc3>
# Going to generate filename.asm and filename_heap.obj

import os
import sys
import struct
import re

heap_init: list[str] = []

# Global counter for generating unique labels
unique_label_counter: int = 0
def get_unique_label(prefix: str) -> str:
    global unique_label_counter
    label: str = f"{prefix}{unique_label_counter}"
    unique_label_counter += 1
    return label

# Global variables for variable memory addressing
var_addresses: dict[str, str] = {}
next_var_address: int = 0x0000

def get_var_address(var: str) -> str:
    global var_addresses
    global next_var_address

    if var not in var_addresses:
        var_addresses[var] = f"x{next_var_address:04X}"
        next_var_address += 1

    return var_addresses[var]

def compile_line(line: str) -> list[str]:
    global heap_init
    global var_addresses
    instructions: list[str] = []

    if line == "YIELD":
        instructions.append("YIELD")
        return instructions
    
    if line == "BRK":
        instructions.append("BRK")
        return instructions

    # If LHS is a register
    if line.startswith("R"):
        # register = register
        m: re.Match[str] | None = re.match(r'^(R\d+)\s*=\s*(R\d+)$', line)
        if m:
            reg: str; reg1: str
            reg, reg1 = m.groups()

            if reg != reg1:
                instructions.append(f"AND {reg}, {reg}, #0")
                instructions.append(f"ADD {reg}, {reg}, {reg1}")
            
            return instructions

        # register = variable
        m = re.match(r'^(R\d+)\s*=\s*([a-zA-Z_]\w*)$', line)
        if m:
            var: str
            reg, var = m.groups()

            instructions.append(f"LDR {reg}, R7, {get_var_address(var)}")

            return instructions
        
        # register = constant
        m = re.match(r'^(R\d+)\s*=\s*(\d+)$', line)
        if m:
            imm: str
            reg, imm = m.groups()

            instructions.append(f"AND {reg}, {reg}, #0")

            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD {reg}, {reg}, #{imm}")
                elif int(imm) <= -16:
                    times: int = int(imm) // -16
                    remainder: int = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #-16")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #15")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
            
            return instructions

        # register = register + register
        m = re.match(r'^(R\d+)\s*=\s*(R\d+)\s*\+\s*(R\d+)$', line)
        if m:
            reg2: str
            reg, reg1, reg2 = m.groups()

            if (reg != reg1) and (reg != reg2):
                instructions.append(f"AND {reg}, {reg}, #0")
            
            instructions.append(f"ADD {reg}, {reg1}, {reg2}")
            return instructions

        # register = register - register
        m = re.match(r'^(R\d+)\s*=\s*(R\d+)\s*\-\s*(R\d+)$', line)
        if m:
            reg, reg1, reg2 = m.groups()

            if (reg == reg1) and (reg == reg2):
                instructions.append(f"AND {reg}, {reg}, #0")
            elif reg == reg1:
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {reg2}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")
                instructions.append(f"ADD {reg1}, {reg1}, R5")
                instructions.append(f"AND R5, R5, #0")
            elif reg == reg2:
                instructions.append(f"NOT {reg}, {reg}")
                instructions.append(f"ADD {reg}, {reg}, #1")
                instructions.append(f"ADD {reg}, {reg1}, {reg}")
            else:
                instructions.append(f"AND {reg}, {reg}, #0")
                instructions.append(f"ADD {reg}, {reg1}, #0")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {reg2}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")
                instructions.append(f"ADD {reg}, {reg}, R5")
                instructions.append(f"AND R5, R5, #0")
            
            return instructions
        
        # register = variable + variable
        m = re.match(r'^(R\d+)\s*=\s*([a-zA-Z_]\w*)\s*\+\s*([a-zA-Z_]\w*)$', line)
        if m:
            var1: str; var2: str
            reg, var1, var2 = m.groups()

            if var1 == var2:
                instructions.append(f"LDR {reg}, R7, {get_var_address(var1)}")
                instructions.append(f"ADD {reg}, {reg}, {reg}")
            else:
                instructions.append(f"LDR {reg}, R7, {get_var_address(var1)}")
                instructions.append(f"LDR R5, R7, {get_var_address(var2)}")
                instructions.append(f"ADD {reg}, {reg}, R5")
                instructions.append(f"AND R5, R5, #0")
            
            return instructions
        
        # register = variable - variable
        m = re.match(r'^(R\d+)\s*=\s*([a-zA-Z_]\w*)\s*\-\s*([a-zA-Z_]\w*)$', line)
        if m:
            reg, var1, var2 = m.groups()

            if var1 == var2:
                instructions.append(f"AND {reg}, {reg}, #0")
            else:
                instructions.append(f"LDR {reg}, R7, {get_var_address(var1)}")
                instructions.append(f"LDR R5, R7, {get_var_address(var2)}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")
                instructions.append(f"ADD {reg}, {reg}, R5")
                instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # register = constant + constant
        m = re.match(r'^(R\d+)\s*=\s*(\d+)\s*\+\s*(\d+)$', line)
        if m:
            imm1: str; imm2: str
            reg, imm1, imm2 = m.groups()

            instructions.append(f"AND {reg}, {reg}, #0")

            if imm1 != "0":
                if (int(imm1) >= -16) and (int(imm1) <= 15):
                    instructions.append(f"ADD {reg}, {reg}, #{imm1}")
                elif int(imm1) <= -16:
                    times = int(imm1) // -16
                    remainder = int(imm1) % -16

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #-16")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                else:
                    times = int(imm1) // 15
                    remainder = int(imm1) % 15

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #15")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")

            if imm2 != "0":
                if (int(imm2) >= -16) and (int(imm2) <= 15):
                    instructions.append(f"ADD {reg}, {reg}, #{imm2}")
                elif int(imm2) <= -16:
                    times = int(imm2) // -16
                    remainder = int(imm2) % -16

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #-16")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                else:
                    times = int(imm2) // 15
                    remainder = int(imm2) % 15

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #15")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")

            return instructions

        # register = constant - constant
        m = re.match(r'^(R\d+)\s*=\s*([a-zA-Z_]\w*)\s*\-\s*([a-zA-Z_]\w*)$', line)
        if m:
            reg, imm1, imm2 = m.groups()

            instructions.append(f"AND {reg}, {reg}, #0")
            
            if imm1 != imm2:
                if imm1 != "0":
                    if (int(imm1) >= -16) and (int(imm1) <= 15):
                        instructions.append(f"ADD {reg}, {reg}, #{imm1}")
                    elif int(imm1) <= -16:
                        times = int(imm1) // -16
                        remainder = int(imm1) % -16

                        for _ in range(times):
                            instructions.append(f"ADD {reg}, {reg}, #-16")
                        
                        instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                    else:
                        times = int(imm1) // 15
                        remainder = int(imm1) % 15

                        for _ in range(times):
                            instructions.append(f"ADD {reg}, {reg}, #15")
                        
                        instructions.append(f"ADD {reg}, {reg}, #{remainder}")

                instructions.append(f"AND R5, R5, #0")

                if imm2 != "0":
                    if (int(imm2) >= -16) and (int(imm2) <= 15):
                        instructions.append(f"ADD R5, R5, #{imm2}")
                    elif int(imm2) <= -16:
                        times = int(imm2) // -16
                        remainder = int(imm2) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #-16")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                    else:
                        times = int(imm2) // 15
                        remainder = int(imm2) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #15")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")

                    instructions.append(f"NOT R5, R5")
                    instructions.append(f"ADD R5, R5, #1")
                    instructions.append(f"ADD {reg}, {reg}, R5")
                    instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # register = register + variable
        m = re.match(r'^(R\d+)\s*=\s*(R\d+)\s*\+\s*([a-zA-Z_]\w*)$', line)
        if m:
            reg, reg1, var = m.groups()

            if reg != reg1:
                instructions.append(f"AND {reg}, {reg}, #0")
            
            instructions.append(f"LDR R5, R7, {get_var_address(var)}")
            instructions.append(f"ADD {reg}, {reg1}, R5")
            instructions.append(f"AND R5, R5, #0")
                
            return instructions
        
        # register = variable + register
        m = re.match(r'^(R\d+)\s*=\s*([a-zA-Z_]\w*)\s*\+\s*(R\d+)$', line)
        if m:
            reg, var, reg1 = m.groups()

            if reg != reg1:
                instructions.append(f"AND {reg}, {reg}, #0")

            instructions.append(f"LDR R5, R7, {get_var_address(var)}")
            instructions.append(f"ADD {reg}, {reg1}, R5")
            instructions.append(f"AND R5, R5, #0")
            return instructions
        
        # register = register - variable
        m = re.match(r'^(R\d+)\s*=\s*(R\d+)\s*\-\s*([a-zA-Z_]\w*)$', line)
        if m:
            reg, reg1, var = m.groups()
            
            if reg != reg1:
                instructions.append(f"AND {reg}, {reg}, #0")
                instructions.append(f"ADD {reg}, {reg}, {reg1}")
            
            instructions.append(f"LDR R5, R7, {get_var_address(var)}")
            instructions.append(f"NOT R5, R5")
            instructions.append(f"ADD R5, R5, #1")
            instructions.append(f"ADD {reg}, {reg}, R5")
            instructions.append(f"AND R5, R5, #0")
            return instructions
        
        # register = variable - register
        m = re.match(r'^(R\d+)\s*=\s*([a-zA-Z_]\w*)\s*\-\s*(R\d+)$', line)
        if m:
            reg, var, reg1 = m.groups()

            if reg == reg1:
                instructions.append(f"NOT {reg1}, {reg1}")
                instructions.append(f"ADD {reg1}, {reg1}, #1")
                instructions.append(f"LDR R5, R7, {get_var_address(var)}")
                instructions.append(f"ADD {reg}, {reg}, R5")
                instructions.append(f"AND R5, R5, #0")
            else:
                instructions.append(f"LDR {reg}, R7, {get_var_address(var)}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {reg1}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")
                instructions.append(f"ADD {reg}, {reg}, R5")
                instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # register = register + constant
        m = re.match(r'^(R\d+)\s*=\s*(R\d+)\s*\+\s*(\d+)$', line)
        if m:
            reg, reg1, imm = m.groups()

            if reg != reg1:
                instructions.append(f"AND {reg}, {reg}, #0")
                instructions.append(f"ADD {reg}, {reg}, {reg1}")
            
            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD {reg}, {reg}, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #-16")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #15")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
            
            return instructions
        
        # register = constant + register
        m = re.match(r'^(R\d+)\s*=\s*(\d+)\s*\+\s*(R\d+)$', line)
        if m:
            reg, imm, reg1 = m.groups()

            if reg != reg1:
                instructions.append(f"AND {reg}, {reg}, #0")
                instructions.append(f"ADD {reg}, {reg}, {reg1}")

            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD {reg}, {reg}, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #-16")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #15")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")

            return instructions

        # register = register - constant
        m = re.match(r'^(R\d+)\s*=\s*(R\d+)\s*\-\s*(\d+)$', line)
        if m:
            reg, reg1, imm = m.groups()
            
            if reg != reg1:
                instructions.append(f"AND {reg}, {reg}, #0")
                instructions.append(f"ADD {reg}, {reg}, {reg1}")
            
            if imm != "0":
                instructions.append(f"AND R5, R5, #0")
                
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R5, R5, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #-16")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #15")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")

                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")
                instructions.append(f"ADD {reg}, {reg}, R5")
                instructions.append(f"AND R5, R5, #0")
            
            return instructions
        
        # register = constant - register
        m = re.match(r'^(R\d+)\s*=\s*(\d+)\s*\-\s*(R\d+)$', line)
        if m:
            reg, imm, reg1 = m.groups()

            if reg == reg1:
                instructions.append(f"NOT {reg}, {reg}")
                instructions.append(f"ADD {reg}, {reg}, #1")

                if imm != "0":
                    if (int(imm) >= -16) and (int(imm) <= 15):
                        instructions.append(f"ADD {reg}, {reg}, #{imm}")
                    elif int(imm) <= -16:
                        times = int(imm) // -16
                        remainder = int(imm) % -16

                        for _ in range(times):
                            instructions.append(f"ADD {reg}, {reg}, #-16")
                        
                        instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                    else:
                        times = int(imm) // 15
                        remainder = int(imm) % 15

                        for _ in range(times):
                            instructions.append(f"ADD {reg}, {reg}, #15")
                        
                        instructions.append(f"ADD {reg}, {reg}, #{remainder}")
            else:
                instructions.append(f"AND {reg}, {reg}, #0")

                if imm != "0":
                    if (int(imm) >= -16) and (int(imm) <= 15):
                        instructions.append(f"ADD {reg}, {reg}, #{imm}")
                    elif int(imm) <= -16:
                        times = int(imm) // -16
                        remainder = int(imm) % -16

                        for _ in range(times):
                            instructions.append(f"ADD {reg}, {reg}, #-16")
                        
                        instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                    else:
                        times = int(imm) // 15
                        remainder = int(imm) % 15

                        for _ in range(times):
                            instructions.append(f"ADD {reg}, {reg}, #15")
                        
                        instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {reg1}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")
                instructions.append(f"ADD {reg}, {reg}, R5")
                instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # register = variable + constant
        m = re.match(r'^(R\d+)\s*=\s*([a-zA-Z_]\w*)\s*\+\s*(\d+)$', line)
        if m:
            reg, var, imm = m.groups()
            
            instructions.append(f"AND {reg}, {reg}, #0")

            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD {reg}, {reg}, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #-16")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #15")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
            
            instructions.append(f"LDR R5, R7, {get_var_address(var)}")
            instructions.append(f"ADD {reg}, {reg}, R5")
            instructions.append(f"AND R5, R5, #0")
            return instructions
        
        # register = constant + variable
        m = re.match(r'^(R\d+)\s*=\s*(\d+)\s*\+\s*([a-zA-Z_]\w*)$', line)
        if m: 
            reg, imm, var = m.groups()

            instructions.append(f"AND {reg}, {reg}, #0")

            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD {reg}, {reg}, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #-16")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #15")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
            
            instructions.append(f"LDR R5, R7, {get_var_address(var)}")
            instructions.append(f"ADD {reg}, {reg}, R5")
            instructions.append(f"AND R5, R5, #0")
            return instructions
        
        # register = variable - constant
        m = re.match(r'^(R\d+)\s*=\s*([a-zA-Z_]\w*)\s*\-\s*(\d+)$', line)
        if m:
            reg, var, imm = m.groups()

            instructions.append(f"LDR {reg}, R7, {get_var_address(var)}")

            if imm != "0":
                instructions.append(f"AND R5, R5, #0")

                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R5, R5, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #-16")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #15")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")

                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")
                instructions.append(f"ADD {reg}, {reg}, R5")
                instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # register = constant - variable
        m = re.match(r'^(R\d+)\s*=\s*(\d+)\s*\-\s*([a-zA-Z_]\w*)$', line)
        if m:
            reg, imm, var = m.groups()

            instructions.append(f"AND {reg}, {reg}, #0")

            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD {reg}, {reg}, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #-16")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #15")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                
            instructions.append(f"LDR R5, R7, {get_var_address(var)}")
            instructions.append(f"NOT R5, R5")
            instructions.append(f"ADD R5, R5, #1")
            instructions.append(f"ADD {reg}, {reg}, R5")
            instructions.append(f"AND R5, R5, #0")

            return instructions

        # register += register (different)
        m = re.match(r'^(R\d+)\s*\+=\s*(?!\1)(R\d+)$', line)
        if m:
            reg1, reg2 = m.groups()

            instructions.append(f"ADD {reg1}, {reg1}, {reg2}")

            return instructions
        
        # register -= register (different)
        m = re.match(r'^(R\d+)\s*-\=\s*(?!\1)(R\d+)$', line)
        if m:
            reg1, reg2 = m.groups()

            instructions.append(f"AND R5, R5, #0")
            instructions.append(f"ADD R5, R5, {reg2}")
            instructions.append(f"NOT R5, R5")
            instructions.append(f"ADD R5, R5, #1")
            instructions.append(f"ADD {reg1}, {reg1}, R5")
            instructions.append(f"AND R5, R5, #0")    
            
            return instructions
        
        # register += variable
        m = re.match(r'^(R\d+)\s*\+=\s*([a-zA-Z_]\w*)$', line)
        if m:
            reg, var = m.groups()

            instructions.append(f"LDR R5, R7, {get_var_address(var)}")
            instructions.append(f"ADD {reg}, {reg}, R5")
            instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # register -= variable
        m = re.match(r'^(R\d+)\s*-\=\s*([a-zA-Z_]\w*)$', line)
        if m:
            reg, var = m.groups()

            instructions.append(f"LDR R5, R7, {get_var_address(var)}")
            instructions.append(f"NOT R5, R5")
            instructions.append(f"ADD R5, R5, #1")
            instructions.append(f"ADD {reg}, {reg}, R5")
            instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # register += constant
        m = re.match(r'^(R\d+)\s*\+=\s*(\d+)$', line)
        if m:
            reg, imm = m.groups()

            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD {reg}, {reg}, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #-16")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD {reg}, {reg}, #15")
                    
                    instructions.append(f"ADD {reg}, {reg}, #{remainder}")
            
            return instructions
        
        # register -= constant
        m = re.match(r'^(R\d+)\s*-\=\s*(\d+)$', line)
        if m:
            reg, imm = m.groups()

            if imm != "0":
                instructions.append(f"AND R5, R5, #0")

                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R5, R5, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #-16")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #15")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")

                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")
                instructions.append(f"ADD {reg}, {reg}, R5")
                instructions.append(f"AND R5, R5, #0")
            
            return instructions
        
        # register += register (same)
        m = re.match(r'^(R\d+)\s*\+=\s*(R\d+)$', line)
        if m:
            reg1, reg2 = m.groups()

            instructions.append(f"ADD {reg1}, {reg1}, {reg2}")

            return instructions
        
        # register -= register (same)
        m = re.match(r'^(R\d+)\s*-\=\s*(R\d+)$', line)
        if m:
            reg1, reg2 = m.groups()

            instructions.append(f"AND {reg1}, {reg1}, #0")

            return instructions
        
    # If LHS is a variable
    else:
        # variable = register
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(R\d+)$', line)
        if m:
            var, reg = m.groups()

            instructions.append(f"STR {reg}, R7, {get_var_address(var)}")

            return instructions
        
        # variable = variable
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*([a-zA-Z_]\w*)$', line)
        if m:
            var1, var2 = m.groups()
            
            if var1 != var2:
                instructions.append(f"LDR R5, R7, {get_var_address(var2)}")
                instructions.append(f"STR R5, R7, {get_var_address(var1)}")
            
            return instructions

        # variable = constant
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(\d+)$', line)
        if m:
            var, imm = m.groups()

            if var not in var_addresses:
                heap_init.append(line)
                get_var_address(var)
            else:
                instructions.append(f"AND R5, R5, #0")

                if imm != "0":
                    if (int(imm) >= -16) and (int(imm) <= 15):
                        instructions.append(f"ADD R5, R5, #{imm}")
                    elif int(imm) <= -16:
                        times = int(imm) // -16
                        remainder = int(imm) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #-16")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                    else:
                        times = int(imm) // 15
                        remainder = int(imm) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #15")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                
                instructions.append(f"STR R5, R7, {get_var_address(var)}")
                instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # variable = register + register
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(R\d+)\s*\+\s*(R\d+)$', line)
        if m:
            var, reg1, reg2 = m.groups()

            instructions.append(f"AND R5, R5, #0")
            instructions.append(f"ADD R5, R5, {reg1}")
            instructions.append(f"ADD R5, R5, {reg2}")
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")
            
            return instructions
        
        # variable = register - register
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(R\d+)\s*\-\s*(R\d+)$', line)
        if m:
            var, reg1, reg2 = m.groups()

            if reg1 == reg2:
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"STR R5, R7, {get_var_address(var)}")
            else:
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"AND R6, R6, #0")
                instructions.append(f"ADD R5, R5, {reg1}")
                instructions.append(f"ADD R6, R6, {reg2}")
                instructions.append(f"NOT R6, R6")
                instructions.append(f"ADD R6, R6, #1")
                instructions.append(f"ADD R5, R5, R6")
                instructions.append(f"STR R5, R7, {get_var_address(var)}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"AND R6, R6, #0")

            return instructions
        
        # variable = variable + variable
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*([a-zA-Z_]\w*)\s*\+\s*([a-zA-Z_]\w*)$', line)
        if m:
            var, var1, var2 = m.groups()

            if (var == var1) and (var == var2):
                instructions.append(f"LDR R5, R7, {get_var_address(var)}")
                instructions.append(f"ADD R5, R5, R5")
                instructions.append(f"STR R5, R7, {get_var_address(var)}")
            else:
                instructions.append(f"LDR R5, R7, {get_var_address(var1)}")
                instructions.append(f"LDR R6, R7, {get_var_address(var2)}")
                instructions.append(f"ADD R5, R5, R6")
                instructions.append(f"STR R5, R7, {get_var_address(var)}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"AND R6, R6, #0")

            return instructions
        
        # variable = variable - variable
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*([a-zA-Z_]\w*)\s*\-\s*([a-zA-Z_]\w*)$', line)
        if m:
            var, var1, var2 = m.groups()
            
            if var1 == var2:
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"STR R5, R7, {get_var_address(var)}")
            else:
                instructions.append(f"LDR R5, R7, {get_var_address(var1)}")
                instructions.append(f"LDR R6, R7, {get_var_address(var2)}")
                instructions.append(f"NOT R6, R6")
                instructions.append(f"ADD R6, R6, #1")
                instructions.append(f"ADD R5, R5, R6")
                instructions.append(f"STR R5, R7, {get_var_address(var)}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"AND R6, R6, #0")

            return instructions
    
        # variable = constant + constant
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(\d+)\s*\+\s*(\d+)$', line)
        if m:
            var, imm1, imm2 = m.groups()
            
            if var not in var_addresses:
                heap_init.append(line)
                get_var_address(var)
            else:
                instructions.append(f"AND R5, R5, #0")

                if imm1 != "0":
                    if (int(imm1) >= -16) and (int(imm1) <= 15):
                        instructions.append(f"ADD R5, R5, #{imm1}")
                    elif int(imm1) <= -16:
                        times = int(imm1) // -16
                        remainder = int(imm1) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #-16")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                    else:
                        times = int(imm1) // 15
                        remainder = int(imm1) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #15")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")

                if imm2 != "0":
                    if (int(imm2) >= -16) and (int(imm2) <= 15):
                        instructions.append(f"ADD R5, R5, #{imm1}")
                    elif int(imm2) <= -16:
                        times = int(imm2) // -16
                        remainder = int(imm2) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #-16")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                    else:
                        times = int(imm2) // 15
                        remainder = int(imm2) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #15")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                
                instructions.append(f"STR R5, R7, {get_var_address(var)}")
                instructions.append(f"AND R5, R5, #0")

            return instructions

        # variable = constant - constant
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(\d+)\s*\-\s*(\d+)$', line)
        if m:
            if var not in var_addresses:
                heap_init.append(line)
                get_var_address(var)
            else:
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"AND R6, R6, #0")

                if imm1 != "0":
                    if (int(imm1) >= -16) and (int(imm1) <= 15):
                        instructions.append(f"ADD R5, R5, #{imm1}")
                    elif int(imm1) <= -16:
                        times = int(imm1) // -16
                        remainder = int(imm1) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #-16")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                    else:
                        times = int(imm1) // 15
                        remainder = int(imm1) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #15")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")

                if imm2 != "0":
                    if (int(imm2) >= -16) and (int(imm2) <= 15):
                        instructions.append(f"ADD R6, R6, #{imm1}")
                    elif int(imm2) <= -16:
                        times = int(imm2) // -16
                        remainder = int(imm2) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R&, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(imm2) // 15
                        remainder = int(imm2) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")

                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")
                    instructions.append(f"AND R6, R6, #0")
                
                instructions.append(f"STR R5, R7, {get_var_address(var)}")
                instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # variable = register + variable
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(R\d+)\s*\+\s*([a-zA-Z_]\w*)$', line)
        if m:
            var, reg, var1 = m.groups()

            instructions.append(f"LDR R5, R7, {get_var_address(var1)}")
            instructions.append(f"ADD R5, R5, {reg}")
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")

            return instructions

        # variable = variable + register
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*([a-zA-Z_]\w*)\s*\+\s*(R\d+)$', line)
        if m:
            var, var1, reg = m.groups()
            
            instructions.append(f"LDR R5, R7, {get_var_address(var1)}")
            instructions.append(f"ADD R5, R5, {reg}")
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # variable = register - variable
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(R\d+)\s*\-\s*([a-zA-Z_]\w*)$', line)
        if m:
            var, reg, var1 = m.groups()

            instructions.append(f"LDR R5, R7, {get_var_address(var1)}")
            instructions.append(f"NOT R5, R5")
            instructions.append(f"ADD R5, R5, #1")
            instructions.append(f"ADD R5, R5, {reg}")
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")

            return instructions

        # variable = variable - register
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*([a-zA-Z_]\w*)\s*\-\s*(R\d+)$', line)
        if m:
            var, var1, reg = m.groups()

            instructions.append(f"LDR R5, R7, {get_var_address(var1)}")
            instructions.append(f"AND R6, R6, #0")
            instructions.append(f"ADD R6, R6, {reg}")
            instructions.append(f"NOT R6, R6")
            instructions.append(f"ADD R6, R6, #1")
            instructions.append(f"ADD R5, R5, R6")
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")
            instructions.append(f"AND R6, R6, #0")

            return instructions
        
        # variable = register + constant
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(R\d+)\s*\+\s*(\d+)$', line)
        if m:
            var, reg, imm = m.groups()

            instructions.append(f"AND R5, R5, #0")
            instructions.append(f"ADD R5, R5, {reg}")
            
            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R5, R5, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #-16")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #15")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
            
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")

            return instructions

        # variable = constant + register
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(\d+)\s*\+\s*(R\d+)$', line)
        if m:
            var, imm, reg = m.groups()
            instructions.append(f"AND R5, R5, #0")
            instructions.append(f"ADD R5, R5, {reg}")

            if var not in var_addresses:
                get_var_address(var)

            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R5, R5, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #-16")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #15")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
            
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")

            return instructions

        # variable = register - constant
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(R\d+)\s*\-\s*(\d+)$', line)
        if m:
            var, reg, imm = m.groups()

            instructions.append(f"AND R5, R5, #0")

            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R5, R5, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #-16")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #15")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")

                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")

            instructions.append(f"ADD R5, R5, {reg}")
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")

            return instructions

        # variable = constant - register
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(\d+)\s*\-\s*(R\d+)$', line)
        if m:
            var, imm, reg = m.groups()

            if var not in var_addresses:
                get_var_address(var)

            instructions.append(f"AND R5, R5, #0")
            instructions.append(f"ADD R5, R5, {reg}")
            instructions.append(f"NOT R5, R5")
            instructions.append(f"ADD R5, R5, #1")

            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R5, R5, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #-16")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #15")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
            
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # variable = variable + constant
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*([a-zA-Z_]\w*)\s*\+\s*(\d+)$', line)
        if m:
            var, var1, imm = m.groups()

            if (var == var1) and (imm == "0"):
                return instructions

            instructions.append(f"LDR R5, R7, {get_var_address(var1)}")

            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R5, R5, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #-16")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #15")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
            
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # variable = constant + variable
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(\d+)\s*\+\s*([a-zA-Z_]\w*)$', line)
        if m:
            var, imm, var1 = m.groups()

            if (var == var1) and (imm == "0"):
                return instructions

            instructions.append(f"LDR R5, R7, {get_var_address(var1)}")

            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R5, R5, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #-16")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #15")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
            
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # variable = variable - constant
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*([a-zA-Z_]\w*)\s*\-\s*(\d+)$', line)
        if m:
            var, var1, imm = m.groups()

            if (var == var1) and (imm == "0"):
                return instructions

            instructions.append(f"LDR R5, R7, {get_var_address(var1)}")

            if imm != "0":
                instructions.append(f"AND R6, R6, #0")

                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R6, R6, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R6, R6, #-16")
                    
                    instructions.append(f"ADD R6, R6, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R6, R6, #15")
                    
                    instructions.append(f"ADD R6, R6, #{remainder}")

                instructions.append(f"NOT R6, R6")
                instructions.append(f"ADD R6, R6, #1")
                instructions.append(f"ADD R5, R5, R6")
            
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")

            if imm != "0":
                instructions.append(f"AND R6, R6, #0")

            return instructions

        # variable = constant - variable
        m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(\d+)\s*\-\s*([a-zA-Z_]\w*)$', line)
        if m:
            var, imm, var1 = m.groups()

            instructions.append(f"LDR R5, R5, {get_var_address(var1)}")
            instructions.append(f"NOT R5, R5")
            instructions.append(f"ADD R5, R5, #1")

            if imm != "0":
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R5, R5, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #-16")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #15")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")

            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")
            
            return instructions
        
        # variable += register
        m = re.match(r'^([a-zA-Z_]\w*)\s*\+=\s*(R\d+)$', line)
        if m:
            var, reg = m.groups()

            instructions.append(f"LDR R5, R7, {get_var_address(var)}")
            instructions.append(f"ADD R5, R5, {reg}")
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")

            return instructions
        
        # variable -= register
        m = re.match(r'^([a-zA-Z_]\w*)\s*-\=\s*(R\d+)$', line)
        if m:
            var, reg = m.groups()

            instructions.append(f"LDR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R6, R6, #0")
            instructions.append(f"ADD R6, R6, {reg}")
            instructions.append(f"NOT R6, R6")
            instructions.append(f"ADD R6, R6, #1")
            instructions.append(f"ADD R5, R5, R6")
            instructions.append(f"STR R5, R7, {get_var_address(var)}")
            instructions.append(f"AND R5, R5, #0")
            instructions.append(f"AND R6, R6, #0")

            return instructions

        # variable += variable (different)
        m = re.match(r'^([a-zA-Z_]\w*)\s*\+=\s*(?!\1)([a-zA-Z_]\w*)$', line)
        if m:
            var1, var2 = m.groups()

            instructions.append(f"LDR R5, R7, {get_var_address(var1)}")
            instructions.append(f"LDR R6, R7, {get_var_address(var2)}")
            instructions.append(f"ADD R5, R5, R6")
            instructions.append(f"STR R5, R7, {get_var_address(var1)}")
            instructions.append(f"AND R5, R5, #0")
            instructions.append(f"AND R6, R6, #0")

            return instructions
        
        # variable -= variable (different)
        m = re.match(r'^([a-zA-Z_]\w*)\s*-\=\s*(?!\1)([a-zA-Z_]\w*)$', line)
        if m:
            var1, var2 = m.groups()

            instructions.append(f"LDR R5, R7, {get_var_address(var1)}")
            instructions.append(f"LDR R6, R7, {get_var_address(var2)}")
            instructions.append(f"NOT R6, R6")
            instructions.append(f"ADD R6, R6, #1")
            instructions.append(f"ADD R5, R5, R6")
            instructions.append(f"STR R5, R7, {get_var_address(var1)}")
            instructions.append(f"AND R5, R5, #0")
            instructions.append(f"AND R6, R6, #0")

            return instructions
        
        # variable += constant
        m = re.match(r'^([a-zA-Z_]\w*)\s*\+=\s*(\d+)$', line)
        if m:
            var, imm = m.groups()

            if imm != "0":
                instructions.append(f"LDR R5, R7, {get_var_address(var)}")

                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R5, R5, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #-16")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R5, R5, #15")
                    
                    instructions.append(f"ADD R5, R5, #{remainder}")

                instructions.append(f"STR R5, R7, {get_var_address(var)}")
                instructions.append(f"AND R5, R5, #0")
            
            return instructions
        
        # variable -= constant
        m = re.match(r'^([a-zA-Z_]\w*)\s*-\=\s*(\d+)$', line)
        if m:
            var, imm = m.groups()

            if imm != "0":
                instructions.append(f"LDR R5, R7, {get_var_address(var)}")
                instructions.append(f"AND R6, R6, #0")
                
                if (int(imm) >= -16) and (int(imm) <= 15):
                    instructions.append(f"ADD R6, R6, #{imm}")
                elif int(imm) <= -16:
                    times = int(imm) // -16
                    remainder = int(imm) % -16

                    for _ in range(times):
                        instructions.append(f"ADD R6, R6, #-16")
                    
                    instructions.append(f"ADD R6, R6, #{remainder}")
                else:
                    times = int(imm) // 15
                    remainder = int(imm) % 15

                    for _ in range(times):
                        instructions.append(f"ADD R6, R6, #15")
                    
                    instructions.append(f"ADD R6, R6, #{remainder}")

                instructions.append(f"NOT R6, R6")
                instructions.append(f"ADD R6, R6, #1")
                instructions.append(f"ADD R5, R5, R6")
                instructions.append(f"STR R5, R7, {get_var_address(var)}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"AND R6, R6, #0")

            return instructions
        
        # variable += variable (same)
        m = re.match(r'^([a-zA-Z_]\w*)\s*\+=\s*([a-zA-Z_]\w*)$', line)
        if m:
            var1, var2 = m.groups()

            instructions.append(f"LDR R5, R7, {get_var_address(var1)}")
            instructions.append(f"ADD R5, R5, R5")
            instructions.append(f"STR R5, R7, {get_var_address(var1)}")

            return instructions
        
        # variable -= variable (same)
        m = re.match(r'^([a-zA-Z_]\w*)\s*-\=\s*([a-zA-Z_]\w*)$', line)
        if m:
            var1, var2 = m.groups()
            
            instructions.append(f"AND R5, R5, #0")
            instructions.append(f"STR R5, R7, {get_var_address(var1)}")

            return instructions
        
    raise ValueError(f"Invalid operation in line: {line}")

def compile_condition(condition: str) -> list[str]:
    instructions: list[str] = []
    m: re.Match[str] | None = re.match(r'^([Rr]\d+|[A-Za-z_]\w*|-?\d+)\s*(==|!=|<=|<|>|>=)\s*([Rr]\d+|[A-Za-z_]\w*|-?\d+)$', condition)
    if m:
        operand: str; op: str; value: str
        operand, op, value = m.groups()
        
        # If both LHS and RHS are registers
        if operand.startswith("R") and value.startswith("R"):
            if op == "==":
                label_true: str = get_unique_label("L")
                label_end: str = get_unique_label("L")

                instructions.append(f"NOT R5, {value}")       # Bitwise complement of value is taken
                instructions.append(f"ADD R5, R5, #1")        # Two's complement of value is taken
                instructions.append(f"ADD R5, {operand}, R5") # R5 = operand + R5 (-value)

                instructions.append(f"BRz {label_true}")      # if zero, condition true
                instructions.append(f"AND R5, R5, #0")        # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")        # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "!=":
                label_false: str = get_unique_label("L")
                label_end = get_unique_label("L")
                
                instructions.append(f"NOT R5, {value}")       # Bitwise complement of value is taken
                instructions.append(f"ADD R5, R5, #1")        # Two's complement of value is taken
                instructions.append(f"ADD R5, {operand}, R5") # R5 = operand + R5 (-value)

                instructions.append(f"BRz {label_false}")     # if zero, condition false
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")        # true branch
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_false}")
                instructions.append(f"AND R5, R5, #0")        # false branch
                instructions.append(f"{label_end}")
            elif op == "<":
                label_true = get_unique_label(prefix="L")
                label_end = get_unique_label("L")

                instructions.append(f"NOT R5, {value}")       # Bitwise complement of value is taken
                instructions.append(f"ADD R5, R5, #1")        # Two's complement of value is taken
                instructions.append(f"ADD R5, {operand}, R5") # R5 = operand + R5 (-value)

                instructions.append(f"BRn {label_true}")      # if negative, condition true
                instructions.append(f"AND R5, R5, #0")        # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")        # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "<=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"NOT R5, {value}")       # Bitwise complement of value is taken
                instructions.append(f"ADD R5, R5, #1")        # Two's complement of value is taken
                instructions.append(f"ADD R5, {operand}, R5") # R5 = operand + R5 (-value)

                instructions.append(f"BRnz {label_true}")     # if negative or zero, condition true
                instructions.append(f"AND R5, R5, #0")        # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")        # true: set to 1
                instructions.append(f"{label_end}")
            elif op == ">=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"NOT R5, {value}")       # Bitwise complement of value is taken
                instructions.append(f"ADD R5, R5, #1")        # Two's complement of value is taken
                instructions.append(f"ADD R5, {operand}, R5") # R5 = operand + R5 (-value)

                instructions.append(f"BRzp {label_true}")     # if positive or zero, condition true
                instructions.append(f"AND R5, R5, #0")        # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")        # true: set to 1
                instructions.append(f"{label_end}")
            else: # op == ">"
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"NOT R5, {value}")       # Bitwise complement of value is taken
                instructions.append(f"ADD R5, R5, #1")        # Two's complement of value is taken
                instructions.append(f"ADD R5, {operand}, R5") # R5 = operand + R5 (-value)

                instructions.append(f"BRp {label_true}")      # if positive, condition true
                instructions.append(f"AND R5, R5, #0")        # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")        # true: set to 1
                instructions.append(f"{label_end}")
        # If LHS is a register, and RHS is a variable
        elif operand.startswith("R") and (not value.isnumeric()):
            value_ref: str = get_var_address(value)

            if op == "==":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {value_ref}")   # Value is loaded from value_ref into R5
                instructions.append(f"NOT R5, R5")                # Bitwise complement of R5 is taken
                instructions.append(f"ADD R5, R5, #1")            # Two's complement of R5 is taken
                instructions.append(f"ADD R5, {operand}, R5")     # R5 = operand + R5 (-value)

                instructions.append(f"BRz {label_true}")          # if zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "!=":
                label_false = get_unique_label("L")
                label_end = get_unique_label("L")
                
                instructions.append(f"LDR R5, R7, {value_ref}")   # Value is loaded from value_ref into R5
                instructions.append(f"NOT R5, R5")                # Bitwise complement of R5 is taken
                instructions.append(f"ADD R5, R5, #1")            # Two's complement of R5 is taken
                instructions.append(f"ADD R5, {operand}, R5")     # R5 = operand + R5 (-value)

                instructions.append(f"BRz {label_false}")         # if zero, condition false
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true branch
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_false}")
                instructions.append(f"AND R5, R5, #0")            # false branch
                instructions.append(f"{label_end}")
            elif op == "<":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")
                
                instructions.append(f"LDR R5, R7, {value_ref}")   # Value is loaded from value_ref into R5
                instructions.append(f"NOT R5, R5")                # Bitwise complement of R5 is taken
                instructions.append(f"ADD R5, R5, #1")            # Two's complement of R5 is taken
                instructions.append(f"ADD R5, {operand}, R5")     # R5 = operand + R5 (-value)

                instructions.append(f"BRn {label_true}")          # if negative, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "<=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {value_ref}")   # Value is loaded from value_ref into R5
                instructions.append(f"NOT R5, R5")                # Bitwise complement of R5 is taken
                instructions.append(f"ADD R5, R5, #1")            # Two's complement of R5 is taken
                instructions.append(f"ADD R5, {operand}, R5")     # R5 = operand + R5 (-value)

                instructions.append(f"BRnz {label_true}")         # if negative or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == ">=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {value_ref}")   # Value is loaded from value_ref into R5
                instructions.append(f"NOT R5, R5")                # Bitwise complement of R5 is taken
                instructions.append(f"ADD R5, R5, #1")            # Two's complement of R5 is taken
                instructions.append(f"ADD R5, {operand}, R5")     # R5 = operand + R5 (-value)

                instructions.append(f"BRzp {label_true}")         # if positive or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            else: # op == ">"
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")
                
                instructions.append(f"LDR R5, R7, {value_ref}")   # Value is loaded from value_ref into R5
                instructions.append(f"NOT R5, R5")                # Bitwise complement of R5 is taken
                instructions.append(f"ADD R5, R5, #1")            # Two's complement of R5 is taken
                instructions.append(f"ADD R5, {operand}, R5")     # R5 = operand_ref + R5 (-value)

                instructions.append(f"BRp {label_true}")          # if positive, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
        # If LHS is a register, and RHS is a constant
        elif operand.startswith("R") and value.isnumeric():
            if op == "==":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {operand}")
                # subtract constant
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times: int = int(value) // -16
                        remainder: int = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRz {label_true}")          # if zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "!=":
                label_false = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {operand}")
                # subtract constant
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRz {label_false}")         # if zero, condition false
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true branch
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_false}")
                instructions.append(f"AND R5, R5, #0")            # false branch
                instructions.append(f"{label_end}")
            elif op == "<":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {operand}")
                # subtract constant
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRn {label_true}")          # Branch if negative
                instructions.append(f"AND R5, R5, #0")            # Otherwise, clean R5
                instructions.append(f"BR {label_end}")            # Continue from the ending part
                instructions.append(f"{label_true}")              # The section where the condition is true starts
                instructions.append(f"AND R5, R5, #0")            # R5 is cleaned
                instructions.append(f"ADD R5, R5, #1")            # R5 is set to 1
                instructions.append(f"{label_end}")               # The end part starts
            elif op == "<=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {operand}")
                # subtract constant
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRnz {label_true}")         # Branch if negative or zero
                instructions.append(f"AND R5, R5, #0")            # Otherwise, clean R5
                instructions.append(f"BR {label_end}")            # Continue from the ending part
                instructions.append(f"{label_true}")              # The section where the condition is true starts
                instructions.append(f"AND R5, R5, #0")            # R5 is cleaned
                instructions.append(f"ADD R5, R5, #1")            # R5 is set to 1
                instructions.append(f"{label_end}")               # The end part starts
            elif op == ">=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {operand}")
                # subtract constant
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRzp {label_true}")         # Branch if positive or zero
                instructions.append(f"AND R5, R5, #0")            # Otherwise, clean R5
                instructions.append(f"BR {label_end}")            # Continue from the ending part
                instructions.append(f"{label_true}")              # The section where the condition is true starts
                instructions.append(f"AND R5, R5, #0")            # R5 is cleaned
                instructions.append(f"ADD R5, R5, #1")            # R5 is set to 1
                instructions.append(f"{label_end}")               # The end part starts
            else: # op == ">"
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {operand}")
                # subtract constant
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRp {label_true}")          # Branch if positive
                instructions.append(f"AND R5, R5, #0")            # Otherwise, clean R5
                instructions.append(f"BR {label_end}")            # Continue from the ending part
                instructions.append(f"{label_true}")              # The section where the condition is true starts
                instructions.append(f"AND R5, R5, #0")            # R5 is cleaned
                instructions.append(f"ADD R5, R5, #1")            # R5 is set to 1
                instructions.append(f"{label_end}")               # The end part starts

        # If LHS is a variable, and RHS is a register
        elif (not operand.startswith("R")) and (not operand.isnumeric()) and value.startswith("R"):
            operand_ref: str = get_var_address(operand)

            if op == "==":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}") # Value of operand is loaded into R5
                instructions.append(f"AND R6, R6, #0")
                instructions.append(f"ADD R6, R6, {value}")
                instructions.append(f"NOT R6, R6")      # Bitwise complement of value is taken
                instructions.append(f"ADD R6, R6, #1")  # Two's complement of value is taken
                instructions.append(f"ADD R5, R5, R6")       # R5 = R5 (operand) + (-value)
                
                instructions.append(f"BRz {label_true}")          # if zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "!=":
                label_false = get_unique_label("L")
                label_end = get_unique_label("L")
                
                instructions.append(f"LDR R5, R7, {operand_ref}") # Value of operand is loaded into R5
                instructions.append(f"AND R6, R6, #0")
                instructions.append(f"ADD R6, R6, {value}")
                instructions.append(f"NOT R6, R6")      # Bitwise complement of value is taken
                instructions.append(f"ADD R6, R6, #1")  # Two's complement of value is taken
                instructions.append(f"ADD R5, R5, R6")       # R5 = R5 (operand) + (-value)

                instructions.append(f"BRz {label_false}")         # if zero, condition false
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true branch
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_false}")
                instructions.append(f"AND R5, R5, #0")            # false branch
                instructions.append(f"{label_end}")
            elif op == "<":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}") # Value of operand is loaded into R5
                instructions.append(f"AND R6, R6, #0")
                instructions.append(f"ADD R6, R6, {value}")
                instructions.append(f"NOT R6, R6")      # Bitwise complement of value is taken
                instructions.append(f"ADD R6, R6, #1")  # Two's complement of value is taken
                instructions.append(f"ADD R5, R5, R6")       # R5 = R5 (operand) + (-value)

                instructions.append(f"BRn {label_true}")          # if negative, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "<=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}") # Value of operand is loaded into R5
                instructions.append(f"AND R6, R6, #0")
                instructions.append(f"ADD R6, R6, {value}")
                instructions.append(f"NOT R6, R6")      # Bitwise complement of value is taken
                instructions.append(f"ADD R6, R6, #1")  # Two's complement of value is taken
                instructions.append(f"ADD R5, R5, R6")       # R5 = R5 (operand) + (-value)

                instructions.append(f"BRnz {label_true}")         # if negative or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == ">=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}") # Value of operand is loaded into R5
                instructions.append(f"AND R6, R6, #0")
                instructions.append(f"ADD R6, R6, {value}")
                instructions.append(f"NOT R6, R6")      # Bitwise complement of value is taken
                instructions.append(f"ADD R6, R6, #1")  # Two's complement of value is taken
                instructions.append(f"ADD R5, R5, R6")       # R5 = R5 (operand) + (-value)
                
                instructions.append(f"BRzp {label_true}")         # if positive or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            else: # op == ">"
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}") # Value of operand is loaded into R5
                instructions.append(f"AND R6, R6, #0")
                instructions.append(f"ADD R6, R6, {value}")
                instructions.append(f"NOT R6, R6")      # Bitwise complement of value is taken
                instructions.append(f"ADD R6, R6, #1")  # Two's complement of value is taken
                instructions.append(f"ADD R5, R5, R6")       # R5 = R5 (operand) + (-value)
                
                instructions.append(f"BRp {label_true}")          # if positive, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
        # If both LHS and RHS are variables
        elif (not operand.startswith("R")) and (not operand.isnumeric()) and (not value.startswith("R")) and (not value.isnumeric()):
            operand_ref = get_var_address(operand)
            value_ref = get_var_address(value)

            if op == "==":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}")
                instructions.append(f"LDR R6, R7, {value_ref}")
                instructions.append(f"NOT R6, R6")
                instructions.append(f"ADD R6, R6, #1")
                instructions.append(f"ADD R5, R5, R6")
                
                instructions.append(f"BRz {label_true}")          # if zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "!=":
                label_false = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}")
                instructions.append(f"LDR R6, R7, {value_ref}")
                instructions.append(f"NOT R6, R6")
                instructions.append(f"ADD R6, R6, #1")
                instructions.append(f"ADD R5, R5, R6")
                
                instructions.append(f"BRz {label_false}")         # if zero, condition false
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true branch
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_false}")
                instructions.append(f"AND R5, R5, #0")            # false branch
                instructions.append(f"{label_end}")
            elif op == "<":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}")
                instructions.append(f"LDR R6, R7, {value_ref}")
                instructions.append(f"NOT R6, R6")
                instructions.append(f"ADD R6, R6, #1")
                instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRn {label_true}")          # if negative, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "<=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}")
                instructions.append(f"LDR R6, R7, {value_ref}")
                instructions.append(f"NOT R6, R6")
                instructions.append(f"ADD R6, R6, #1")
                instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRnz {label_true}")         # if negative or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == ">=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}")
                instructions.append(f"LDR R6, R7, {value_ref}")
                instructions.append(f"NOT R6, R6")
                instructions.append(f"ADD R6, R6, #1")
                instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRzp {label_true}")         # if positive or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            else: # op == ">"
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}")
                instructions.append(f"LDR R6, R7, {value_ref}")
                instructions.append(f"NOT R6, R6")
                instructions.append(f"ADD R6, R6, #1")
                instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRp {label_true}")          # if positive, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")

        # If LHS is a variable, and RHS is a constant
        elif (not operand.startswith("R")) and (not operand.isnumeric()) and value.isnumeric():
            operand_ref = get_var_address(operand)

            if op == "==":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}")

                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")
                
                instructions.append(f"BRz {label_true}")          # if zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "!=":
                label_false = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}")

                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRz {label_false}")         # if zero, condition false
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true branch
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_false}")
                instructions.append(f"AND R5, R5, #0")            # false branch
                instructions.append(f"{label_end}")
            elif op == "<":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}")
                
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRn {label_true}")          # if negative, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "<=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}")
                
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRnz {label_true}")         # if negative or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == ">=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}")
                
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRzp {label_true}")         # if positive or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            else: # op == ">"
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {operand_ref}")
                
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRp {label_true}")          # if positive, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
        # If LHS is a constant, and RHS is a register
        elif operand.isnumeric() and value.startswith("R"):
            if op == "==":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")
                
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {value}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")

                if operand != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R6, R6, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")
                
                instructions.append(f"BRz {label_true}")          # if zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "!=":
                label_false = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {value}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")

                if operand != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R6, R6, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRz {label_false}")         # if zero, condition false
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true branch
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_false}")
                instructions.append(f"AND R5, R5, #0")            # false branch
                instructions.append(f"{label_end}")
            elif op == "<":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {value}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")

                if operand != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R6, R6, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRn {label_true}")          # if negative, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "<=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {value}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")

                if operand != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R6, R6, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRnz {label_true}")         # if negative or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == ">=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {value}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")

                if operand != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R6, R6, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRzp {label_true}")         # if positive or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == ">":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, {value}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")

                if operand != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R6, R6, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRp {label_true}")          # if positive, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
        # If LHS is a constant, and RHS is a variable
        elif operand.isnumeric() and (not value.isnumeric()):
            value_ref = get_var_address(value)

            if op == "==":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {value_ref}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")

                if operand != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R6, R6, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"ADD R5, R5, R6")
                
                instructions.append(f"BRz {label_true}")          # if zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "!=":
                label_false = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {value_ref}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")

                if operand != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R6, R6, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRz {label_false}")         # if zero, condition false
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true branch
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_false}")
                instructions.append(f"AND R5, R5, #0")            # false branch
                instructions.append(f"{label_end}")
            elif op == "<":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {value_ref}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")
                
                if operand != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R6, R6, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRn {label_true}")          # if negative, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1,
                instructions.append(f"{label_end}")
            elif op == "<=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {value_ref}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")

                if operand != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R6, R6, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRnz {label_true}")         # if negative or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == ">=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {value_ref}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")

                if operand != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R6, R6, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRzp {label_true}")         # if positive or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            else: # op == ">"
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                instructions.append(f"LDR R5, R7, {value_ref}")
                instructions.append(f"NOT R5, R5")
                instructions.append(f"ADD R5, R5, #1")
                
                if operand != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R6, R6, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRp {label_true}")          # if positive, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
        # Continue from here
        # If both LHS and RHS are constants
        elif operand.isnumeric() and value.isnumeric():
            if op == "==":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                # operand is loaded into R5
                if operand != "0":
                    instructions.append(f"AND R5, R5, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R5, R5, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #-16")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #15")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")

                # value is loaded into R6
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    # R5 = R5 (operand) + R6 (-value)
                    instructions.append(f"ADD R5, R5, R6")
                
                instructions.append(f"BRz {label_true}")          # if zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "!=":
                label_false = get_unique_label("L")
                label_end = get_unique_label("L")

                # operand is loaded into R5
                if operand != "0":
                    instructions.append(f"AND R5, R5, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R5, R5, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #-16")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #15")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                
                # value is loaded into R6
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    # R5 = R5 (operand) + R6 (-value)
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRz {label_false}")         # if zero, condition false
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true branch
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_false}")
                instructions.append(f"AND R5, R5, #0")            # false branch
                instructions.append(f"{label_end}")
            elif op == "<":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                # operand is loaded into R5
                if operand != "0":
                    instructions.append(f"AND R5, R5, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R5, R5, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #-16")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #15")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                
                # value is loaded into R6
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    # R5 = R5 (operand) + R6 (-value)
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRn {label_true}")          # if negative, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == "<=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                # operand is loaded into R5
                if operand != "0":
                    instructions.append(f"AND R5, R5, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R5, R5, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #-16")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #15")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                
                # value is loaded into R6
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    # R5 = R5 (operand) + R6 (-value)
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRnz {label_true}")         # if negative or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            elif op == ">=":
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                # operand is loaded into R5
                if operand != "0":
                    instructions.append(f"AND R5, R5, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R5, R5, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #-16")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #15")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                
                # value is loaded into R6
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    # R5 = R5 (operand) + R6 (-value)
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRzp {label_true}")         # if positive or zero, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")
            else: # op == ">"
                label_true = get_unique_label("L")
                label_end = get_unique_label("L")

                # operand is loaded into R5
                if operand != "0":
                    instructions.append(f"AND R5, R5, #0")
                    if (int(operand) >= -16) and (int(operand) <= 15):
                        instructions.append(f"ADD R5, R5, #{operand}")
                    elif int(operand) < -16:
                        times = int(operand) // -16
                        remainder = int(operand) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #-16")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                    else:
                        times = int(operand) // 15
                        remainder = int(operand) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R5, R5, #15")
                        
                        instructions.append(f"ADD R5, R5, #{remainder}")
                
                # value is loaded into R6
                if value != "0":
                    instructions.append(f"AND R6, R6, #0")
                    if (int(value) >= -16) and (int(value) <= 15):
                        instructions.append(f"ADD R6, R6, #{value}")
                    elif int(value) < -16:
                        times = int(value) // -16
                        remainder = int(value) % -16

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #-16")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    else:
                        times = int(value) // 15
                        remainder = int(value) % 15

                        for _ in range(times):
                            instructions.append(f"ADD R6, R6, #15")
                        
                        instructions.append(f"ADD R6, R6, #{remainder}")
                    
                    instructions.append(f"NOT R6, R6")
                    instructions.append(f"ADD R6, R6, #1")
                    # R5 = R5 (operand) + R6 (-value)
                    instructions.append(f"ADD R5, R5, R6")

                instructions.append(f"BRp {label_true}")          # if positive, condition true
                instructions.append(f"AND R5, R5, #0")            # false: set to 0
                instructions.append(f"BR {label_end}")
                instructions.append(f"{label_true}")
                instructions.append(f"AND R5, R5, #0")
                instructions.append(f"ADD R5, R5, #1")            # true: set to 1
                instructions.append(f"{label_end}")

    else:
        raise ValueError(f"Invalid condition statement: {condition}")
    
    return instructions

def compile(filename: str) -> None:
    if not filename.endswith(".lc3"):
        print("Error: Provide an .lc3 file")
        exit(os.EX_SOFTWARE)

    try:
        with open(filename, "r") as file_to_read:
            content_read: list[str] = file_to_read.readlines()

            # Keys for the dictionaries which are the elements of the stack:
            # For if/if-else blocks:
                # type ("if"), else (the label value), end (the label value), processed_else (boolean)
            # For while blocks:
                # type ("while"), start (the label value), end (the label value)
            block_stack: list[dict[str, str]] = []
            
            content_to_write: list[str] = [".ORIG x3000\n"]
            
            # Load x4000 into R7
            content_to_write.append("AND R7, R7, #0\n")      # x0
            content_to_write.append("ADD R7, R7, #1\n")      # x1
            content_to_write.append("ADD R7, R7, R7\n")      # x2
            content_to_write.append("ADD R7, R7, R7\n")      # x4
            content_to_write.append("ADD R7, R7, R7\n")      # x8
            content_to_write.append("ADD R7, R7, R7\n")      # x10
            content_to_write.append("ADD R7, R7, R7\n")      # x20
            content_to_write.append("ADD R7, R7, R7\n")      # x40
            content_to_write.append("ADD R7, R7, R7\n")      # x80
            content_to_write.append("ADD R7, R7, R7\n")      # x100
            content_to_write.append("ADD R7, R7, R7\n")      # x200
            content_to_write.append("ADD R7, R7, R7\n")      # x400
            content_to_write.append("ADD R7, R7, R7\n")      # x800
            content_to_write.append("ADD R7, R7, R7\n")      # x1000
            content_to_write.append("ADD R7, R7, R7\n")      # x2000
            content_to_write.append("ADD R7, R7, R7\n")      # x4000
            
            for line in content_read:
                line: str = line.strip()
                if line == "":
                    continue
                # Single-line comments are allowed through the delimiter //
                elif line.startswith("//"):
                    continue
                elif "//" in line:
                    line = line[:line.find("//")].strip()
                
                if (not line.startswith("if")) and (not line.startswith("else")) and (not line.startswith("while")) and (not line.startswith("end")):
                    transpiled_lines: list[str] = compile_line(line)
                    
                    for instr in transpiled_lines:
                        content_to_write.append(f"{instr}\n")
                    continue

                elif line.startswith("while"):
                    # Labels for the beginning and end of the while block
                    start_label: str = get_unique_label("L")
                    end_label: str = get_unique_label("L")

                    # Emit the start label
                    content_to_write.append(f"{start_label}\n")
                    
                    # Compile the condition for the while loop
                    condition: str = line[6:].strip().strip("()")
                    content_to_write.extend(f"{instr}\n" for instr in compile_condition(condition))
                    
                    # If condition false, branch to the end label.
                    content_to_write.append(f"BRz {end_label}\n")
                    
                    # Push the while block onto the block stack
                    block_stack.append({"type": "while", "start": start_label, "end": end_label})
                
                elif line.startswith("if"):
                    # Create labels for the condition, else branch and the end of the block
                    cond_label: str = get_unique_label("L")
                    else_label: str = get_unique_label("L")
                    end_label = get_unique_label("L")

                    # Emit the condition label
                    content_to_write.append(f"{cond_label}\n")
                    condition = line[2:].strip().strip("()")
                    content_to_write.extend(f"{instr}\n" for instr in compile_condition(condition))

                    # If condition is false, branch to the else label
                    content_to_write.append(f"BRz {else_label}\n")

                    # Push the if-else block onto the stack
                    block_stack.append({"type": "if", "else": else_label, "end": end_label, "processed_else": False})

                elif line.startswith("else"):
                    # Make sure an 'if' block exists.
                    if not block_stack or block_stack[-1]["type"] != "if":
                        raise ValueError("Unexpected else without matching if")
                    
                    block: dict[str, str] = block_stack[-1]

                    # Finish the if part of the if-else block by jumping to the end label
                    content_to_write.append(f"BR {block["end"]}\n")

                    # Emit the else label
                    content_to_write.append(f"{block["else"]}\n")
                    block["processed_else"] = True

                elif line.startswith("end"):
                    if not block_stack:
                        raise ValueError("Unexpected end without a matching block")
                    
                    block = block_stack.pop()
                    
                    if block["type"] == "if":
                        # If an else label was never emitted (e.g., an if block without an else was encountered),
                        # emit the previously assigned else label here
                        if not block.get("processed_else", False):
                            content_to_write.append(f"{block["else"]}\n")

                        # Emit the common end label for the if/if-else block
                        content_to_write.append(f"{block["end"]}\n")
                    
                    elif block["type"] == "while":
                        # At the end of the while block, go back to the beginning of the while block
                        content_to_write.append(f"BR {block["start"]}\n")

                        # Emit the exit label for the while block (the end part)
                        content_to_write.append(f"{block["end"]}\n")
        
        content_to_write.append("YIELD\n")        
        content_to_write.append("HALT\n")
        content_to_write.append(".END\n")

    except Exception as err:
        print(f"Error: {err}")
        exit(os.EX_IOERR)

    try:
        asm_filename: str = filename.replace(".lc3", ".asm")
        with open(asm_filename, "w") as file_to_write:
            file_to_write.writelines(content_to_write)
            generate_heap(filename, heap_init)

        return asm_filename
    except Exception as err:
        print(f"Error: {err}")
        exit(os.EX_CANTCREAT)

# Written by Onur Orman.
def generate_heap(filename: str, init_lines: list[str]) -> None:
    try:
        with open(filename.replace(".lc3", "_heap.obj"), "wb") as file_to_write:
            content_to_write: list[bytes] = []
            for init_line in init_lines:
                # variable = constant
                m: re.Match[str] | None = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(\d+)$', init_line)
                if m:
                    _: str; imm: str
                    _, imm = m.groups()

                    if (int(imm) < ((-1) * pow(2, 16))) or (int(imm) > (pow(2, 16) - 1)):
                        raise ValueError(f"Value {imm} outside the range for 16-bit numbers")

                    value: int = int(imm)
                    content_to_write.append(struct.pack("<H", value))
                    continue

                # variable = constant + constant
                m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(\d+)\s*\+\s*(\d+)$', init_line)
                if m:
                    imm1: str; imm2: str
                    _, imm1, imm2 = m.groups()

                    if (int(imm1) < ((-1) * pow(2, 16))) or (int(imm1) > (pow(2, 16) - 1)):
                        raise ValueError(f"Value {imm1} outside the range for 16-bit numbers")
                    elif (int(imm2) < ((-1) * pow(2, 16))) or (int(imm2) > (pow(2, 16) - 1)):
                        raise ValueError(f"Value {imm2} outside the range for 16-bit numbers")

                    value = int(imm1) + int(imm2)

                    if (value < ((-1) * pow(2, 16))) or (value > (pow(2, 16) - 1)):
                        raise ValueError(f"Value {value} outside the range for 16-bit numbers")

                    content_to_write.append(struct.pack("<H", value))
                    continue

                # variable = constant - constant
                m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(\d+)\s*\-\s*(\d+)$', init_line)
                if m:
                    _, imm1, imm2 = m.groups()

                    if (int(imm1) < ((-1) * pow(2, 16))) or (int(imm1) > (pow(2, 16) - 1)):
                        raise ValueError(f"Value {imm1} outside the range for 16-bit numbers")
                    elif (int(imm2) < ((-1) * pow(2, 16))) or (int(imm2) > (pow(2, 16) - 1)):
                        raise ValueError(f"Value {imm2} outside the range for 16-bit numbers")

                    value = int(imm1) - int(imm2)

                    if (value < ((-1) * pow(2, 16))) or (value > (pow(2, 16) - 1)):
                        raise ValueError(f"Value {value} outside the range for 16-bit numbers")

                    content_to_write.append(struct.pack("<H", value))
                    continue

            file_to_write.writelines(content_to_write)
    except Exception as err:
        print(f"Error: {err}")
        exit(os.EX_CANTCREAT)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Error: Provide a valid .lc3 file as the argument")
        exit(os.EX_USAGE)

    compile(sys.argv[1])