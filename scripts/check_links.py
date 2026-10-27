#!/usr/bin/env python3
"""Check internal links in Hugo's public/ output.

Usage:
    python scripts/check_links.py
    python scripts/check_links.py --public /path/to/public

Checks href/src of local pages, URL-decodes Chinese paths, resolves
root-relative and relative URLs, and treats directory URLs as index.html.
"""

from __future__ import annotations

import argparse
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent


class LinkParser(HTMLParser):
    def __init__(self, page: str) -> None:
        super().__init__()
        self.page = page
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        for key in ("href", "src"):
            value = data.get(key)
            if value:
                self.links.append(value)


def is_external(value: str) -> bool:
    return value.startswith(
        ("http://", "https://", "mailto:", "tel:", "javascript:", "data:", "#")
    )


def resolve(public: Path, page: str, value: str) -> Path | None:
    value = unquote(value.split("#", 1)[0].split("?", 1)[0])
    if not value:
        return None
    if value.startswith("/"):
        return (public / value.lstrip("/")).resolve()
    base = public / page
    if not page or page.endswith("/"):
        return (base / value).resolve()
    return (base.parent / value).resolve()


def check(public: Path) -> tuple[int, int, dict[str, set[str]]]:
    missing: dict[str, set[str]] = {}
    pages = 0
    links = 0

    for html_file in public.rglob("*.html"):
        rel = html_file.relative_to(public).as_posix()
        page = rel[: -len("index.html")] if rel.endswith("index.html") else rel
        parser = LinkParser(page)
        parser.feed(html_file.read_text(encoding="utf-8", errors="ignore"))
        pages += 1

        for value in parser.links:
            if is_external(value):
                continue
            target = resolve(public, page, value)
            if target is None:
                continue
            links += 1
            try:
                target.relative_to(public)
            except ValueError:
                missing.setdefault(value, set()).add(page)
                continue

            if value.split("#", 1)[0].endswith("/") or target.is_dir():
                if not (target / "index.html").exists():
                    missing.setdefault(value, set()).add(page)
            elif not target.exists():
                missing.setdefault(value, set()).add(page)

    return pages, links, missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", default=str(ROOT / "public"))
    args = parser.parse_args()
    public = Path(args.public).resolve()

    if not (public / "index.html").exists():
        print(f"public/index.html not found: {public}", file=sys.stderr)
        return 1

    pages, links, missing = check(public)
    print(f"scanned {pages} HTML pages, {links} internal links")

    if not missing:
        print("OK: 0 broken internal links")
        return 0

    print(f"BROKEN: {len(missing)} targets")
    for value in sorted(missing):
        sources = ", ".join(sorted(missing[value])[:3])
        print(f"  {value}  <-  {sources}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
