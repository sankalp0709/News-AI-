import os
import sys
import json
import glob
import time
import subprocess
import datetime as dt

def run(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    out, _ = p.communicate()
    return p.returncode, out.decode('utf-8', errors='ignore')

def today_dir(base):
    d = dt.datetime.utcnow().strftime('%Y%m%d')
    p = os.path.join(base, d)
    return p

def start_server():
    p = subprocess.Popen(['python','scripts/api_server.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(1.5)
    return p

def stop_server(p):
    try:
        p.terminate()
    except Exception:
        pass

def main():
    rep = {}
    rc, _ = run('python scripts/run_ingest.py')
    rep['ingest_rc'] = rc
    rc, _ = run('python scripts/format_metadata.py')
    rep['format_rc'] = rc
    rc, _ = run('python scripts/generate_audio.py --avatar dev --voice default --limit 3')
    rep['audio_rc'] = rc
    rc, _ = run('python scripts/smart_feed.py')
    rep['rank_rc'] = rc
    srv = start_server()
    try:
        proc = today_dir(os.path.join('data','processed'))
        files = glob.glob(os.path.join(proc, 'item_*.json'))
        item_id = None
        if files:
            with open(files[0],'r',encoding='utf-8') as f:
                obj = json.load(f)
                item_id = obj.get('id')
        import requests
        if item_id:
            payload = {"id": item_id, "item": {"priority_score": 0.8}, "signals": {"user_like": True}}
            r = requests.post('http://127.0.0.1:8000/feedback', json=payload, timeout=5)
            rep['feedback_status'] = r.status_code
            rep['feedback_body'] = r.json()
    finally:
        stop_server(srv)
    out_dir = os.path.join('reports')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'integration_report.json')
    with open(out_path,'w',encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(json.dumps({'written': out_path}))

if __name__ == '__main__':
    main()