"""Render the Telegram Assist icon: a chat bubble with a voice wave, in FlowPilot's colors.

    uv run --no-project --with pillow python scripts/brand.py

Writes ``custom_components/telegram_assist/brand/icon.png`` and ``icon@2x.png`` (PNG,
transparent, no empty margins, as home-assistant/brands asks). Not Telegram's logo on purpose.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "custom_components" / "telegram_assist" / "brand"

VIOLET = "#9C7BF0"
TEAL = "#2BB8A6"
WHITE = "#FFFFFF"
SCALE = 8  # draw large, then shrink: smooth edges


def mark(size: int) -> Image.Image:
    s = size * SCALE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # the bubble with its tail at the bottom left
    d.rounded_rectangle((0, 0, s, 0.80 * s), radius=0.24 * s, fill=VIOLET)
    d.polygon([(0.14 * s, 0.70 * s), (0.10 * s, s), (0.42 * s, 0.76 * s)], fill=VIOLET)
    # the voice wave: five rounded bars
    heights = [0.20, 0.38, 0.52, 0.38, 0.20]
    bar, gap = 0.085 * s, 0.065 * s
    total = len(heights) * bar + (len(heights) - 1) * gap
    x = (s - total) / 2
    for i, h in enumerate(heights):
        top, bottom = 0.40 * s - h * s / 2, 0.40 * s + h * s / 2
        color = TEAL if i == len(heights) // 2 else WHITE
        d.rounded_rectangle((x, top, x + bar, bottom), radius=bar / 2, fill=color)
        x += bar + gap
    return img.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mark(256).save(OUT / "icon.png")
    mark(512).save(OUT / "icon@2x.png")
    print("written", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
