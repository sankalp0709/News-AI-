import os
import sys
import glob
import json
import subprocess
import datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def today_dirs():
    d = dt.datetime.utcnow().strftime("%Y%m%d")
    pproc = os.path.join(ROOT, "data", "processed", d)
    paud = os.path.join(ROOT, "data", "audio", d, "vaani")
    return pproc, paud

def test_generate_audio_creates_wavs():
    pproc, paud = today_dirs()
    os.makedirs(pproc, exist_ok=True)
    # Ensure at least one processed file exists
    sample = os.path.join(pproc, "item_999.json")
    with open(sample, "w", encoding="utf-8") as f:
        json.dump({"id": "t999", "title": "Test", "summary_short": "a", "summary_medium": "b", "category": "general", "language": "en", "polarity": "neutral", "confidence_score": 0.5, "tone": "calm", "timestamp": dt.datetime.utcnow().isoformat()}, f)
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "generate_audio.py"), "--avatar", "vaani", "--voice", "default", "--limit", "1"], check=False, cwd=ROOT)
    files = glob.glob(os.path.join(paud, "*.wav"))
    assert len(files) >= 1