from setuptools import setup, find_packages

VERSION = "0.5.9" 
DESCRIPTION = "A MIPS32 testbench in Python based on cocotb"
LONG_DESCRIPTION = "A MIPS32 testbench in Python based on cocotb"

setup(
        name="cocotb_mips32", 
        version=VERSION,
        author="Daniel Perdices",
        author_email="<daniel.perdices@uam.es>",
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        packages=find_packages(),
        entry_points = {
            "console_scripts": ["cocotb-mips32 = cocotb_mips32.cli:main"],
        },
        install_requires=["cocotb", "docker"], # add any additional packages that 
        
)