import os
import sys
import json
import argparse
import logging
from logging.handlers import RotatingFileHandler
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import time
import hmac
import hashlib
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.rl_feedback import compute_reward, log_event, append_provenance
from agents.automator import decide, requeue_item, queue_item, demote_item, update_item_fields

class ApiHandler(BaseHTTPRequestHandler):
    RATE_LIMITS = {}
    RATE_WINDOW_SECONDS = int(os.environ.get('RATE_WINDOW_SECONDS','60'))
    RATE_LIMIT_PER_WINDOW = int(os.environ.get('RATE_LIMIT_PER_WINDOW','60'))

    def _send(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _client_ip(self):
        try:
            return self.client_address[0]
        except Exception:
            return "unknown"

    def _allow(self, key):
        now = int(time.time())
        win = now // self.RATE_WINDOW_SECONDS
        k = f"{key}:{win}"
        c = self.RATE_LIMITS.get(k, 0)
        if c >= self.RATE_LIMIT_PER_WINDOW:
            return False
        self.RATE_LIMITS[k] = c + 1
        return True

    def _verify_signature(self, body_bytes):
        secret = os.environ.get('API_SECRET')
        if not secret:
            return True
        ts = self.headers.get('X-Timestamp')
        sig = self.headers.get('X-Signature')
        try:
            ts_int = int(ts)
        except Exception:
            return False
        now = int(time.time())
        if abs(now - ts_int) > 300:
            return False
        msg = (str(ts_int).encode('utf-8')) + body_bytes
        calc = hmac.new(secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(calc, str(sig or ''))

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            body = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            return self._send(400, {"error": "invalid_json"})

        ip = self._client_ip()
        if not self._allow(f"{ip}:{self.path}"):
            return self._send(429, {"error": "rate_limited"})
        if not self._verify_signature(body):
            return self._send(401, {"error": "invalid_signature"})

        if self.path == "/feedback":
            item = payload.get("item", {})
            item_id = payload.get("id") or item.get("id")
            signals = payload.get("signals", {})
            reward = compute_reward(signals)
            action = decide(item, reward)
            update_item_fields(item_id, {"reward_score": reward, "rl_reward_score": reward})
            log_event({"type": "feedback", "id": item_id, "signals": signals, "reward": reward, "action": action})
            try:
                append_provenance("feedback", item_id, {"signals": signals, "reward": reward, "action": action})
            except Exception:
                pass
            requeued = False
            queued = False
            demoted = False
            if item_id:
                if action == "requeue":
                    requeued = requeue_item(item_id)
                elif action == "queue":
                    queued = queue_item(item_id)
                elif action == "demote":
                    demoted = demote_item(item_id)
            return self._send(200, {"id": item_id, "reward": reward, "action": action, "requeued": requeued, "queued": queued, "demoted": demoted})

        if self.path == "/requeue":
            item_id = payload.get("id")
            ok = bool(item_id) and requeue_item(item_id)
            log_event({"type": "requeue", "id": item_id, "ok": ok})
            try:
                append_provenance("requeue", item_id, {"ok": ok})
            except Exception:
                pass
            return self._send(200, {"id": item_id, "requeued": ok})

        return self._send(404, {"error": "not_found"})

    def do_GET(self):
        if self.path == "/processed/sample":
            sample = None
            try:
                with open(os.path.join("exports","weekly_report.json"), "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data.get("items") or []
                if items:
                    x = items[0]
                    sample = {
                        "id": x.get("id"),
                        "script": x.get("summary_medium") or x.get("summary_short") or x.get("title"),
                        "tone": x.get("tone"),
                        "confidence_score": x.get("confidence") or x.get("confidence_score") or 0.5,
                        "audio_path": x.get("audio_path"),
                        "priority_score": x.get("priority_score") or 0.0,
                        "trend_score": x.get("trend_score") or 0.0,
                        "rl_reward_score": x.get("rl_reward_score") or 0.0
                    }
            except Exception:
                sample = None
            if not sample:
                sample = {
                    "id": "sample-id",
                    "script": "Sample medium summary for narration.",
                    "tone": "calm",
                    "confidence_score": 0.5,
                    "audio_path": "data/audio/20250101/dev/item_1_dev.wav",
                    "priority_score": 0.0,
                    "trend_score": 0.0,
                    "rl_reward_score": 0.0
                }
            return self._send(200, sample)
        return self._send(404, {"error": "not_found"})

def configure_logging():
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    info_handler = RotatingFileHandler(os.path.join("logs","server.log"), maxBytes=1024*1024, backupCount=3)
    err_handler = RotatingFileHandler(os.path.join("logs","errors.log"), maxBytes=1024*1024, backupCount=3)
    err_handler.setLevel(logging.ERROR)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    info_handler.setFormatter(fmt)
    err_handler.setFormatter(fmt)
    logger.addHandler(info_handler)
    logger.addHandler(err_handler)

def main():
    configure_logging()
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default=os.environ.get('API_HOST','127.0.0.1'))
    ap.add_argument('--port', type=int, default=int(os.environ.get('API_PORT','8000')))
    args = ap.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ApiHandler)
    print(f"API server running at http://{args.host}:{args.port}/")
    logging.info("API server started")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("API server stopped")

if __name__ == "__main__":
    main()
