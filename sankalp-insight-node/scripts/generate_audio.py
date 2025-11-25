import os
import sys
import glob
import json
import datetime as dt
import wave
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tts.vaani_client import synthesize as vaani_synth
from tts.fallback import simplify_text, synthesize_local

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def today_dir(base, sub=None, date_override=None):
    d = date_override or dt.datetime.utcnow().strftime("%Y%m%d")
    p = os.path.join(base, d)
    if sub:
        p = os.path.join(p, sub)
    ensure_dir(p)
    return p

def audio_duration(path):
    try:
        with wave.open(path, 'rb') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            return round(frames / float(rate), 2)
    except Exception:
        return None

def create_silence_wav(path, seconds=1, rate=16000):
    try:
        import wave
        import struct
        ensure_dir(os.path.dirname(path))
        frames = int(seconds * rate)
        with wave.open(path, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            silence = struct.pack('<h', 0)
            for _ in range(frames):
                w.writeframesraw(silence)
        return True
    except Exception:
        return False

def normalize_path(p):
    if not p:
        return p
    return str(p).replace("\\", "/")

def synthesize_text(text, voice, tone, lang, out_path):
    ok = False
    status = "failed"
    res = vaani_synth(text, voice=voice, tone=tone, lang=lang, out_path=out_path)
    if isinstance(res, str) and os.path.exists(res):
        ok = True
        status = "success"
    else:
        simp = simplify_text(text)
        res2 = synthesize_local(simp, voice=voice, tone=tone, lang=lang, out_path=out_path)
        if isinstance(res2, str) and os.path.exists(res2):
            ok = True
            status = "fallback"
    if not ok and out_path:
        if create_silence_wav(out_path, seconds=1):
            ok = True
            status = "silent_fallback"
    return ok, status

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="default")
    ap.add_argument("--avatar", default="default")
    ap.add_argument("--limit", type=int, default=0, help="0 = no limit")
    ap.add_argument("--missing-only", action="store_true", help="only synthesize items without audio_path")
    ap.add_argument("--date", default=None, help="YYYYMMDD processed/audio date override")
    args = ap.parse_args()

    proc_dir = today_dir(os.path.join("data","processed"), date_override=args.date)
    audio_dir = today_dir(os.path.join("data","audio"), args.avatar, date_override=args.date)
    files = sorted(glob.glob(os.path.join(proc_dir, "item_*.json")))
    count = 0
    for f in files:
        with open(f, "r", encoding="utf-8") as fd:
            obj = json.load(fd)
        if args.missing_only:
            existing = obj.get("audio_path")
            if existing:
                ep = existing if os.path.isabs(existing) else os.path.join(os.path.dirname(proc_dir), existing)
                if os.path.exists(ep):
                    continue
        text = obj.get("summary_medium") or obj.get("summary_short") or obj.get("title")
        voice = args.voice
        tone = obj.get("tone") or "calm"
        lang = obj.get("language") or "en"
        base = os.path.splitext(os.path.basename(f))[0]
        out_path = os.path.join(audio_dir, f"{base}_{args.avatar}.wav")
        ok, status = synthesize_text(text, voice, tone, lang, out_path)
        dur = audio_duration(out_path) if ok else None
        obj["audio_path"] = normalize_path(out_path) if ok else None
        obj["audio_duration"] = dur
        obj["voice_used"] = voice
        obj["synthesis_status"] = status
        obj["avatar"] = args.avatar
        with open(f, "w", encoding="utf-8") as fo:
            json.dump(obj, fo, ensure_ascii=False, indent=2)
        count += 1
        if args.limit and count >= args.limit:
            break
    print(json.dumps({"audio_generated": count, "audio_dir": audio_dir}))

if __name__ == "__main__":
    main()