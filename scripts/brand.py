"""Render the Telegram Assist brand: a chat bubble with a voice wave, in FlowPilot's colors.

    uv run --no-project --with pillow python scripts/brand.py --font Onest.ttf

``--font`` is the Onest variable TTF (https://github.com/google/fonts/tree/main/ofl/onest), the
wordmark font of the FlowPilot family. Writes:

- ``custom_components/telegram_assist/brand/``  icon, logo (+ @2x, dark_logo) for Home Assistant
- ``assets/social-preview.png``                  GitHub social preview (upload by hand)

PNG, transparent, no empty margins, as home-assistant/brands asks. Not Telegram's logo on purpose.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "custom_components" / "telegram_assist" / "brand"

VIOLET = "#9C7BF0"
TEAL = "#2BB8A6"
WHITE = "#FFFFFF"
INK_LIGHT = "#1D2330"  # wordmark on light backgrounds
INK_DARK = "#E4E7EC"  # wordmark on dark backgrounds
CANVAS = "#1B1F26"
NAME = "Telegram Assist"
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


def font(path: Path, size: int, weight: int = 640) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(path), size)
    f.set_variation_by_axes([weight])
    return f


def logo(height: int, ink: str, font_path: Path) -> Image.Image:
    """Mark and wordmark side by side, trimmed: the short side is ``height``."""
    h = height * 4
    m = mark(h)
    f = font(font_path, int(h * 0.56))
    box = f.getbbox(NAME)
    gap = int(h * 0.22)
    canvas = Image.new("RGBA", (h + gap + box[2] + h, h), (0, 0, 0, 0))
    canvas.paste(m, (0, 0), m)
    ImageDraw.Draw(canvas).text((h + gap, (h - (box[3] + box[1])) // 2), NAME, font=f, fill=ink)
    trimmed = canvas.crop(canvas.getbbox())
    width = round(trimmed.width * height / trimmed.height)
    return trimmed.resize((width, height), Image.Resampling.LANCZOS)


def social(font_path: Path) -> Image.Image:
    img = Image.new("RGB", (1280, 640), CANVAS)
    m = mark(280)
    img.paste(m, (120, 180), m)
    d = ImageDraw.Draw(img)
    d.text((460, 215), NAME, font=font(font_path, 96), fill=INK_DARK)
    tagline = font(font_path, 40, 420)
    d.text((464, 350), "Talk to Home Assistant Assist", font=tagline, fill="#8A93A3")
    d.text((464, 400), "from Telegram, by text and voice", font=tagline, fill="#8A93A3")
    return img


def save(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)
    print(f"{path.relative_to(ROOT)}  {img.width}x{img.height}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", type=Path, required=True, help="Onest variable TTF")
    font_path = parser.parse_args().font
    save(mark(256), OUT / "icon.png")
    save(mark(512), OUT / "icon@2x.png")
    save(logo(128, INK_LIGHT, font_path), OUT / "logo.png")
    save(logo(256, INK_LIGHT, font_path), OUT / "logo@2x.png")
    save(logo(128, INK_DARK, font_path), OUT / "dark_logo.png")
    save(logo(256, INK_DARK, font_path), OUT / "dark_logo@2x.png")
    save(social(font_path), ROOT / "assets" / "social-preview.png")


if __name__ == "__main__":
    main()
