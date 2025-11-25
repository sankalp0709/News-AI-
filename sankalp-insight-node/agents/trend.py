import datetime as dt
from dateutil import parser as dparser

def _ts(s):
    try:
        t = dparser.parse(s)
        if t.tzinfo is not None:
            t = t.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return t
    except Exception:
        return dt.datetime.utcnow()

def _bucket(ts, ref, minutes):
    delta = ref - ts
    return max(0, int(delta.total_seconds() // (minutes*60)))

def _bins(items, minutes=120, window=6):
    ref = max((_ts(x.get("timestamp")) for x in items), default=dt.datetime.utcnow())
    bins = [0]*window
    for x in items:
        b = _bucket(_ts(x.get("timestamp")), ref, minutes)
        if b < window:
            bins[b] += 1
    return bins

def _velocity(bins):
    if len(bins) < 2:
        return 0.0
    last = bins[0]
    prev = bins[1]
    denom = max(1, sum(bins))
    v = (last - prev) / float(denom)
    return max(0.0, min(1.0, v*3.0))

def _density(bins):
    total = max(1, sum(bins))
    return max(0.0, min(1.0, bins[0]/float(total)))

def score_category(items):
    b_short = _bins(items, minutes=60, window=8)
    b_long = _bins(items, minutes=240, window=8)
    v_short = _velocity(b_short)
    d_short = _density(b_short)
    v_long = _velocity(b_long)
    s = 0.5*v_short + 0.2*d_short + 0.3*v_long
    return max(0.0, min(1.0, s))

def compute(items):
    cats = {}
    for x in items:
        c = x.get("category") or "general"
        cats.setdefault(c, []).append(x)
    scores = {}
    for c, its in cats.items():
        scores[c] = score_category(its)
    return scores