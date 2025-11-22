import os
import sys
import json
import time
import subprocess
import requests
import datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(ROOT, "reports")

def ensure_reports():
    os.makedirs(REPORTS, exist_ok=True)

def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0, r.stdout, r.stderr

def get_feed(base):
    try:
        r = requests.get(base + "/feed", timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return {"items": []}
    return {"items": []}

def main():
    ensure_reports()
    results = {"ts": dt.datetime.utcnow().isoformat()}
    ok_ing, out_ing, err_ing = run([sys.executable, os.path.join(ROOT, "scripts", "run_ingest.py")])
    ok_fmt, out_fmt, err_fmt = run([sys.executable, os.path.join(ROOT, "scripts", "format_metadata.py")])
    ok_aud, out_aud, err_aud = run([sys.executable, os.path.join(ROOT, "scripts", "generate_audio.py"), "--avatar", "vaani", "--voice", "default", "--limit", "5"])
    ok_feed, out_feed, err_feed = run([sys.executable, os.path.join(ROOT, "scripts", "smart_feed.py")])
    results["steps"] = {
        "ingest": ok_ing,
        "format_metadata": ok_fmt,
        "audio": ok_aud,
        "feed": ok_feed
    }
    base = f"http://{os.environ.get('API_HOST', '127.0.0.1')}:{os.environ.get('API_PORT', '8000')}"
    data = get_feed(base)
    items = data.get("items", [])
    results["feed_item_count"] = len(items)
    if items:
        item = items[0]
        signals = {"editor_approve": 1.0, "user_like": 0.7}
        try:
            rr = requests.post(base + "/feedback", json={"id": item.get("id"), "item": item, "signals": signals}, timeout=10)
            results["feedback_status"] = rr.status_code
        except Exception:
            results["feedback_status"] = 0
    path = os.path.join(REPORTS, "integration_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(json.dumps({"written": path, "ok": all(results["steps"].values())}))

if __name__ == "__main__":
    main()