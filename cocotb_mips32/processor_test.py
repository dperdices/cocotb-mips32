from typing import Text
from cocotb.triggers import Timer, Edge, First, RisingEdge
import cocotb
import random
from cocotb_mips32.utils.compiling import compile_program

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
        uut._log.debug(f"Starting clock (clock cycle={self.CLOCK_CYCLE}ns)")
        while self.clock_ticking:
            uut.Clk <= 0
            await Timer(self.CLOCK_CYCLE // 2, units="ns")
            uut.Clk <= 1
            await Timer(self.CLOCK_CYCLE // 2, units="ns")

    async def read_inst_mem(self, uut):
        """Async read instruction memory co-routine."""
        while self.clock_ticking:
            address = to_int(uut.IAddr.value)
            if address not in self.instructions:
                uut.IDataIn <= 0
            else:
                uut.IDataIn <= self.instructions[address]
            await First(Edge(uut.IAddr), Timer(self.CLOCK_CYCLE, units="ns"))

    async def read_data_mem(self, uut):
        """Async read data memory co-routine."""
        while self.clock_ticking:
            address = to_int(uut.DAddr.value)
            if address not in self.data:
                uut.DDataIn <= 0
            else:
                uut.DDataIn <= self.data[address]
            await First(Edge(uut.DAddr), Timer(self.CLOCK_CYCLE, units="ns"))

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
            self.Regs()[i] <= random.randint(lower_limit, upper_limit)

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
        uut.Reset <= 1
        uut.IDataIn <= 0
        uut.DDataIn <= 0
        uut.Clk <= 0

    async def init_processor(self, uut):
        """Initializes the processor."""
        if self.initialized:
            return
        self.uut = uut
        self.reset_processor(uut)
        await self.wait_cycles(1)
        uut.Reset <= 1
        cocotb.fork(self.clock(uut))
        cocotb.fork(self.read_data_mem(uut))
        cocotb.fork(self.read_inst_mem(uut))
        cocotb.fork(self.write_data_mem(uut))
        await self.wait_cycles(3)
        uut.Reset <= 0
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

    def register_test(self):
        """Registers the test in the module."""
        f = self.main
        self.main.__func__.__name__ = self.__class__.__name__
        self.main.__func__.__qualname__ = self.__class__.__name__
        self.main.__func__.__doc__ = self.__doc__ or self.asm_code
        globals()[self.__class__.__name__] = cocotb.test()(f)
        return globals()[self.__class__.__name__]

    async def main(self, uut):
        uut._log.info(f"{to_int(uut.IAddr.value)}")
        await self.wait_cycles(3)
        uut._log.info(f"{to_int(uut.IAddr.value)}")
        self.clock_ticking = False
        print("End of test")
