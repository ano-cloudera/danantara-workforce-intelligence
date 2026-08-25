#!/usr/bin/env python3
import argparse, os, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
VENV = HERE / '.venv-frontend'; MARKER = VENV / '.requirements-installed'

def ensure_venv():
    if not VENV.exists(): subprocess.check_call([sys.executable,'-m','venv',str(VENV)])
    py = VENV/'bin'/'python'
    if not MARKER.exists() or (HERE/'requirements.txt').stat().st_mtime > MARKER.stat().st_mtime:
        subprocess.check_call([str(py),'-m','pip','install','--upgrade','pip'])
        subprocess.check_call([str(py),'-m','pip','install','-r',str(HERE/'requirements.txt')])
        MARKER.touch()
    return py

def main():
    p=argparse.ArgumentParser(); p.add_argument('--local-port',type=int,default=8080); a=p.parse_args()
    py=ensure_venv(); port=os.getenv('CDSW_APP_PORT') or os.getenv('CML_APP_PORT') or str(a.local_port); host=os.getenv('APP_BIND_HOST','127.0.0.1')
    os.chdir(HERE); os.execv(str(py),[str(py),'-m','uvicorn','app.main:app','--host',host,'--port',str(port)])
if __name__=='__main__': main()
