import os
import sys
import json
import time
import subprocess
import datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

def log(msg):
    path = os.path.join(ROOT, "logs", "scheduler.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.utcnow().isoformat()} {msg}\n")

def run(cmd):
    try:
        log(f"RUN {cmd}")
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        log(f"EXIT {r.returncode} STDOUT={r.stdout.strip()} STDERR={r.stderr.strip()}")
        return r.returncode == 0
    except Exception as e:
        log(f"ERROR {cmd} {e}")
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