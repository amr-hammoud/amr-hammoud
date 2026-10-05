"""Render a neofetch-style info card (info-card.svg).

Edit CARD below, then: python scripts/make_info_card.py
STATIC=1 emits a frozen frame (handy for local previews).
"""

import os
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "info-card.svg")

USER = "amr"
HOST = "github"

# (key, value) rows; None draws a blank spacer line
CARD = [
    ("Name", "Amr Hammoud"),
    ("Role", "Full-Stack Developer"),
    ("Also", "RoboTech Instructor"),
    ("Edu", "B.S. Computer Science"),
    ("Hobbies", "Photography & Design"),
    None,
    ("Languages", "TypeScript, Python, JavaScript, Java, C#, PHP"),
    ("Frontend", "React, Next.js, Redux, Tailwind, MUI, D3"),
    ("Backend", "NestJS, Express, Laravel, GraphQL"),
    ("Data", "PostgreSQL, MySQL, MongoDB, Redis, Prisma"),
    ("DevOps", "Docker, AWS, GCP, Linux, Jest"),
    ("Hardware", "Arduino, Raspberry Pi, Flutter"),
    ("Creative", "Figma, Photoshop, Lightroom, Premiere"),
]

BG = "#0d1117"
BAR = "#161b22"
BORDER = "#30363d"
KEY = "#3fb950"
VAL = "#c9d1d9"
DIM = "#8b949e"
BLOCKS = ["#484f58", "#f85149", "#3fb950", "#d29922", "#58a6ff", "#bc8cff", "#39c5cf", "#e6edf3"]

WIDTH = 490
FONT_SIZE = 12.5
LINE_H = 19
PAD_X = 22
BAR_H = 30
KEY_COL = 96


def build_svg(static=False):
    header = f"{USER}@{HOST}"
    lines = [("header", header), ("rule", "-" * len(header))]
    lines += [("blank", None) if row is None else ("kv", row) for row in CARD]
    lines += [("blank", None), ("blocks", None)]

    top = BAR_H + 22
    height = top + len(lines) * LINE_H + 12
    stagger = 0.09
    base = 0.4

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="{WIDTH}" '
        f'height="{height}" role="img" aria-label="{escape(header)} info card">',
        "<style>",
        ".l{opacity:0;animation:in .45s ease-out forwards}",
        "@keyframes in{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}",
        ".s .l{opacity:1;animation:none}",
        "</style>",
        f'<g class="{"s" if static else ""}">',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<path d="M0.5 {BAR_H} V10.5 a10 10 0 0 1 10 -10 H{WIDTH - 10.5} a10 10 0 0 1 10 10 V{BAR_H} Z" fill="{BAR}"/>',
        f'<line x1="0.5" y1="{BAR_H}" x2="{WIDTH - 0.5}" y2="{BAR_H}" stroke="{BORDER}"/>',
    ]
    for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        out.append(f'<circle cx="{20 + i * 18}" cy="{BAR_H / 2}" r="5.5" fill="{c}"/>')
    out.append(
        f'<text x="{WIDTH / 2}" y="{BAR_H / 2 + 4}" text-anchor="middle" fill="{DIM}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="12">'
        f'{escape(header)}: ~ — neofetch</text>'
    )
    out.append(
        f'<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,\'DejaVu Sans Mono\',monospace" '
        f'font-size="{FONT_SIZE}" xml:space="preserve">'
    )
    for i, (kind, data) in enumerate(lines):
        y = top + i * LINE_H
        delay = f' style="animation-delay:{base + i * stagger:.2f}s"'
        if kind == "header":
            out.append(
                f'<text class="l"{delay} x="{PAD_X}" y="{y}" font-weight="bold">'
                f'<tspan fill="{KEY}">{USER}</tspan><tspan fill="{VAL}">@</tspan>'
                f'<tspan fill="{KEY}">{HOST}</tspan></text>'
            )
        elif kind == "rule":
            out.append(f'<text class="l"{delay} x="{PAD_X}" y="{y}" fill="{DIM}">{data}</text>')
        elif kind == "kv":
            key, val = data
            out.append(
                f'<text class="l"{delay} x="{PAD_X}" y="{y}">'
                f'<tspan fill="{KEY}" font-weight="bold">{escape(key)}</tspan>'
                f'<tspan x="{PAD_X + KEY_COL}" fill="{VAL}">{escape(val)}</tspan></text>'
            )
        elif kind == "blocks":
            out.append(f'<g class="l"{delay}>')
            for j, c in enumerate(BLOCKS):
                out.append(f'<rect x="{PAD_X + j * 24}" y="{y - 13}" width="24" height="16" fill="{c}"/>')
            out.append("</g>")
    out.append("</g></g></svg>")
    return "\n".join(out) + "\n"


def main():
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build_svg(static=os.environ.get("STATIC") == "1"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
