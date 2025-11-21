import os
import sys
import json
import subprocess
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def normalize_path(p):
    if not p:
        return p
    return str(p).replace("\\", "/")

def ensure_exports():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    p = os.path.join(root, "exports", "sample_integration.json")
    if os.path.exists(p):
        return p
    subprocess.run(["python", os.path.join(root, "scripts", "smart_feed.py")], cwd=root, check=False)
    subprocess.run(["python", os.path.join(root, "scripts", "make_integration_samples.py")], cwd=root, check=False)
    return p

def validate_item(x):
    if not isinstance(x.get("id"), str):
        return False
    if not isinstance(x.get("script"), str):
        return False
    if not isinstance(x.get("tone"), str):
        return False
    if not isinstance(x.get("language"), str):
        return False
    ap = x.get("audio_path")
    if not isinstance(ap, str):
        return False
    if "\\" in ap:
        return False
    try:
        float(x.get("priority_score"))
        float(x.get("trend_score"))
    except Exception:
        return False
    return True

def main():
    path = ensure_exports()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", [])
    ok = all(validate_item(x) for x in items)
    print(json.dumps({"count": len(items), "schema_ok": ok}))

if __name__ == "__main__":
    main()