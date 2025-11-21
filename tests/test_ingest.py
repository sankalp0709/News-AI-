import os
import sys
import glob
import subprocess
import datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def today_raw_dir():
    d = dt.datetime.utcnow().strftime("%Y%m%d")
    p = os.path.join(ROOT, "data", "raw", d)
    return p

def test_run_ingest_creates_files():
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "run_ingest.py")], check=False, cwd=ROOT)
    p = today_raw_dir()
    files = glob.glob(os.path.join(p, "rss_*.json"))
    assert len(files) >= 1