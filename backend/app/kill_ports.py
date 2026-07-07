import subprocess
import os

def kill_port(port):
    try:
        # Get process ID on the port
        pid_bytes = subprocess.check_output(f"lsof -t -i:{port}", shell=True)
        pids = pid_bytes.decode().strip().split("\n")
        for pid in pids:
            if pid:
                print(f"Killing process {pid} on port {port}")
                os.system(f"kill -9 {pid}")
    except Exception:
        # Port not in use or lsof failed, which is fine
        pass

if __name__ == "__main__":
    kill_port(8000)
    kill_port(3000)
    kill_port(4111)
    print("Done killing ports.")
