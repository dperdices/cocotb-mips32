from typing import Text
from cocotb.triggers import Timer, Edge, First, RisingEdge
import cocotb
import random
from cocotb_mips32.utils.compiling import compile_program
import json 

def to_int(a, default=0):
    """Converts a value to an integer."""
    try:
        return int(a)
    except:
        return default

    
class MIPS32ProcessorTest(object):
    CLOCK_CYCLE = 10 # ns
    data = {}
    instructions = {}
    clock_ticking = True
    data_text = None
    instructions_text = None
    asm_code = None
    asm_file = None
    initialized = False
    log_file = None
    result = "tbd"
    error = None
    t = 0
    state = []
    def __init__(self) -> None:
        # If asm_file is present, read the asm code from the file
        if self.asm_file:
            with open(self.asm_file, "r") as f:
                self.asm_code = f.read()

        # If asm_code is present, compile it and generate text and data segments
        if self.asm_code:
            data, instruct = compile_program(self.asm_code)

            self.data_text = self.data_text if self.data_text else data
            self.instructions_text = self.instructions_text or instruct

        # If data segment is present, load it
        if self.data_text:
            self.data = self.data if self.data else self.memload_from_str(self.data_text)
        
        # If instructions segment is present, load it
        if self.instructions_text:
            self.instructions = self.instructions if self.instructions else self.memload_from_str(self.instructions_text)
        super().__init__()

    async def clock(self, uut):
        """Clock co-routine."""
        self.CLOCK_CYCLE = 2*(self.CLOCK_CYCLE // 2)
        self.log.debug(f"Starting clock (clock cycle={self.CLOCK_CYCLE}ns)")
        while self.clock_ticking:
            uut.Clk.value = 0
            await Timer(self.CLOCK_CYCLE // 2, units="ns")
            if self.initialized:
                self.saveState()
            uut.Clk.value = 1
            await Timer(self.CLOCK_CYCLE // 2, units="ns")
            if self.initialized:
                self.saveState()
            self.t += 1

    def saveState(self):
        self.state.append({
            "clk": self.uut.Clk.value,
            "t": self.t,
            "PC": self.PC,
            "regs": self.Regs
        })

    async def read_inst_mem(self, uut):
        """Async read instruction memory co-routine."""
        while self.clock_ticking:
            address = to_int(uut.IAddr.value)
            if address not in self.instructions:
                uut.IDataIn.value = 0
            else:
                uut.IDataIn.value = self.instructions[address]
            await First(Edge(uut.IAddr), Timer(self.CLOCK_CYCLE // 2, units="ns"))

    async def read_data_mem(self, uut):
        """Async read data memory co-routine."""
        while self.clock_ticking:
            address = to_int(uut.DAddr.value)
            if address not in self.data:
                uut.DDataIn.value = 0
            else:
                uut.DDataIn.value = self.data[address]
            await First(Edge(uut.DAddr), Timer(self.CLOCK_CYCLE // 2, units="ns"))

    async def write_data_mem(self, uut):
        """Sync write data memory co-routine."""
        while self.clock_ticking:
            await RisingEdge(uut.Clk)
            address = to_int(uut.DAddr.value)
            if uut.DWrEn.value == 1:
                self.data[address] = int(uut.DDataOut.value)
            
    async def wait_cycles(self, n):
        """Waits for n clock cycles."""
        await Timer(n*self.CLOCK_CYCLE, units="ns")
        return None


    @property
    def PC(self):
        return self.uut.IAddr

    @property
    def regs(self):
        return self.Regs(self.uut)

    def Regs(self, uut):
        return uut.RegsMIPS.regs

    def randomized_regs(self, uut, lower_limit=1, upper_limit=2**31-1):
        """Sets a randomized register set."""
        for i in range(1, 32):
            self.Regs()[i].value = random.randint(lower_limit, upper_limit)

    def assertRegEqual(self, reg, val):
        assert self.regs[reg] == val, f"Register ${reg} is not equal to {val}, but ${reg}={int(self.regs[reg])}"

    def assertMemEqual(self, dir, val):
        true_val = self.data[dir] if dir in self.data else 0
        assert (true_val == val), f"Memory address ${dir} is not equal to {val}, but MEM[{dir}]={int(true_val)}"

    def assertPCEqual(self, val):
        assert self.PC == val, f"PC is not equal to {val}, but PC={int(self.PC)}"

    def get_regs_as_dict(self, uut):
        """Returns the registers as a dictionary."""
        res = {}
        regs = self.Regs(uut)
        for i in range(32):
            res[i] = to_int(regs[i].value)
        return res

    def compare_regs(self, regs1, regs2):
        """Compares two register dicts."""
        for i in range(32):
            if regs1[i] != regs2[i]:
                return False
        return True

    def reset_processor(self, uut):
        """Resets the processor."""
        uut.Reset.value = 1
        uut.IDataIn.value = 0
        uut.DDataIn.value = 0
        uut.Clk.value = 0

    async def init_processor(self, uut):
        """Initializes the processor."""
        if self.initialized:
            return
        self.uut = uut
        self.log = self.uut._log
        self.reset_processor(uut)
        await self.wait_cycles(1)
        uut.Reset.value = 1
        cocotb.fork(self.clock(uut))
        cocotb.fork(self.read_data_mem(uut))
        cocotb.fork(self.read_inst_mem(uut))
        cocotb.fork(self.write_data_mem(uut))
        await self.wait_cycles(3)
        self.t = 0
        self.state = []
        uut.Reset.value = 0
        self.initialized = True

    def memload_from_str(self, str):
        """Loads a memory (as a dict) from a string."""
        res = {}
        for line in str.split("\n"):
            if line[0] == "#":
                continue
            pieces = line.split("\t")
            if len(pieces) == 2:
                res[int(pieces[0], base=16)] = int(pieces[1], base=16)
        return res

    def log_result(self):
        """Logs the result to the file"""
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(f"{self.__class__.__name__}\t{self.result}\n")

    def register_test(self):
        """Registers the test in the module."""
        async def wrapper(uut):
            await self.init_processor(uut)
            try:
                await self.main(uut)
                self.result = "correct"
            except AssertionError as e:
                self.result = "error"
                self.error = e
            except Exception as e:
                self.result = "exec_error"
                self.error = e
            
            if "cocotb_result" not in globals():
                globals["cocotb_result"] = {
                    "results": []
                }
            
            globals["cocotb_result"]["result"].append({
                "name": self.__class__.__name__,
                "asm": self.asm_code,
                "data": self.data,
                "instructions": self.instructions,
                "data_text": self.data_text,
                "instructions_text": self.instructions_text,
                "state": self.state,
                "result": self.result
            })

            with open("results.json", "w") as f:
                f.write(json.dumps(globals["cocotb_result"]))
            self.log_result()
            if self.error:
                raise self.error

        f = wrapper
        f.__name__ = self.__class__.__name__
        f.__qualname__ = self.__class__.__name__
        f.__doc__ = self.__doc__ or self.asm_code
        globals()[self.__class__.__name__] = cocotb.test()(f)
        return globals()[self.__class__.__name__]

    async def main(self, uut):
        self.log.info(f"{to_int(uut.IAddr.value)}")
        await self.wait_cycles(3)
        self.log.info(f"{to_int(uut.IAddr.value)}")
        self.clock_ticking = False
        print("End of test")
