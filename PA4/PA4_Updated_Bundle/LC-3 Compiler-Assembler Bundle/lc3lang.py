# The unified interface for lc3c, the compiler for LC-3 Language, and lc3a, the LC-3 assembler

# Invocation on terminal: python3 lc3lang.py <filename.lc3>
# Going to generate filename.asm, filename_heap.obj, and filename_code.obj

# If you want to invoke the compiler and assembler separately:
# Run the compiler: python3 lc3c.py <filename.lc3>
    # Going to generate filename.asm and filename_heap.obj
# Run the assembler: python3 lc3a.py <filename.asm>
    # Going to generate filename_code.obj

import os
import sys

from lc3c import compile
from lc3a import assemble

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Error: Provide a valid .lc3 file as the argument")
        exit(os.EX_USAGE)

    asm_filename: str = compile(sys.argv[1])
    assemble(asm_filename)