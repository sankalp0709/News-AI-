import os
import glob
import json
import datetime as dt

def thresholds():
    pr = float(os.environ.get("AUTOMATOR_PRIORITY_THRESHOLD", "0.5"))
    rw = float(os.environ.get("AUTOMATOR_REWARD_THRESHOLD", "0.2"))
    esc_pr = float(os.environ.get("AUTOMATOR_ESC_PRIORITY", "0.1"))
    esc_rw = float(os.environ.get("AUTOMATOR_ESC_REWARD", "0.0"))
    dyn = os.environ.get("AUTOMATOR_DYNAMIC", "0")
    pos_q = float(os.environ.get("AUTOMATOR_POS_REQUEUE", "0.6"))
    neg_skip = float(os.environ.get("AUTOMATOR_NEG_SKIP", "-0.3"))
    if dyn == "1":
        avg = _avg_reward()
        try:
            if avg is not None:
                pr = max(0.1, min(0.9, pr - 0.1*avg))
                rw = max(-1.0, min(1.0, rw - 0.2*avg))
        except Exception:
            pass
    return pr, rw, esc_pr, esc_rw, pos_q, neg_skip

def decide(item, reward):
    pr, rw, esc_pr, esc_rw, pos_q, neg_skip = thresholds()
    p = float(item.get("priority_score", 0.0))
    if reward is not None and reward >= pos_q:
        return "queue"
    if reward is not None and reward <= neg_skip:
        return "skip"
    if p <= esc_pr and reward <= esc_rw:
        return "escalate"
    if p < pr or reward < rw:
        return "requeue"
    return "none"

def _today_dir(base):
    d = dt.datetime.utcnow().strftime("%Y%m%d")
    p = os.path.join(base, d)
    os.makedirs(p, exist_ok=True)
    return p

def _avg_reward():
    path = os.path.join("logs", "rl_events.log")
    try:
        if not os.path.exists(path):
            return None
        vals = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f.readlines()[-200:]:
                try:
                    obj = json.loads(line.strip())
                    if "reward" in obj:
                        vals.append(float(obj.get("reward")))
                except Exception:
                    continue
        if not vals:
            return None
        return sum(vals)/float(len(vals))
    except Exception:
        return None

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

def _modify_item(item_id, mutator):
    path, obj = _find_processed_by_id(item_id)
    if not path or not obj:
        return False
    try:
        obj = mutator(obj)
        with open(path, "w", encoding="utf-8") as fo:
            json.dump(obj, fo, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

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

def set_reward(item_id, reward):
    return _modify_item(item_id, lambda o: {**o, "reward_score": float(reward)})

def set_skip(item_id):
    return _modify_item(item_id, lambda o: {**o, "skip": True})

def set_demote(item_id):
    def mutate(o):
        ps = float(o.get("priority_score", 0.0))
        ps = max(0.0, ps - 0.1)
        o["priority_score"] = ps
        o["demote"] = True
        return o
    return _modify_item(item_id, mutate)