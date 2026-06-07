#!/usr/bin/env python3

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

STATE_PATH = os.path.expanduser("~/.claude/flush/flush_state.json")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/state":
            if os.path.exists(STATE_PATH):
                with open(STATE_PATH) as f:
                    data = f.read()
            else:
                data = json.dumps({"flush": False, "score": 0, "hits": []})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data.encode())
        elif self.path == "/ack":
            # UI calls this after animation plays to reset state
            if os.path.exists(STATE_PATH):
                with open(STATE_PATH) as f:
                    state = json.load(f)
                state["flush"] = False
                with open(STATE_PATH, "w") as f:
                    json.dump(state, f)
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass  # silence request logs

if __name__ == "__main__":
    server = HTTPServer(("localhost", 7329), Handler)
    print("flush state server running on http://localhost:7329")
    server.serve_forever()
