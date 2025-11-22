import os
import glob
import subprocess
import json
import datetime as dt

def today_dir(base):
    d = dt.datetime.utcnow().strftime('%Y%m%d')
    p = os.path.join(base, d)
    return p

def test_generate_audio_writes_audio_path():
    subprocess.call(['python', 'scripts/run_ingest.py'])
    subprocess.call(['python', 'scripts/format_metadata.py'])
    rc = subprocess.call(['python', 'scripts/generate_audio.py', '--avatar', 'test', '--voice', 'default', '--limit', '1'])
    assert rc == 0
    proc = today_dir(os.path.join('data','processed'))
    files = sorted(glob.glob(os.path.join(proc, 'item_*.json')))
    assert len(files) > 0
    with open(files[0], 'r', encoding='utf-8') as f:
        obj = json.load(f)
    ap = obj.get('audio_path')
    assert ap
    assert os.path.exists(ap)