import os
import json
import time
import subprocess
import requests
import glob

def start_server():
    env = os.environ.copy()
    p = subprocess.Popen(['python','scripts/api_server.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(1.5)
    return p

def stop_server(p):
    try:
        p.terminate()
    except Exception:
        pass

def one_processed_item():
    files = glob.glob(os.path.join('data','processed','*','item_*.json'))
    if not files:
        return None
    files.sort()
    with open(files[0],'r',encoding='utf-8') as f:
        return json.load(f)

def test_feedback_and_requeue():
    subprocess.call(['python','scripts/run_ingest.py'])
    subprocess.call(['python','scripts/format_metadata.py'])
    item = one_processed_item()
    assert item is not None
    srv = start_server()
    try:
        payload = {"id": item.get("id"), "item": {"priority_score": 0.7}, "signals": {"user_like": True}}
        r = requests.post('http://127.0.0.1:8000/feedback', json=payload, timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert 'reward' in data
        assert 'action' in data
        r2 = requests.post('http://127.0.0.1:8000/requeue', json={"id": item.get("id")}, timeout=5)
        assert r2.status_code == 200
        data2 = r2.json()
        assert 'requeued' in data2
    finally:
        stop_server(srv)