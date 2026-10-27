#!/usr/bin/env python3
"""Run release-oriented checks against Hugo's generated public/ output."""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
OG_LIMIT = 120 * 1024


class IndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.description = ""
        self.inline_scripts: list[str] = []
        self.stats: list[tuple[str, str]] = []
        self._stat_count: str | None = None
        self._stat_text: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        data = dict(attrs)
        if tag == "meta" and data.get("name") == "description":
            self.description = data.get("content") or ""
        if tag == "script" and not data.get("src"):
            script_type = (data.get("type") or "").lower()
            if script_type != "application/ld+json":
                self.inline_scripts.append(script_type or "text/javascript")
        if tag == "span" and "stat-num" in (data.get("class") or "").split():
            self._stat_count = data.get("data-count")
            self._stat_text = []

    def handle_data(self, data: str) -> None:
        if self._stat_count is not None:
            self._stat_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._stat_count is not None:
            text = "".join(self._stat_text).strip()
            self.stats.append((self._stat_count, text))
            self._stat_count = None
            self._stat_text = []


def main() -> int:
    errors: list[str] = []
    index_file = PUBLIC / "index.html"

    if not index_file.exists():
        print("public/index.html is missing; build the site first", file=sys.stderr)
        return 1

    parser = IndexParser()
    parser.feed(index_file.read_text(encoding="utf-8", errors="ignore"))
    inline_pages: list[str] = []
    for html_file in PUBLIC.rglob("*.html"):
        if html_file == index_file:
            page_parser = parser
        else:
            page_parser = IndexParser()
            page_parser.feed(
                html_file.read_text(encoding="utf-8", errors="ignore")
            )
        if page_parser.inline_scripts:
            inline_pages.append(
                html_file.relative_to(PUBLIC).as_posix()
            )

    if len(parser.description.strip()) < 40:
        errors.append(
            f"homepage meta description is too short ({len(parser.description)} chars)"
        )

    if not parser.stats:
        errors.append("homepage counters were not found")
    for expected, rendered in parser.stats:
        if rendered != expected:
            errors.append(
                f"counter fallback mismatch: expected {expected!r}, rendered {rendered!r}"
            )
        if rendered.isdigit() and int(rendered) <= 0:
            errors.append(f"counter must be greater than zero: {rendered}")

    if inline_pages:
        errors.append(
            "executable inline scripts remain: "
            + ", ".join(inline_pages[:5])
        )

    og_cover = PUBLIC / "images" / "og-cover.png"
    if not og_cover.exists():
        errors.append("social preview image is missing")
    elif og_cover.stat().st_size > OG_LIMIT:
        errors.append(
            f"og-cover.png is {og_cover.stat().st_size} bytes; limit is {OG_LIMIT}"
        )

    projects_file = PUBLIC / "projects" / "index.html"
    if not projects_file.exists():
        errors.append("projects index is missing")
    else:
        projects_html = projects_file.read_text(encoding="utf-8", errors="ignore")
        for token in ("站内详情", "GitHub 外链"):
            if token not in projects_html:
                errors.append(f"projects index does not distinguish: {token}")

    search_index = PUBLIC / "index.json"
    if not search_index.exists():
        errors.append("search index is missing")
    elif search_index.stat().st_size > 120 * 1024:
        errors.append(
            f"search index is {search_index.stat().st_size} bytes; limit is 120 KB"
        )

    note_pages = [
        path
        for path in (PUBLIC / "notes").glob("*/index.html")
        if path.parent.name != "notes"
    ]
    missing_diagrams = [
        path.parent.name
        for path in note_pages
        if "note-diagram" not in path.read_text(
            encoding="utf-8", errors="ignore"
        )
    ]
    if missing_diagrams:
        errors.append(
            "notes missing workflow diagrams: "
            + ", ".join(sorted(missing_diagrams)[:8])
        )

    if errors:
        print(f"FAILED: {len(errors)} quality issue(s)")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        "OK: meta, counters, CSP, OG image, search index, project labels, note diagrams"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
