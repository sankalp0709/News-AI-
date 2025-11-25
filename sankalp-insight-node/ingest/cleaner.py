import re
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None
try:
    from langdetect import detect
except Exception:
    detect = None

def clean_text(text):
    html = text or ""
    if BeautifulSoup is None:
        plain = re.sub(r"<[^>]+>", " ", html)
    else:
        soup = BeautifulSoup(html, "html.parser")
        plain = soup.get_text(" ")
    norm = re.sub(r"\s+", " ", plain).strip()
    return norm

def detect_language(text):
    if detect is None:
        return "unknown"
    try:
        return detect(text or "")
    except Exception:
        return "unknown"

def clean_article(article):
    a = dict(article or {})
    a["title"] = clean_text(a.get("title"))
    a["summary"] = clean_text(a.get("summary"))
    a["language"] = detect_language((a.get("title") or "") + " " + (a.get("summary") or ""))
    return a