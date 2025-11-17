import os
import re
import requests

def _sentences(text):
    t = text or ""
    s = re.split(r"(?<=[\.!?])\s+", t)
    return [x.strip() for x in s if x.strip()]

def _fallback_short(text):
    s = _sentences(text)
    return " ".join(s[:2])[:400]

def _fallback_medium(text):
    s = _sentences(text)
    return " ".join(s[:4])[:800]

def _uniguru(text):
    url = os.environ.get("UNIGURU_SUMMARY_URL")
    key = os.environ.get("UNIGURU_API_KEY")
    if not url:
        return None
    try:
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        payload = {"text": text}
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def summarize_short(text):
    res = _uniguru(text)
    if isinstance(res, dict) and res.get("summary_short"):
        return res.get("summary_short")
    return _fallback_short(text)

def summarize_medium(text):
    res = _uniguru(text)
    if isinstance(res, dict) and res.get("summary_medium"):
        return res.get("summary_medium")
    return _fallback_medium(text)