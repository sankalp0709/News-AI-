import os
import glob
import subprocess
import json
import datetime as dt

def today_dir(base):
    d = dt.datetime.utcnow().strftime('%Y%m%d')
    p = os.path.join(base, d)
    return p

def test_format_metadata_outputs_processed_items():
    subprocess.call(['python', 'scripts/run_ingest.py'])
    rc = subprocess.call(['python', 'scripts/format_metadata.py'])
    assert rc == 0
    proc = today_dir(os.path.join('data','processed'))
    files = glob.glob(os.path.join(proc, 'item_*.json'))
    assert len(files) > 0
    with open(files[0], 'r', encoding='utf-8') as f:
        obj = json.load(f)
    assert obj.get('summary_short')
    assert obj.get('summary_medium')
    assert obj.get('language')
    assert obj.get('polarity') in {'positive','neutral','negative'}
    assert obj.get('tone')
    assert obj.get('confidence_score') is not None