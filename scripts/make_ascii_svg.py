"""Render ASCII art as a self-typing SVG (ascii-art.svg).

Two sources:
  python scripts/make_ascii_svg.py                      # big "AMR" wordmark
  python scripts/make_ascii_svg.py --text HELLO
  python scripts/make_ascii_svg.py --image source-prepped.png   # portrait

Each row is revealed by a left-to-right clip wipe with a block cursor riding
the edge, staggered top to bottom. It plays once and freezes (SMIL), which
GitHub renders when the SVG is embedded with <img>.
"""

import argparse
import os
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "ascii-art.svg")

RAMP = " .`:-=+*cs#%@"  # bright (sparse) -> dark (dense)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

BG = "#0d1117"
BORDER = "#30363d"
FG = "#c9d1d9"
CURSOR = "#3fb950"

CHAR_W = 6.6   # monospace advance at FONT_SIZE (0.6em)
LINE_H = 11.0
FONT_SIZE = 11
PAD = 20


def text_darkness(text, cols, stretch=3.1):
    """Rasterize text and shade it like a bevelled block so the ramp has depth."""
    font_path = next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)
    if font_path is None:
        raise SystemExit("No bold TTF font found; add one to FONT_CANDIDATES")
    font = ImageFont.truetype(font_path, 400)
    left, top, right, bottom = font.getbbox(text)
    margin = 40
    img = Image.new("L", (right - left + 2 * margin, bottom - top + 2 * margin), 0)
    ImageDraw.Draw(img).text((margin - left, margin - top), text, font=font, fill=255)

    mask = np.asarray(img, dtype=np.float32) / 255.0
    height = np.asarray(img.filter(ImageFilter.GaussianBlur(14)), dtype=np.float32) / 255.0
    gy, gx = np.gradient(height)
    # light from the top-left: edges facing it get lighter, others darker
    shade = -(gx + gy) * 18.0
    dark = mask * np.clip(0.82 + shade, 0.35, 1.0)

    # characters are ~2x taller than wide, so halve the row count;
    # stretch makes the letters tall enough to balance the info card
    rows = max(1, round(cols * img.height / img.width / 2.0 * stretch))
    small = Image.fromarray((dark * 255).astype(np.uint8)).resize((cols, rows), Image.LANCZOS)
    return np.asarray(small, dtype=np.float32) / 255.0


def image_darkness(path, cols):
    img = Image.open(path).convert("L")
    rows = max(1, round(cols * img.height / img.width / 2.0))
    small = img.resize((cols, rows), Image.LANCZOS)
    return 1.0 - np.asarray(small, dtype=np.float32) / 255.0


def to_lines(dark):
    idx = np.clip((dark * (len(RAMP) - 1)).round().astype(int), 0, len(RAMP) - 1)
    lines = ["".join(RAMP[i] for i in row) for row in idx]
    # drop fully blank rows at top/bottom
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def build_svg(lines, static=False, aspect=None):
    """aspect = height/width of the panel; art is centered vertically inside it."""
    cols = max(len(l) for l in lines)
    text_w = cols * CHAR_W
    width = text_w + 2 * PAD
    height = len(lines) * LINE_H + 2 * PAD
    top = PAD
    if aspect and width * aspect > height:
        top += (width * aspect - height) / 2
        height = width * aspect

    row_dur = 0.32
    stagger = 0.07
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height:.1f}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img" aria-label="ASCII art">',
        f'<rect x="0.5" y="0.5" width="{width - 1:.1f}" height="{height - 1:.1f}" rx="10" '
        f'fill="{BG}" stroke="{BORDER}"/>',
        "<defs>",
    ]
    for i, _ in enumerate(lines):
        y = top + i * LINE_H
        if static:
            out.append(f'<clipPath id="r{i}"><rect x="{PAD}" y="{y:.1f}" width="{text_w:.1f}" height="{LINE_H}"/></clipPath>')
        else:
            out.append(
                f'<clipPath id="r{i}"><rect x="{PAD}" y="{y:.1f}" width="0" height="{LINE_H}">'
                f'<animate attributeName="width" from="0" to="{text_w:.1f}" begin="{i * stagger:.2f}s" '
                f'dur="{row_dur}s" fill="freeze"/></rect></clipPath>'
            )
    out.append("</defs>")
    out.append(
        f'<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,\'DejaVu Sans Mono\',monospace" '
        f'font-size="{FONT_SIZE}" fill="{FG}" xml:space="preserve">'
    )
    for i, line in enumerate(lines):
        # no-break spaces: plain spaces collapse in some SVG renderers
        line = line.ljust(cols).replace(" ", "\u00a0")
        y = top + i * LINE_H + LINE_H * 0.8
        out.append(
            f'<text x="{PAD}" y="{y:.1f}" textLength="{text_w:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'clip-path="url(#r{i})">{escape(line)}</text>'
        )
    out.append("</g>")

    if not static:
        # one cursor that jumps row to row along the wipe edge, then blinks at the end
        end = len(lines) * stagger + row_dur
        last_y = top + (len(lines) - 1) * LINE_H
        out.append(f'<rect width="{CHAR_W:.1f}" height="{LINE_H - 1:.1f}" fill="{CURSOR}" x="{PAD}" y="{top:.1f}">')
        for i, _ in enumerate(lines):
            y = top + i * LINE_H
            b = i * stagger
            out.append(f'<set attributeName="y" to="{y:.1f}" begin="{b:.2f}s"/>')
            out.append(
                f'<animate attributeName="x" from="{PAD}" to="{PAD + text_w:.1f}" begin="{b:.2f}s" '
                f'dur="{row_dur}s" fill="freeze"/>'
            )
        out.append(f'<set attributeName="y" to="{last_y + LINE_H:.1f}" begin="{end:.2f}s"/>')
        out.append(f'<set attributeName="x" to="{PAD}" begin="{end:.2f}s"/>')
        out.append(
            f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" '
            f'begin="{end:.2f}s" repeatCount="5" fill="freeze"/>'
        )
        out.append("</rect>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--text", default="AMR")
    src.add_argument("--image", help="prepped grayscale portrait (white background)")
    ap.add_argument("--cols", type=int, default=None)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--aspect", type=float, default=387 / 370,
                    help="panel height/width; default matches the info card beside it")
    args = ap.parse_args()

    if args.image:
        dark = image_darkness(args.image, args.cols or 100)
    else:
        dark = text_darkness(args.text, args.cols or 52)
    lines = to_lines(dark)
    svg = build_svg(lines, static=os.environ.get("STATIC") == "1", aspect=args.aspect)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {args.out} ({len(lines)} rows)")


if __name__ == "__main__":
    main()
