#!/usr/bin/env python3
"""Insert the generated workflow figure into each note exactly once."""

from __future__ import annotations

from pathlib import Path

from diagram_catalog import DIAGRAMS

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "content" / "notes"


def split_note(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML front matter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("unterminated YAML front matter")
    return text[: end + 5], text[end + 5 :]


def figure(spec: dict) -> str:
    slug = spec["slug"]
    return f"""## 复现流程图

<figure class="note-diagram">
  <img src="/images/notes/{slug}/workflow.svg" alt="{spec['desc']}" loading="lazy">
  <figcaption>图 1 · {spec['title']}。{spec['desc']}</figcaption>
</figure>
"""


def main() -> int:
    changed = 0
    for spec in DIAGRAMS:
        path = NOTES / f"{spec['slug']}.md"
        text = path.read_text(encoding="utf-8")
        if f"/images/notes/{spec['slug']}/workflow.svg" in text:
            continue
        front, body = split_note(text)
        path.write_text(
            front + "\n" + figure(spec) + "\n" + body.lstrip("\n"),
            encoding="utf-8",
        )
        changed += 1
    print(f"Inserted workflow figure into {changed} notes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
