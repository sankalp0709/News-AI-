import os
import json
import datetime as dt
import hashlib

DEFAULT_WEIGHTS = {
    "editor_approve": 1.0,
    "user_like": 0.6,
    "user_skip": -0.4,
    "manual_override": -0.8
}

def get_weights():
    w = dict(DEFAULT_WEIGHTS)
    raw = os.environ.get("RL_WEIGHTS_JSON")
    if raw:
        try:
            ext = json.loads(raw)
            w.update({k: float(v) for k, v in ext.items() if k in w})
        except Exception:
            pass
    return w

def compute_reward(signals, weights=None):
    w = weights or get_weights()
    s = dict(signals or {})
    r = 0.0
    for k, val in s.items():
        if k in w:
            r += (w[k] * (1 if bool(val) else 0))
    return round(max(-1.0, min(1.0, r)), 4)

def log_event(event):
    path = os.path.join("logs", "rl_events.log")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            rec = dict(event or {})
            rec["ts"] = dt.datetime.utcnow().isoformat()
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass

def _provenance_path():
    return os.path.join("data","provenance","log.jsonl")

def _last_hash(path):
    try:
        if not os.path.exists(path):
            return "0"*64
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            pos = max(0, size-4096)
            f.seek(pos)
            tail = f.read().decode("utf-8", errors="ignore").splitlines()
            for line in reversed(tail):
                try:
                    obj = json.loads(line)
                    h = obj.get("hash")
                    if h:
                        return h
                except Exception:
                    continue
    except Exception:
        return "0"*64
    return "0"*64

def append_provenance(stage, item_id, data):
    path = _provenance_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        prev = _last_hash(path)
        payload = json.dumps(data or {}, ensure_ascii=False, sort_keys=True)
        content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        curr = hashlib.sha256((prev + content_hash).encode("utf-8")).hexdigest()
        rec = {
            "ts": dt.datetime.utcnow().isoformat(),
            "stage": stage,
            "id": item_id,
            "prev_hash": prev,
            "content_hash": content_hash,
            "hash": curr
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False