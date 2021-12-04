from cocotb_mips32 import MIPS32ProcessorTest
import sys

class TestInstr(MIPS32ProcessorTest):
    asm_code = """
    addi $1, $zero, 1
    """
    async def main(self, uut):
        await self.init_processor(uut)
        await self.wait_cycles(1)
        assert self.regs[1] == 1
        assert self.PC == 4

this = sys.modules[__name__]
setattr(this, "test_inst", TestInstr().register_test())
