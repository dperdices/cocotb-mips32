FROM ubuntu:20.04
LABEL version="0.5" maintainer="Daniel Perdices <daniel.perdices@uam.es>"
RUN apt-get update && apt-get install -y binutils-mips-linux-gnu python3 python3-pip libx11-6 libxext-dev libxft2 bash 
RUN mkdir /cwd /opt/questasim /rtl_dir /tmp_dir
ADD questasim /opt/questasim
ENV PATH="/opt/questasim/linux_x86_64/:${PATH}"
RUN pip3 install cocotb cocotb-mips32
RUN adduser nonroot
USER nonroot
WORKDIR /cwd