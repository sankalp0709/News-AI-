import os
import sys
import json
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INCLUDE_DIRS = [
    "scripts",
    "models",
    "exports",
    "docs",
    "tests"
]

EXCLUDE_NAMES = {"__pycache__", ".pytest_cache", ".DS_Store", "Thumbs.db"}

def should_include(path):
    name = os.path.basename(path)
    if name in EXCLUDE_NAMES:
        return False
    if name.endswith(('.pyc', '.pyo', '.orig', '.log')):
        return False
    return True

def add_dir(zf, base):
    full = os.path.join(ROOT, base)
    if not os.path.exists(full):
        return
    for root, dirs, files in os.walk(full):
        dirs[:] = [d for d in dirs if should_include(d)]
        for f in files:
            if not should_include(f):
                continue
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, ROOT)
            zf.write(fp, rel)

def main():
    outp = os.path.join(ROOT, "integration_ready.zip")
    with zipfile.ZipFile(outp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for d in INCLUDE_DIRS:
            add_dir(zf, d)
    print(json.dumps({"written": outp}))

if __name__ == "__main__":
    main()