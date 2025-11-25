import os
import sys
import time
import json
import argparse
import logging
from logging.handlers import RotatingFileHandler

def run(cmd):
    import subprocess
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    out, _ = p.communicate()
    return p.returncode, out.decode('utf-8', errors='ignore')

def notify_failure(title, body):
    url = os.environ.get('SLACK_WEBHOOK_URL')
    if not url:
        return False
    import requests
    try:
        payload = {"text": f"{title}\n```{body[:1500]}```"}
        r = requests.post(url, json=payload, timeout=float(os.environ.get('HTTP_TIMEOUT_SECONDS','20')))
        return r.ok
    except Exception:
        return False

def configure_logging():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('scheduler')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(os.path.join('logs','scheduler.log'), maxBytes=1024*1024, backupCount=3)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    return logger

def execute_pipeline_with_retries(max_retries=3, delay_seconds=5):
    logger = logging.getLogger('scheduler')
    tries = 0
    while tries < max_retries:
        rc, out = run('python scripts/run_pipeline.py')
        if rc == 0:
            logger.info('pipeline_ok')
            return True
        tries += 1
        logger.error(json.dumps({"pipeline_rc": rc, "attempt": tries, "output": out[:2000]}))
        notify_failure('Pipeline failed', out)
        time.sleep(delay_seconds * (2 ** (tries-1)))
    return False

def loop(interval_seconds):
    logger = logging.getLogger('scheduler')
    logger.info(json.dumps({"start_interval": interval_seconds}))
    while True:
        execute_pipeline_with_retries()
        time.sleep(interval_seconds)

def main():
    logger = configure_logging()
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['hourly','four_hourly','daily'])
    ap.add_argument('--daemon', action='store_true')
    args = ap.parse_args()
    if args.mode == 'hourly':
        interval = 3600
    elif args.mode == 'four_hourly':
        interval = 4*3600
    else:
        interval = 24*3600
    if args.daemon:
        loop(interval)
    else:
        ok = execute_pipeline_with_retries()
        print(json.dumps({"status": "ok" if ok else "failed"}))

if __name__ == '__main__':
    main()