#!/usr/bin/env python3
"""Generate the placeholder avatar, favicons and Open Graph cover."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
IMAGES = STATIC / "images"

WINDOWS_FONT_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")
WINDOWS_FONT_REGULAR = Path(r"C:\Windows\Fonts\msyh.ttc")


def blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def radial_background(
    size: tuple[int, int],
    inner: tuple[int, int, int] = (24, 63, 56),
    outer: tuple[int, int, int] = (7, 17, 15),
    center: tuple[float, float] = (0.24, 0.16),
) -> Image.Image:
    width, height = size
    small = Image.new("RGB", (120, 120))
    pixels = small.load()
    cx = center[0] * 119
    cy = center[1] * 119
    max_distance = math.hypot(119, 119)

    for y in range(120):
        for x in range(120):
            distance = math.hypot(x - cx, y - cy) / max_distance
            pixels[x, y] = blend(inner, outer, min(distance * 1.22, 1.0))

    return small.resize((width, height), Image.Resampling.BICUBIC).convert("RGBA")


def draw_swirl(canvas: Image.Image, center: tuple[float, float], radius: float, scale: float = 1.0) -> None:
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow = Image.new("L", canvas.size, 0)
    glow_draw = ImageDraw.Draw(glow)

    spiral: list[tuple[float, float]] = []
    steps = 260
    turns = 3.1
    for index in range(steps):
        t = index / (steps - 1)
        angle = -math.pi * 0.55 + t * turns * math.tau
        current_radius = radius * (1.0 - 0.83 * t)
        x = center[0] + math.cos(angle) * current_radius
        y = center[1] + math.sin(angle) * current_radius * 0.90
        spiral.append((x, y))

    glow_draw.line(spiral, fill=145, width=max(2, round(28 * scale)), joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(max(3, round(22 * scale))))

    teal_glow = Image.new("RGBA", canvas.size, (94, 234, 212, 0))
    teal_glow.putalpha(glow)
    overlay.alpha_composite(teal_glow)

    draw = ImageDraw.Draw(overlay)
    segment_count = len(spiral) - 1
    for index in range(segment_count):
        t = index / max(segment_count, 1)
        color = blend((94, 234, 212), (232, 197, 71), t)
        draw.line(
            (spiral[index], spiral[index + 1]),
            fill=(*color, 255),
            width=max(2, round(13 * scale)),
            joint="curve",
        )

    ring_draw = ImageDraw.Draw(overlay)
    ring_width = max(1, round(2 * scale))
    for ring_radius, alpha in ((radius * 1.20, 34), (radius * 1.35, 22), (radius * 1.50, 13)):
        box = (
            center[0] - ring_radius,
            center[1] - ring_radius,
            center[0] + ring_radius,
            center[1] + ring_radius,
        )
        ring_draw.ellipse(box, outline=(94, 234, 212, alpha), width=ring_width)

    canvas.alpha_composite(overlay)


def load_font(path: Path, size: int, fallback_size: int | None = None) -> ImageFont.FreeTypeFont:
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=fallback_size or size)


def make_profile() -> Image.Image:
    scale = 3
    size = 360
    canvas = radial_background((size * scale, size * scale))

    # Soft highlight in the lower-right corner.
    highlight = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(highlight)
    draw.ellipse(
        (
            size * scale * 0.58,
            size * scale * 0.60,
            size * scale * 1.15,
            size * scale * 1.16,
        ),
        fill=(232, 197, 71, 20),
    )
    highlight = highlight.filter(ImageFilter.GaussianBlur(60 * scale))
    canvas.alpha_composite(highlight)

    draw_swirl(
        canvas,
        center=(size * scale * 0.52, size * scale * 0.52),
        radius=size * scale * 0.38,
        scale=scale,
    )

    dot = ImageDraw.Draw(canvas)
    dot.ellipse(
        (
            size * scale * 0.67,
            size * scale * 0.25,
            size * scale * 0.73,
            size * scale * 0.31,
        ),
        fill=(232, 197, 71, 255),
    )

    return canvas.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)


def make_cover() -> Image.Image:
    output_size = (1200, 630)
    scale = 2
    canvas = radial_background(
        (output_size[0] * scale, output_size[1] * scale),
        inner=(22, 67, 59),
        outer=(7, 17, 15),
        center=(0.76, 0.30),
    )

    draw_swirl(
        canvas,
        center=(output_size[0] * scale * 0.78, output_size[1] * scale * 0.48),
        radius=output_size[1] * scale * 0.34,
        scale=scale,
    )

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        (0, 0, output_size[0] * scale * 0.58, output_size[1] * scale),
        fill=(7, 17, 15, 58),
    )
    canvas.alpha_composite(overlay)

    draw = ImageDraw.Draw(canvas)
    title_font = load_font(WINDOWS_FONT_BOLD, 220 * scale)
    subtitle_font = load_font(WINDOWS_FONT_REGULAR, 62 * scale)
    meta_font = load_font(WINDOWS_FONT_REGULAR, 38 * scale)

    left = 92 * scale
    draw.rounded_rectangle(
        (left, 115 * scale, left + 12 * scale, 196 * scale),
        radius=6 * scale,
        fill=(94, 234, 212, 255),
    )
    draw.text((left + 38 * scale, 90 * scale), "漩涡", font=title_font, fill=(237, 247, 242, 255))
    draw.text(
        (left + 38 * scale, 365 * scale),
        "记录代码、安全与思考",
        font=subtitle_font,
        fill=(201, 216, 210, 255),
    )
    draw.text(
        (left + 38 * scale, 475 * scale),
        "xuanwo  ·  网络安全 / CTF / 漏洞复现",
        font=meta_font,
        fill=(94, 234, 212, 255),
    )

    return canvas.convert("RGB").resize(output_size, Image.Resampling.LANCZOS)


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)

    profile = make_profile()
    profile.save(IMAGES / "profile.png", optimize=True)
    profile.resize((32, 32), Image.Resampling.LANCZOS).save(STATIC / "favicon-32x32.png", optimize=True)
    profile.resize((16, 16), Image.Resampling.LANCZOS).save(STATIC / "favicon-16x16.png", optimize=True)
    profile.resize((180, 180), Image.Resampling.LANCZOS).save(STATIC / "apple-touch-icon.png", optimize=True)

    make_cover().save(IMAGES / "og-cover.png", optimize=True)
    print("Generated profile.png, favicons and og-cover.png")


if __name__ == "__main__":
    main()

