#!/usr/bin/env python3
"""
desk_server.py - serve the desk, and give it somewhere real to save.

The desk used to keep your marks in browser storage. That is per-browser AND
per-address, so marks made on http://localhost:8901 were invisible to the phone
on http://192.168.x.x:8902, and a cleared cache lost them silently.

This serves the same page but adds two endpoints:

    GET  /state   -> the contents of desk-state.json
    POST /state   -> replace desk-state.json

so every device writes to one file on this PC. The desk saves after every change,
with no button to remember, and the next rebuild reads the same file.

  py desk_server.py                 # this PC only, port 8901
  py desk_server.py --lan           # also reachable from your phone on the wi-fi
"""

import argparse
import http.server
import json
import os
import pathlib
import shutil
import socket
import socketserver
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE / "site"
STATE = HERE / "desk-state.json"
BACKUPS = HERE / "state-history"
MAX_BODY = 4 * 1024 * 1024          # a few thousand marks; anything larger is a mistake


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(SITE), **kw)

    def log_message(self, fmt, *args):
        if "/state" in (self.path or ""):
            return                    # saving every few seconds; do not spam the window
        super().log_message(fmt, *args)

    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] == "/state":
            try:
                data = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
            except Exception as e:
                return self._json(500, {"error": str(e)})
            return self._json(200, data)
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/state":
            return self._json(404, {"error": "no such endpoint"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > MAX_BODY:
                return self._json(413, {"error": "bad size"})
            data = json.loads(self.rfile.read(n).decode("utf-8"))
            if not isinstance(data, dict):
                return self._json(400, {"error": "expected an object"})

            # Keep the last few versions. This file is now the only copy of months of
            # notes and outcomes; a bad write with no history would be unrecoverable.
            if STATE.exists():
                BACKUPS.mkdir(exist_ok=True)
                shutil.copy(STATE, BACKUPS / time.strftime("desk-state-%Y%m%d-%H%M%S.json"))
                old = sorted(BACKUPS.glob("desk-state-*.json"))
                for p in old[:-20]:
                    p.unlink(missing_ok=True)

            # Write beside the target and swap, so an interrupted write cannot
            # leave a half-written file where your marks used to be.
            tmp = STATE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, STATE)
            return self._json(200, {"saved": len(data)})
        except Exception as e:
            return self._json(500, {"error": str(e)})


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    ap.add_argument("--lan", action="store_true", help="allow phones on the same wi-fi")
    args = ap.parse_args()

    if not (SITE / "desk.html").exists():
        sys.exit("No site\\desk.html yet. Run the refresh first.")

    host = "0.0.0.0" if args.lan else "127.0.0.1"
    with Server((host, args.port), Handler) as srv:
        print()
        print(f"   On this PC:    http://localhost:{args.port}/desk.html")
        if args.lan:
            try:
                print(f"   On your phone: http://{lan_ip()}:{args.port}/desk.html")
            except Exception:
                print("   Could not work out this PC's wi-fi address.")
        print()
        print(f"   Marks are saved to {STATE.name}, automatically, from every device.")
        print("   Leave this window open. Close it to stop.")
        print()
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
