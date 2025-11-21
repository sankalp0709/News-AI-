import os
import sys
import json
import time
import subprocess
import datetime as dt
import logging
from logging.handlers import RotatingFileHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

def _init_logging():
    app_path = os.path.join(ROOT, "logs", "scheduler.log")
    err_path = os.path.join(ROOT, "logs", "errors.log")
    os.makedirs(os.path.dirname(app_path), exist_ok=True)
    fh = RotatingFileHandler(app_path, maxBytes=1024*1024, backupCount=3)
    eh = RotatingFileHandler(err_path, maxBytes=1024*1024, backupCount=3)
    logging.basicConfig(level=logging.INFO, handlers=[fh])
    elog = logging.getLogger("errors")
    elog.setLevel(logging.ERROR)
    elog.addHandler(eh)

def log(msg):
    logging.getLogger().info(msg)

def run(cmd):
    try:
        log(f"RUN {cmd}")
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        msg = f"EXIT {r.returncode} STDOUT={r.stdout.strip()} STDERR={r.stderr.strip()}"
        if r.returncode != 0:
            logging.getLogger("errors").error(msg)
        else:
            log(msg)
        return r.returncode == 0
    except Exception as e:
        logging.getLogger("errors").error(f"ERROR {cmd} {e}")
        return False

def pipeline(avatars):
    ok = True
    ok &= run([PY, os.path.join(ROOT, "scripts", "run_ingest.py")])
    ok &= run([PY, os.path.join(ROOT, "scripts", "format_metadata.py")])
    for a in avatars:
        ok &= run([PY, os.path.join(ROOT, "scripts", "generate_audio.py"), "--avatar", a, "--voice", "default", "--limit", "10"])
    ok &= run([PY, os.path.join(ROOT, "scripts", "smart_feed.py")])
    return ok

def interval_seconds(name):
    if name == "hourly":
        return 3600
    if name == "4h":
        return 4*3600
    if name == "daily":
        return 24*3600
    return 3600

def main():
    _init_logging()
    mode = os.environ.get("SCHED_MODE", "once")
    interval = os.environ.get("SCHED_INTERVAL", "hourly")
    avatars = (os.environ.get("SCHED_AVATARS", "vaani").split(","))
    avatars = [x.strip() for x in avatars if x.strip()]
    log(f"START mode={mode} interval={interval} avatars={avatars}")
    if mode == "once":
        pipeline(avatars)
        log("DONE once")
        print(json.dumps({"ok": True, "mode": mode, "interval": interval}))
        return
    sec = interval_seconds(interval)
    while True:
        ok = pipeline(avatars)
        log(f"DONE cycle ok={ok}")
        time.sleep(sec)

if __name__ == "__main__":
    main()