import os
import time
import json
import requests

def test_feedback_and_requeue():
    base = f"http://{os.environ.get('API_HOST', '127.0.0.1')}:{os.environ.get('API_PORT', '8000')}"
    # Health
    h = requests.get(base + "/health", timeout=5)
    assert h.status_code == 200
    # Load feed
    f = requests.get(base + "/feed", timeout=5)
    assert f.status_code == 200
    data = f.json()
    items = data.get("items", [])
    assert len(items) > 0
    item = items[0]
    signals = {"editor_approve": 1.0, "user_like": 0.5}
    r = requests.post(base + "/feedback", json={"id": item.get("id"), "item": item, "signals": signals}, timeout=5)
    assert r.status_code == 200
    time.sleep(0.3)
    rq = requests.post(base + "/requeue", json={"id": item.get("id")}, timeout=5)
    assert rq.status_code == 200