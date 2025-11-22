import os
import glob
import subprocess
import json
import datetime as dt

def today_dir(base):
    d = dt.datetime.utcnow().strftime('%Y%m%d')
    p = os.path.join(base, d)
    return p

def test_run_ingest_creates_raw_files():
    rc = subprocess.call(['python', 'scripts/run_ingest.py'])
    assert rc == 0
    raw = today_dir(os.path.join('data','raw'))
    files = glob.glob(os.path.join(raw, 'rss_*.json'))
    assert len(files) > 0
    with open(files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert isinstance(data.get('items'), list)