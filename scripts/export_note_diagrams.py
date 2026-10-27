#!/usr/bin/env python3
"""Export every diagram-design HTML file to a blog SVG asset."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIAGRAMS = ROOT / "docs" / "diagrams"
SKILL = Path(
    os.environ.get(
        "DIAGRAM_DESIGN_SKILL",
        r"D:\agent\diagram-design-main\skills\diagram-design",
    )
)
EXPORTER = SKILL / "scripts" / "export_svg.py"


def main() -> int:
    if not EXPORTER.exists():
        print(f"export_svg.py not found: {EXPORTER}", file=sys.stderr)
        return 1

    count = 0
    for source in sorted(DIAGRAMS.glob("*.html")):
        slug = source.stem
        output = ROOT / "static" / "images" / "notes" / slug / "workflow.svg"
        output.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                sys.executable,
                str(EXPORTER),
                "--system-fonts",
                str(source),
                str(output),
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        if result.returncode:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            return result.returncode
        if not output.exists() or output.stat().st_size < 2000:
            print(f"bad SVG export: {output}", file=sys.stderr)
            return 1
        count += 1
    print(f"Exported {count} diagrams to SVG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
