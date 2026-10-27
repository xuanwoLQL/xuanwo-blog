#!/usr/bin/env python3
"""Small HTTP echo server for practicing curl requests."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def _handle(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        payload = {
            "method": self.command,
            "path": self.path,
            "headers": dict(self.headers),
            "body_utf8": body.decode("utf-8", errors="replace"),
            "body_hex": body.hex(),
        }
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = _handle
    do_POST = _handle
    do_PUT = _handle
    do_PATCH = _handle

    def log_message(self, fmt: str, *args) -> None:
        print(fmt % args)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
