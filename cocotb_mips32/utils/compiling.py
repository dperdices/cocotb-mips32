"""
Compiling utils for the testbench

Author: Daniel Perdices <daniel.perdices at uam.es>
"""
import subprocess
import tempfile

class CompileError(ValueError):
    pass

def compile_program(asm_code:str):
    """Compiles a program generating data and instructions memories.

    Args:
        asm_code (str): The ASM code

    Returns:
        (str, str): (data, instructions) memories
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        asm_filename = f"{tmpdirname}/program.s"
        obj_filename = f"{tmpdirname}/program.o"
        with open(asm_filename, "w") as f:
            f.write(asm_code)


        asm2obj(asm_filename, obj_filename)
        data, instruct =  obj2data(obj_filename), obj2text(obj_filename)
        return data, instruct


def asm2obj(filename:str, objname:str):
    """Generates the object file from the assembly file.

    Args:
        filename (str): path to the assembly file
        objname (str): path to the object file

    Raises:
        CompileError: Compiling error
    """
    command = ["mips-linux-gnu-as"] 
    command += ["-g2", "-g", "--gdwarf2", "-mips32", "-O0", "-o", objname, filename]
    proc = subprocess.run(command, capture_output=True)
    if proc.returncode != 0:
        raise CompileError(str(proc.stderr, encoding="utf8"))

def obj2data(objname:str, dataname=None):
    """Obtains the data memory from the object file.

    Args:
        objname (str): Object file path.
        dataname (str, optional): Data file path. Defaults to None.

    Raises:
        CompileError: Compiling error.

    Returns (only if dataname is None):
        str: data memory
    """
    command = ["mips-linux-gnu-objdump"]
    command += ["--full-contents",  objname]
    command += ["-j", ".data"]
    proc = subprocess.run(command, capture_output=True)
    
    if proc.returncode != 0:
        raise CompileError(str(proc.stderr, encoding="utf8"))
    
    lines = parse_full_contents(str(proc.stdout, encoding="utf8"))
    if dataname:
        with open(dataname, "w") as f:
            f.write("\n".join(lines))
    else:
        return "\n".join(lines)

def obj2text(objname, dataname=None):
    """Obtains the instruction memory from the object file.

    Args:
        objname (str): Object file path.
        dataname (str, optional): Instruction file path. Defaults to None.

    Raises:
        CompileError: Compiling error.

    Returns (only if dataname is None):
        str: instruction memory
    """
    command = ["mips-linux-gnu-objdump"]
    command += ["--full-contents",  objname]
    command += ["-j", ".text"]
    proc = subprocess.run(command, capture_output=True)
    
    if proc.returncode != 0:
        raise CompileError(str(proc.stderr, encoding="utf8"))
    lines = parse_full_contents(str(proc.stdout, encoding="utf8"))
    if dataname:
        with open(dataname, "w") as f:
            f.write("\n".join(lines))
    else:
        return "\n".join(lines)

def obj2commented(objname, commentedversion=None):
    """Obtains the commented instruction memory from the object file.

    Args:
        objname (str): Object file path.
        commentedversion (str, optional): Instruction file path. Defaults to None.

    Raises:
        CompileError: Compiling error.

    Returns (only if dataname is None):
        str: commented instruction memory
    """
    command = ["mips-linux-gnu-objdump"]
    command += ["-S",  objname]
    command += ["-j", ".text", "--source-comment=##  "]
    proc = subprocess.run(command, capture_output=True)
    
    if proc.returncode != 0:
        raise CompileError(str(proc.stderr, encoding="utf8"))
    if commentedversion:
        with open(commentedversion, "wb") as f:
            f.write(proc.stdout)
    else:
        return str(proc.stdout, encoding="utf8")

def parse_full_contents(text):
    """Parses the output of the objdump command.

    Args:
        text (str): Output of the objdump command.

    Returns:
        str: Formatted output.
    """
    res = []
    parsing = False
    for line in text.split("\n"):
        if ("Contents of section" in line) or ("Contenido de la" in line):
            parsing = True
            continue
        if parsing and len(line) > 0:
            line = line.strip()
            pieces = line.split(" ")
            address = int(pieces[0], base=16)
            for i in range(4):
                res.append("%08x\t%s" % ((address+i*4, pieces[i+1])))
    return res
