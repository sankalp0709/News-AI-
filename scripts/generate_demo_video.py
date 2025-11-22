import os
import json
import subprocess
import wave
import contextlib
from imageio_ffmpeg import get_ffmpeg_exe

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def pick_audio():
    p = os.path.join(ROOT, "exports", "weekly_report.json")
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    for it in data.get("items", []):
        ap = it.get("audio_path")
        if ap:
            full = os.path.join(ROOT, ap)
            if os.path.exists(full):
                return full
    return None

def _duration_wav(path):
    try:
        with contextlib.closing(wave.open(path, 'rb')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return frames / float(rate)
    except Exception:
        return 10.0

def main():
    img = os.path.join(ROOT, "docs", "architecture_v1.png")
    audio = pick_audio()
    if not audio:
        print(json.dumps({"error": "no_audio"}))
        return
    dur = _duration_wav(audio)
    outp = os.path.join(ROOT, "exports", "demo.mp4")
    ff = get_ffmpeg_exe()
    cmd = [ff, '-y', '-loop', '1', '-i', img, '-i', audio, '-c:v', 'libx264', '-t', str(dur), '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', outp]
    subprocess.run(cmd, check=True)
    print(json.dumps({"written": outp}))

if __name__ == "__main__":
    main()