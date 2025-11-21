import os
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

def _bins(items, minutes=None, window=None):
    m = int(os.environ.get("TREND_BIN_MINUTES", "120")) if minutes is None else int(minutes)
    w = int(os.environ.get("TREND_WINDOW", "6")) if window is None else int(window)
    ref = max((_ts(x.get("timestamp")) for x in items), default=dt.datetime.utcnow())
    bins = [0]*w
    for x in items:
        b = _bucket(_ts(x.get("timestamp")), ref, m)
        if b < w:
            bins[b] += 1
    return bins

def _velocity(bins):
    if len(bins) < 2:
        return 0.0
    alpha = float(os.environ.get("TREND_SMOOTH_ALPHA", "0.6"))
    last = bins[0]
    prev = bins[1]
    decayed = 0.0
    w = 1.0
    for i, b in enumerate(bins):
        decayed += b * w
        w *= alpha
    denom = max(1.0, decayed)
    v = (last - prev) / denom
    return max(0.0, min(1.0, v*3.0))

def _density(bins):
    alpha = float(os.environ.get("TREND_SMOOTH_ALPHA", "0.6"))
    decayed_total = 0.0
    w = 1.0
    for b in bins:
        decayed_total += b * w
        w *= alpha
    total = max(1.0, decayed_total)
    return max(0.0, min(1.0, bins[0]/float(total)))

def score_category(items):
    b = _bins(items)
    v = _velocity(b)
    d = _density(b)
    s = 0.7*v + 0.3*d
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