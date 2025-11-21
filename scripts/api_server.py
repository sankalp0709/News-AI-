import os
import sys
import json
import logging
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
                # ensure required fields
                it["script"] = it.get("script") or it.get("summary_medium") or it.get("summary_short") or it.get("title")
                if it.get("rl_reward_score") is None:
                    it["rl_reward_score"] = it.get("reward_score", 0.0)
                return self._send(200, it)
            except Exception as e:
                logging.getLogger("errors").error("/processed/sample failure: %s", str(e))
                return self._send(404, {"error": "not_found"})
        return self._send(404, {"error": "not_found"})

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            body = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            return self._send(400, {"error": "invalid_json"})

        if self.path == "/feedback":
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