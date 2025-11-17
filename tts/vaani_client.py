import os
import base64
import requests

def synthesize(text, voice="default", tone="calm", lang="en", out_path=None):
    url = os.environ.get("VAANI_TTS_URL")
    key = os.environ.get("VAANI_API_KEY")
    if not url:
        return None
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    payload = {"text": text, "voice": voice, "tone": tone, "lang": lang}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        if "audio" in ct:
            if not out_path:
                return r.content
            with open(out_path, "wb") as f:
                f.write(r.content)
            return out_path
        data = r.json()
        if isinstance(data, dict):
            if data.get("audio_base64"):
                b = base64.b64decode(data.get("audio_base64"))
                if out_path:
                    with open(out_path, "wb") as f:
                        f.write(b)
                    return out_path
                return b
            if data.get("audio_url"):
                ar = requests.get(data.get("audio_url"), timeout=30)
                ar.raise_for_status()
                if out_path:
                    with open(out_path, "wb") as f:
                        f.write(ar.content)
                    return out_path
                return ar.content
        return None
    except Exception:
        return None