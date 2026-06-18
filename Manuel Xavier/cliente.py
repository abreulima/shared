import os
import runpy

os.environ["JOGO_ONLINE"] = "1"
os.environ["JOGO_SERVIDOR_IP"] = "192.168.1.191"
os.environ.setdefault("JOGO_SERVIDOR_PORTA", "50007")

runpy.run_path("jogo.py", run_name="__main__")