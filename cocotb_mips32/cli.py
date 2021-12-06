import subprocess
import os
import tempfile
import argparse
import docker

def main():
    with tempfile.TemporaryDirectory(prefix="cocotb-mips32") as tmp_dir:
        parser = argparse.ArgumentParser(description="MIPS32 test suite")
        parser.add_argument("-m","--module", help="Python module", required=True)
        parser.add_argument("-t","--toplevel", help="Top Level entity name", default="processor")
        parser.add_argument("-s","--simulator", help="Simulator (questa or docker-questa)", default="questa")
        parser.add_argument("-d", "--rtl-dir", help="Path to the RTL folder with the vhdl source files", required=True)
        parser.add_argument("--stdout", help="stdout/stderr of the simulator", default=None)
        parser.add_argument("--docker-image", help="Docker image with cocotb and questa", default="cocotb-questa")

        args = vars(parser.parse_args())
        module, toplevel, simulator, rtl_dir = args["module"], args["toplevel"], args["simulator"], args["rtl_dir"]
        file_stdout, docker_image = args["stdout"], args["docker_image"]

        if simulator == "docker-questa":
            print("Running in docker")
            real_rtl_dir = os.path.abspath(rtl_dir)
            rtl_dir = "/rtl_dir"
            real_tmp_dir = os.path.abspath(tmp_dir)
            tmp_dir = "/tmp_dir"
            client = docker.from_env()
            fli_lib = client.containers.run(docker_image, command="cocotb-config --lib-name-path fli questa", auto_remove=True).decode("utf8").replace("\n", "")
        else:
            fli_lib = subprocess.run(["cocotb-config", "--lib-name-path", "fli", "questa"], stdout=subprocess.PIPE).stdout.decode("utf8").replace("\n", "")
        do_script = f"""# Autogenerated file
        onerror {{
        quit -f -code 1
        }}
        if [file exists {tmp_dir}/work] {{vdel -lib {tmp_dir}/work -all}}
        vlib {tmp_dir}/work
        vmap -c
        vmap work {tmp_dir}/work
        vcom -work work +acc {rtl_dir}/*.vhd
        vsim  -onfinish exit -foreign "cocotb_init {fli_lib}" work.{toplevel}
        run -all
        quit"""


        VSIM_PATH="vsim"
        env=os.environ.copy()
        env["MODULE"] = module
        env["TOPLEVEL"] = toplevel
        env["TOPLEVEL_LANG"] = "vhdl"
        cmd = [VSIM_PATH]
        cmd += ["-c", "-64"]

        if file_stdout:
            stdout, stderr = subprocess.PIPE, subprocess.STDOUT
        else:
            stdout, stderr = None, None
        
        if simulator == "docker-questa":
            vols = {
                real_tmp_dir: {
                    "bind": tmp_dir, "mode": "rw"
                },
                real_rtl_dir: {
                    "bind": rtl_dir, "mode": "ro"
                },
                os.getcwd(): {
                    "bind": "/cwd", "mode": "rw"
                }
            }
            print(env["LM_LICENSE_FILE"])
            env["PATH"] = f"{env['PATH']}:/opt/questasim/linux_x86_64"
            env["TMPDIR"] = "/tmp/"
            print(f"Running {cmd} in container")
            container = client.containers.run(docker_image, command=cmd, stdout=True, volumes=vols, stderr=True, 
                            auto_remove=False, environment=env, detach=True, stdin_open=True, 
                            cap_add=["SYS_PTRACE"], security_opt=["seccomp=unconfined"])
            # Writing to stdin
            input_socket = container.attach_socket(
                params={
                    "stdin":True,
                    "stdout":True,
                    "stderr":True,
                    "stream":True,
                },
            )
            input_socket._sock.sendall(do_script.encode("utf8"))
            container.stop()
            container.wait()
            print(container.logs().decode("utf8"))
            print(container.logs(stdout=True).decode("utf8"))
            container.remove()
            
        else:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, env=env, stderr=stderr, stdout=stdout)
            stdout, stderr = proc.communicate(do_script.encode("utf8"))
            if file_stdout:
                with open(file_stdout, "ab") as f:
                    f.write(stdout)
                    
if __name__ == "__main__":
    main()
