import os
import glob
import json
import datetime as dt

def thresholds():
    pr = float(os.environ.get("AUTOMATOR_PRIORITY_THRESHOLD", "0.5"))
    rw = float(os.environ.get("AUTOMATOR_REWARD_THRESHOLD", "0.2"))
    esc_pr = float(os.environ.get("AUTOMATOR_ESC_PRIORITY", "0.1"))
    esc_rw = float(os.environ.get("AUTOMATOR_ESC_REWARD", "0.0"))
    q_rw = float(os.environ.get("AUTOMATOR_QUEUE_REWARD", "0.6"))
    dm_rw = float(os.environ.get("AUTOMATOR_DEMOTE_REWARD", "-0.4"))
    return pr, rw, esc_pr, esc_rw, q_rw, dm_rw

def decide(item, reward):
    pr, rw, esc_pr, esc_rw, q_rw, dm_rw = thresholds()
    p = float(item.get("priority_score", 0.0))
    if p <= esc_pr and reward <= esc_rw:
        return "escalate"
    if reward <= dm_rw:
        return "demote"
    if p < pr or reward < rw:
        return "requeue"
    if reward >= q_rw:
        return "queue"
    return "none"

def _today_dir(base):
    d = dt.datetime.utcnow().strftime("%Y%m%d")
    p = os.path.join(base, d)
    os.makedirs(p, exist_ok=True)
    return p

def _find_processed_by_id(item_id):
    pdir = _today_dir(os.path.join("data","processed"))
    for f in glob.glob(os.path.join(pdir, "item_*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fd:
                obj = json.load(fd)
            if obj.get("id") == item_id:
                return f, obj
        except Exception:
            continue
    return None, None

def requeue_item(item_id):
    path, obj = _find_processed_by_id(item_id)
    if not path or not obj:
        return False
    obj["requeue_requested"] = True
    try:
        with open(path, "w", encoding="utf-8") as fo:
            json.dump(obj, fo, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def queue_item(item_id):
    path, obj = _find_processed_by_id(item_id)
    if not path or not obj:
        return False
    obj["queue_requested"] = True
    obj["queued_at"] = dt.datetime.utcnow().isoformat()
    try:
        with open(path, "w", encoding="utf-8") as fo:
            json.dump(obj, fo, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def demote_item(item_id):
    path, obj = _find_processed_by_id(item_id)
    if not path or not obj:
        return False
    obj["demoted"] = True
    obj["demoted_at"] = dt.datetime.utcnow().isoformat()
    try:
        with open(path, "w", encoding="utf-8") as fo:
            json.dump(obj, fo, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def update_item_fields(item_id, fields):
    path, obj = _find_processed_by_id(item_id)
    if not path or not obj:
        return False
    for k, v in (fields or {}).items():
        obj[k] = v
    try:
        with open(path, "w", encoding="utf-8") as fo:
            json.dump(obj, fo, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False