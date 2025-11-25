import math

POS = {"good","great","positive","benefit","growth","optimistic","gain","win","strong","record","surge","rise","improve","success","joy","happy","up","boost","advance"}
NEG = {"bad","poor","negative","loss","drop","decline","fall","weak","crisis","fear","warn","risk","fail","collapse","urgent","emergency","down","plunge","cut"}
URGENT = {"breaking","urgent","emergency","crisis","alert","deadline"}

def _score(text):
    t = (text or "").lower()
    tokens = [x for x in t.replace("\n"," ").split() if x]
    negators = {"not","no","never","none"}
    intensifiers = {"very","extremely","highly","strongly"}
    p = 0
    n = 0
    flip = False
    intens = 1.0
    for tok in tokens:
        w = tok.strip('.,!?;:"\'')
        if w in negators:
            flip = True
            continue
        if w in intensifiers:
            intens = min(2.0, intens + 0.5)
            continue
        val = 0
        if w in POS:
            val = 1
        elif w in NEG:
            val = -1
        if val != 0:
            val = (-val if flip else val)
            flip = False
            if val > 0:
                p += intens
            else:
                n += intens
            intens = 1.0
    s = p - n
    if s > 0:
        pol = "positive"
    elif s < 0:
        pol = "negative"
    else:
        pol = "neutral"
    length_norm = max(1.0, len(tokens)/50.0)
    coverage = min(1.0, (p+n) / max(1.0, len(tokens)))
    consistency = min(1.0, abs(s) / max(1.0, p+n)) if (p+n) > 0 else 0.0
    base = 0.25
    conf = base + 0.35*coverage + 0.25*consistency + 0.15*min(1.0, (p+n)/5.0) / length_norm
    conf = max(0.1, min(1.0, conf)) if (p+n) > 0 else 0.3
    if any(w in t for w in URGENT):
        tone = "urgent"
    elif s > 0:
        tone = "joyful"
    elif s < 0:
        tone = "serious"
    else:
        tone = "calm"
    return pol, float(f"{conf:.2f}"), tone

def analyze(text):
    return _score(text)