import os
import sys
import json
import urllib.parse
import logging
import time
import hmac
import hashlib
import base64
import jwt
from logging.handlers import RotatingFileHandler
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.rl_feedback import compute_reward, log_event
from agents.automator import decide, requeue_item, set_reward, set_skip, set_demote

class ApiHandler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        cors = os.environ.get("API_CORS_ORIGIN", "*")
        self.send_header("Access-Control-Allow-Origin", cors)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Client-Nonce, X-Signature")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(data)
    def _send_raw(self, code, data, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        cors = os.environ.get("API_CORS_ORIGIN", "*")
        self.send_header("Access-Control-Allow-Origin", cors)
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(200, {"ok": True})

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok"})
        if self.path == "/version":
            v = os.environ.get("API_VERSION", "v0.2")
            return self._send(200, {"version": v})
        if self.path == "/feed":
            try:
                p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports", "weekly_report.json")
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return self._send(200, data)
            except Exception as e:
                logging.getLogger("errors").error("/feed failure: %s", str(e))
                return self._send(404, {"error": "not_found"})
        if self.path == "/processed/sample":
            try:
                p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports", "weekly_report.json")
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data.get("items", [])
                if not items:
                    return self._send(404, {"error": "no_items"})
                it = dict(items[0])
                it["script"] = it.get("script") or it.get("summary_medium") or it.get("summary_short") or it.get("title")
                if it.get("rl_reward_score") is None:
                    it["rl_reward_score"] = it.get("reward_score", 0.0)
                return self._send(200, it)
            except Exception as e:
                logging.getLogger("errors").error("/processed/sample failure: %s", str(e))
                return self._send(404, {"error": "not_found"})
        if self.path.startswith("/audio"):
            try:
                q = urllib.parse.urlparse(self.path).query
                qs = urllib.parse.parse_qs(q)
                item_id = (qs.get("id") or [None])[0]
                if not item_id:
                    return self._send(400, {"error": "missing_id"})
                from agents.automator import _find_processed_by_id
                fp, obj = _find_processed_by_id(item_id)
                ap = obj.get("audio_path") if obj else None
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                full = os.path.join(base, ap) if ap else None
                if not full or not os.path.exists(full):
                    return self._send(404, {"error": "not_found"})
                with open(full, "rb") as fd:
                    data = fd.read()
                return self._send_raw(200, data, "audio/wav")
            except Exception as e:
                logging.getLogger("errors").error("/audio failure: %s", str(e))
                return self._send(404, {"error": "not_found"})
        if self.path == "/" or self.path == "/index.html":
            try:
                fp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "index.html")
                with open(fp, "rb") as f:
                    data = f.read()
                return self._send_raw(200, data, "text/html; charset=utf-8")
            except Exception:
                return self._send(404, {"error": "not_found"})
        return self._send(404, {"error": "not_found"})

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            body = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            return self._send(400, {"error": "invalid_json"})

        def _validate_auth(raw):
            if os.environ.get("API_SECURITY_ENFORCE", "0") != "1":
                return True
            auth = self.headers.get("Authorization") or ""
            nonce = self.headers.get("X-Client-Nonce") or ""
            sig = self.headers.get("X-Signature") or ""
            if not auth.startswith("Bearer "):
                return False
            token = auth.split(" ", 1)[1]
            sec = os.environ.get("API_JWT_SECRET", "")
            ssec = os.environ.get("API_SIGNATURE_SECRET", "")
            try:
                jwt.decode(token, sec, algorithms=["HS256"])
            except Exception:
                return False
            if not nonce or not ssec:
                return False
            h = hmac.new(ssec.encode("utf-8"), (nonce.encode("utf-8") + raw), hashlib.sha256).hexdigest()
            ok = (h.lower() == sig.strip().lower())
            if ok:
                k = f"_nonce_{nonce}"
                if getattr(ApiHandler, k, None):
                    return False
                setattr(ApiHandler, k, time.time())
            return ok

        if self.path == "/feedback":
            if not _validate_auth(body):
                return self._send(401, {"error": "unauthorized"})
            item = payload.get("item", {})
            item_id = payload.get("id") or item.get("id")
            signals = payload.get("signals", {})
            reward = compute_reward(signals)
            action = decide(item, reward)
            log_event({"type": "feedback", "id": item_id, "signals": signals, "reward": reward, "action": action})
            if item_id:
                set_reward(item_id, reward)
            if action == "requeue" and item_id:
                requeued = requeue_item(item_id)
            elif action == "queue" and item_id:
                requeued = requeue_item(item_id)
            else:
                requeued = False
            if action == "skip" and item_id:
                set_skip(item_id)
            if action == "escalate" and item_id:
                set_demote(item_id)
            return self._send(200, {"id": item_id, "reward": reward, "action": action, "requeued": requeued})

        if self.path == "/requeue":
            if not _validate_auth(body):
                return self._send(401, {"error": "unauthorized"})
            item_id = payload.get("id")
            ok = bool(item_id) and requeue_item(item_id)
            log_event({"type": "requeue", "id": item_id, "ok": ok})
            return self._send(200, {"id": item_id, "requeued": ok})

        return self._send(404, {"error": "not_found"})

def main():
    # logging setup
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"), exist_ok=True)
    app_log = RotatingFileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "app.log"), maxBytes=512000, backupCount=3)
    err_log = RotatingFileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "errors.log"), maxBytes=512000, backupCount=3)
    logging.basicConfig(level=logging.INFO, handlers=[app_log])
    elogger = logging.getLogger("errors")
    elogger.setLevel(logging.ERROR)
    elogger.addHandler(err_log)

    host = os.environ.get("API_HOST", "127.0.0.1")
    env_port = int(os.environ.get("API_PORT", "8000"))
    # CLI override
    port = env_port
    for i, a in enumerate(sys.argv):
        if a == "--port" and i+1 < len(sys.argv):
            try:
                port = int(sys.argv[i+1])
            except Exception:
                pass
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"API server running at http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()