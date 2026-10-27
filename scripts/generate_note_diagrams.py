#!/usr/bin/env python3
"""Generate self-contained HTML diagrams for note pages."""

from __future__ import annotations

import argparse
import html
from pathlib import Path

from diagram_catalog import DIAGRAMS

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "diagrams"

PAPER = "#f6f2e9"
PAPER_2 = "#efe9dd"
INK = "#0c211c"
MUTED = "#5b726a"
SOFT = "#5f736b"
ACCENT = "#0f766e"
LINK = "#0369a1"
RULE = "rgba(12,33,28,0.14)"
RULE_STRONG = "rgba(12,33,28,0.28)"
ACCENT_TINT = "rgba(15,118,110,0.08)"
ZONE = "rgba(12,33,28,0.025)"

SANS = "'MiSans','HarmonyOS Sans SC','Noto Sans SC','Microsoft YaHei',sans-serif"
SERIF = "'Noto Serif SC','Source Han Serif SC','Songti SC','SimSun',serif"
MONO = "'Cascadia Mono','Cascadia Code','Consolas','Liberation Mono',monospace"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def text(
    x: float,
    y: float,
    value: str,
    *,
    size: float,
    fill: str = INK,
    family: str = SANS,
    weight: int | None = None,
    anchor: str = "middle",
    spacing: str | None = None,
) -> str:
    attrs = [
        f'x="{x:g}"',
        f'y="{y:g}"',
        f'fill="{fill}"',
        f'font-size="{size:g}"',
        f'font-family="{family}"',
        f'text-anchor="{anchor}"',
    ]
    if weight is not None:
        attrs.append(f'font-weight="{weight}"')
    if spacing is not None:
        attrs.append(f'letter-spacing="{spacing}"')
    return f"<text {' '.join(attrs)}>{esc(value)}</text>"


def defs(slug: str) -> str:
    return f"""
<defs>
  <marker id="{slug}-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
    <polygon points="0 0, 8 3, 0 6" fill="{MUTED}"/>
  </marker>
  <marker id="{slug}-arrow-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
    <polygon points="0 0, 8 3, 0 6" fill="{ACCENT}"/>
  </marker>
  <marker id="{slug}-arrow-link" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
    <polygon points="0 0, 8 3, 0 6" fill="{LINK}"/>
  </marker>
</defs>"""


def svg_header(slug: str, title: str, desc: str, kind_label: str) -> str:
    return f"""
<rect width="960" height="600" fill="{PAPER}"/>
{defs(slug)}
{text(40, 38, kind_label, size=8, fill=MUTED, family=MONO, anchor="start", spacing="0.16em")}
{text(40, 70, title, size=26, fill=INK, family=SERIF, weight=400, anchor="start")}
{text(40, 94, desc, size=10, fill=MUTED, family=SANS, anchor="start")}
<line x1="40" y1="112" x2="920" y2="112" stroke="{RULE}" stroke-width="0.8"/>"""


def legend(
    slug: str,
    y: int = 548,
    *,
    first: str = "执行步骤",
    third: str = "执行方向",
) -> str:
    return f"""
<line x1="40" y1="{y - 16}" x2="920" y2="{y - 16}" stroke="{RULE}" stroke-width="0.8"/>
{text(40, y, "LEGEND", size=8, fill=MUTED, family=MONO, anchor="start", spacing="0.16em")}
<rect x="122" y="{y - 10}" width="28" height="12" rx="2" fill="#fffdf8" stroke="{RULE_STRONG}" stroke-width="0.8"/>
{text(158, y, first, size=9, fill=MUTED, family=SANS, anchor="start")}
<rect x="278" y="{y - 10}" width="28" height="12" rx="2" fill="{ACCENT_TINT}" stroke="{ACCENT}" stroke-width="0.8"/>
{text(314, y, "关键节点", size=9, fill=MUTED, family=SANS, anchor="start")}
<line x1="438" y1="{y - 4}" x2="476" y2="{y - 4}" stroke="{MUTED}" stroke-width="1.2" marker-end="url(#{slug}-arrow)"/>
{text(488, y, third, size=9, fill=MUTED, family=SANS, anchor="start")}"""


def takeaway(value: str) -> str:
    return f"""
<rect x="40" y="344" width="3" height="56" rx="1.5" fill="{ACCENT}"/>
{text(60, 366, "关键判断", size=8, fill=ACCENT, family=MONO, anchor="start", spacing="0.14em")}
{text(60, 388, value, size=13, fill=INK, family=SERIF, anchor="start")}"""


def render_flow(spec: dict) -> str:
    steps = spec["steps"]
    n = len(steps)
    if n < 4 or n > 6:
        raise ValueError(f"{spec['slug']}: flow requires 4-6 steps")
    margin = 40
    gap = 24 if n == 6 else 38
    node_w = (960 - margin * 2 - gap * (n - 1)) / n
    node_h = 112
    y = 190
    cy = y + node_h / 2
    parts: list[str] = []
    focal_index = next((i for i, s in enumerate(steps) if s.get("focal")), n - 1)

    for i in range(n - 1):
        x1 = margin + i * (node_w + gap) + node_w
        x2 = margin + (i + 1) * (node_w + gap)
        stroke = ACCENT if i + 1 == focal_index else MUTED
        marker = f"{spec['slug']}-arrow-accent" if i + 1 == focal_index else f"{spec['slug']}-arrow"
        width = 1.4 if i + 1 == focal_index else 1.1
        parts.append(
            f'<line x1="{x1 + 2:g}" y1="{cy:g}" x2="{x2 - 3:g}" y2="{cy:g}" '
            f'stroke="{stroke}" stroke-width="{width}" marker-end="url(#{marker})"/>'
        )

    for i, step in enumerate(steps):
        x = margin + i * (node_w + gap)
        focal = i == focal_index or bool(step.get("focal"))
        fill = ACCENT_TINT if focal else "#fffdf8"
        stroke = ACCENT if focal else RULE_STRONG
        parts.append(f'<rect x="{x:g}" y="{y}" width="{node_w:g}" height="{node_h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
        tag_w = min(60, max(38, len(step["tag"]) * 7))
        parts.append(f'<rect x="{x + 8:g}" y="{y + 8}" width="{tag_w:g}" height="14" rx="2" fill="transparent" stroke="{stroke}" stroke-width="0.8"/>')
        parts.append(text(x + 8 + tag_w / 2, y + 18, step["tag"], size=7, fill=stroke, family=MONO, spacing="0.08em"))
        lines = step["title"].split("\n")
        start_y = y + 46 if len(lines) == 1 else y + 38
        for j, line in enumerate(lines[:2]):
            parts.append(text(x + node_w / 2, start_y + j * 18, line, size=13, fill=INK, weight=600))
        sub_lines = step.get("sub", [])
        if isinstance(sub_lines, str):
            sub_lines = [sub_lines]
        for j, line in enumerate(sub_lines[:2]):
            parts.append(text(x + node_w / 2, y + 80 + j * 13, line, size=8.5, fill=MUTED, family=MONO))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(spec['title'])}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: {PAPER}; color: {INK}; font-family: {SANS}; }}
    .frame {{ max-width: 1040px; margin: 0 auto; padding: 32px 24px; }}
    .diagram-container {{ width: 100%; overflow-x: auto; }}
    svg {{ width: 100%; min-width: 960px; display: block; }}
  </style>
</head>
<body>
  <div class="frame"><div class="diagram-container">
    <svg viewBox="0 0 960 600" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{spec['slug']}-title {spec['slug']}-desc">
      <title id="{spec['slug']}-title">{esc(spec['title'])}</title>
      <desc id="{spec['slug']}-desc">{esc(spec['desc'])}</desc>
      {svg_header(spec['slug'], spec['title'], spec['desc'], spec.get('eyebrow', 'REPRODUCTION FLOW'))}
      {''.join(parts)}
      {takeaway(spec['takeaway'])}
      {legend(spec['slug'], first="数据变换" if spec['kind'] == 'pipeline' else "执行步骤")}
    </svg>
  </div></div>
</body>
</html>
"""


def render_layers(spec: dict) -> str:
    layers = spec["layers"]
    if not 4 <= len(layers) <= 6:
        raise ValueError(f"{spec['slug']}: layers requires 4-6 entries")
    start_y = 150
    band_h = 62
    gap = 12
    parts: list[str] = []
    for i, layer in enumerate(layers):
        y = start_y + i * (band_h + gap)
        focal = bool(layer.get("focal"))
        fill = ACCENT_TINT if focal else ("#fffdf8" if i % 2 else PAPER_2)
        stroke = ACCENT if focal else RULE
        parts.append(f'<rect x="88" y="{y}" width="800" height="{band_h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
        parts.append(text(112, y + band_h / 2 + 4, layer["index"], size=9, fill=ACCENT if focal else MUTED, family=MONO, anchor="start", spacing="0.10em"))
        parts.append(text(184, y + 27, layer["title"], size=14, fill=INK, weight=600, anchor="start"))
        parts.append(text(184, y + 45, layer.get("sub", ""), size=9, fill=MUTED, anchor="start"))
        parts.append(text(864, y + band_h / 2 + 4, layer.get("note", ""), size=8.5, fill=SOFT, family=MONO, anchor="end"))
    parts.append(f'<line x1="56" y1="{start_y + len(layers) * (band_h + gap) - gap - 8}" x2="56" y2="{start_y + 8}" stroke="{MUTED}" stroke-width="1.2" marker-end="url(#{spec["slug"]}-arrow)"/>')
    parts.append(f'<text x="42" y="{start_y - 14}" fill="{MUTED}" font-size="8" font-family="{MONO}" text-anchor="start" letter-spacing="0.12em">UP</text>')
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(spec['title'])}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: {PAPER}; color: {INK}; font-family: {SANS}; }}
    .frame {{ max-width: 1040px; margin: 0 auto; padding: 32px 24px; }}
    .diagram-container {{ width: 100%; overflow-x: auto; }}
    svg {{ width: 100%; min-width: 960px; display: block; }}
  </style>
</head>
<body>
  <div class="frame"><div class="diagram-container">
    <svg viewBox="0 0 960 600" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{spec['slug']}-title {spec['slug']}-desc">
      <title id="{spec['slug']}-title">{esc(spec['title'])}</title>
      <desc id="{spec['slug']}-desc">{esc(spec['desc'])}</desc>
      {svg_header(spec['slug'], spec['title'], spec['desc'], spec.get('eyebrow', 'LAYER STACK'))}
      {''.join(parts)}
      {legend(spec['slug'], first="层级", third="抽象方向")}
    </svg>
  </div></div>
</body>
</html>
"""


def node_center(node: dict, zone_x: float) -> tuple[float, float, float, float]:
    x = zone_x + 30
    y = node["y"]
    return x, y, x + 200, y + 72


def render_arch(spec: dict) -> str:
    zones = spec["zones"]
    if not 2 <= len(zones) <= 3:
        raise ValueError(f"{spec['slug']}: arch requires 2-3 zones")
    zone_w = 260 if len(zones) == 3 else 380
    gap = 50 if len(zones) == 3 else 40
    start_x = (960 - (zone_w * len(zones) + gap * (len(zones) - 1))) / 2
    zone_y = 150
    zone_h = 330
    nodes_by_id: dict[str, tuple[float, float, float, float]] = {}
    node_zone: dict[str, int] = {}
    zone_parts: list[str] = []
    node_parts: list[str] = []
    for zi, zone in enumerate(zones):
        zx = start_x + zi * (zone_w + gap)
        zone_parts.append(f'<rect x="{zx:g}" y="{zone_y}" width="{zone_w}" height="{zone_h}" rx="8" fill="{ZONE}" stroke="{RULE}" stroke-width="0.8"/>')
        label_w = max(72, len(zone["label"]) * 7)
        zone_parts.append(f'<rect x="{zx + 12:g}" y="{zone_y + 4}" width="{label_w:g}" height="14" rx="2" fill="{PAPER}"/>')
        zone_parts.append(text(zx + 12 + label_w / 2, zone_y + 14, zone["label"], size=7.5, fill=SOFT, family=MONO, spacing="0.12em"))
        for node in zone["nodes"]:
            nx = zx + (zone_w - 200) / 2
            ny = node["y"]
            focal = bool(node.get("focal"))
            fill = ACCENT_TINT if focal else "#fffdf8"
            stroke = ACCENT if focal else RULE_STRONG
            node_parts.append(f'<rect x="{nx:g}" y="{ny}" width="200" height="72" rx="7" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
            tag_w = max(38, len(node["tag"]) * 7)
            node_parts.append(f'<rect x="{nx + 8:g}" y="{ny + 7}" width="{tag_w:g}" height="12" rx="2" fill="transparent" stroke="{stroke}" stroke-width="0.8"/>')
            node_parts.append(text(nx + 8 + tag_w / 2, ny + 16, node["tag"], size=6.5, fill=stroke, family=MONO, spacing="0.06em"))
            node_parts.append(text(nx + 100, ny + 40, node["title"], size=12.5, fill=INK, weight=600))
            node_parts.append(text(nx + 100, ny + 56, node.get("sub", ""), size=8.5, fill=MUTED, family=MONO))
            nodes_by_id[node["id"]] = node_center(node, zx)
            node_zone[node["id"]] = zi

    edges: list[str] = []
    used_sources: set[str] = set()
    used_targets: set[str] = set()
    for edge in spec.get("edges", []):
        source = edge["from"]
        target = edge["to"]
        if node_zone[source] == node_zone[target]:
            raise ValueError(
                f"{spec['slug']}: architecture edges must cross zones: "
                f"{source} -> {target}"
            )
        if source in used_sources or target in used_targets:
            raise ValueError(
                f"{spec['slug']}: architecture edges need unique attach points: "
                f"{source} -> {target}"
            )
        used_sources.add(source)
        used_targets.add(target)
        x1, y1, x2r, y2r = nodes_by_id[edge["from"]]
        xt, yt, _, _ = nodes_by_id[edge["to"]]
        right = x2r
        left = xt
        cy1 = y1 + 36
        cy2 = yt + 36
        reach_focal = bool(edge.get("focal"))
        stroke = ACCENT if reach_focal else (LINK if edge.get("external") else MUTED)
        marker = f"{spec['slug']}-arrow-accent" if reach_focal else (f"{spec['slug']}-arrow-link" if edge.get("external") else f"{spec['slug']}-arrow")
        if abs(cy1 - cy2) < 1:
            path = f"M {right + 3:g},{cy1:g} H {left - 4:g}"
        else:
            mid = (right + left) / 2
            vdir = 1 if cy2 > cy1 else -1
            path = (
                f"M {right + 3:g},{cy1:g} H {mid - 8:g} "
                f"Q {mid:g},{cy1:g} {mid:g},{cy1 + 8 * vdir:g} "
                f"V {cy2 - 8 * vdir:g} "
                f"Q {mid:g},{cy2:g} {mid + 8:g},{cy2:g} H {left - 4:g}"
            )
        edges.append(f'<path d="{path}" fill="none" stroke="{stroke}" stroke-width="1.15" marker-end="url(#{marker})"/>')

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(spec['title'])}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: {PAPER}; color: {INK}; font-family: {SANS}; }}
    .frame {{ max-width: 1040px; margin: 0 auto; padding: 32px 24px; }}
    .diagram-container {{ width: 100%; overflow-x: auto; }}
    svg {{ width: 100%; min-width: 960px; display: block; }}
  </style>
</head>
<body>
  <div class="frame"><div class="diagram-container">
    <svg viewBox="0 0 960 600" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{spec['slug']}-title {spec['slug']}-desc">
      <title id="{spec['slug']}-title">{esc(spec['title'])}</title>
      <desc id="{spec['slug']}-desc">{esc(spec['desc'])}</desc>
      {svg_header(spec['slug'], spec['title'], spec['desc'], spec.get('eyebrow', 'ARCHITECTURE'))}
      {''.join(zone_parts)}
      {''.join(edges)}
      {''.join(node_parts)}
      {legend(spec['slug'], first="组件", third="调用 / 数据流")}
    </svg>
  </div></div>
</body>
</html>
"""


def render(spec: dict) -> str:
    if spec["kind"] in {"flow", "pipeline"}:
        return render_flow(spec)
    if spec["kind"] == "layers":
        return render_layers(spec)
    if spec["kind"] == "arch":
        return render_arch(spec)
    raise ValueError(f"Unknown kind {spec['kind']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", help="generate only these slugs")
    args = parser.parse_args()
    selected = set(args.only or [])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    count = 0
    for spec in DIAGRAMS:
        slug = spec["slug"]
        if slug in seen:
            raise ValueError(f"duplicate diagram slug: {slug}")
        seen.add(slug)
        if selected and slug not in selected:
            continue
        note = ROOT / "content" / "notes" / f"{slug}.md"
        if not note.exists():
            raise FileNotFoundError(f"note not found for diagram: {note}")
        (OUT_DIR / f"{slug}.html").write_text(render(spec), encoding="utf-8")
        count += 1
    print(f"Generated {count} diagram HTML files in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
