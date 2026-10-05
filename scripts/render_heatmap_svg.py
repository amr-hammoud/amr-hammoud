"""Render data/contributions.json as an animated heatmap (contrib-heatmap.svg).

Boxes slide in along diagonals once on load, then freeze (CSS keyframes).
Without the JSON it draws an empty grid so the README never shows a broken image.
STATIC=1 emits a frozen frame.
"""

import json
import os
from datetime import date, timedelta
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "contributions.json")
OUT = os.path.join(ROOT, "contrib-heatmap.svg")

# none -> brightest; level 5 is a neon top end for the busiest days
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
BG = "#0d1117"
BORDER = "#30363d"
TEXT = "#8b949e"
STRONG = "#c9d1d9"

WIDTH = 860
CELL = 12
GAP = 3
STEP = CELL + GAP
LEFT = 54
TOP = 44
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def load():
    if os.path.exists(DATA):
        with open(DATA, encoding="utf-8") as f:
            return json.load(f)
    # placeholder: last 53 weeks, all empty
    today = date.today()
    start = today - timedelta(days=52 * 7 + (today.weekday() + 1) % 7)
    days = [{"date": (start + timedelta(i)).isoformat(), "count": 0, "level": 0}
            for i in range((today - start).days + 1)]
    return {"placeholder": True, "total": 0, "days": days, "current_streak": 0, "longest_streak": 0,
            "best_day": {"date": today.isoformat(), "count": 0}}


def neon_threshold(days):
    """Count above which a day gets the extra level-5 color (top ~3% of active days)."""
    counts = sorted(d["count"] for d in days if d["count"] > 0)
    if len(counts) < 20:
        return None
    return counts[int(len(counts) * 0.97)]


def build_svg(data, static=False):
    days = data["days"]
    first = date.fromisoformat(days[0]["date"])
    # calendar columns start on Sunday
    origin = first - timedelta(days=(first.weekday() + 1) % 7)
    neon = neon_threshold(days)

    cells = []
    month_labels = {}
    for d in days:
        dt = date.fromisoformat(d["date"])
        offset = (dt - origin).days
        col, row = offset // 7, offset % 7
        level = min(int(d.get("level", 0)), 4)
        if neon is not None and d["count"] >= neon and d["count"] > 0:
            level = 5
        cells.append((col, row, level, d))
        if row == 0 and dt.day <= 7:
            month_labels.setdefault(col, MONTHS[dt.month - 1])

    cols = max(c for c, *_ in cells) + 1
    grid_w = cols * STEP - GAP
    left = (WIDTH - grid_w - LEFT) / 2 + LEFT  # center grid + labels
    grid_h = 7 * STEP - GAP
    legend_y = TOP + grid_h + 26
    height = legend_y + 52

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="{WIDTH}" '
        f'height="{height}" role="img" aria-label="{data["total"]} contributions in the last year">',
        "<style>",
        "text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}",
        ".c{opacity:0;animation:drop .5s cubic-bezier(.2,.7,.3,1) forwards}",
        "@keyframes drop{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:none}}",
        ".f{opacity:0;animation:fade .6s ease-out forwards}",
        "@keyframes fade{to{opacity:1}}",
        ".s .c,.s .f{opacity:1;animation:none}",
        "</style>",
        f'<g class="{"s" if static else ""}">',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
    ]

    for col, label in month_labels.items():
        if col > cols - 2:
            continue
        out.append(f'<text x="{left + col * STEP:.1f}" y="{TOP - 10}" fill="{TEXT}" font-size="11">{label}</text>')
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(
            f'<text x="{left - 10:.1f}" y="{TOP + row * STEP + CELL - 2}" fill="{TEXT}" '
            f'font-size="10" text-anchor="end">{label}</text>'
        )

    for col, row, level, d in cells:
        delay = (col + row) * 0.022
        noun = "contribution" if d["count"] == 1 else "contributions"
        out.append(
            f'<rect class="c" style="animation-delay:{delay:.3f}s" x="{left + col * STEP:.1f}" '
            f'y="{TOP + row * STEP}" width="{CELL}" height="{CELL}" rx="2.5" fill="{PALETTE[level]}">'
            f'<title>{d["count"]} {noun} on {d["date"]}</title></rect>'
        )

    end = (cols + 7) * 0.022 + 0.3
    fade = f' style="animation-delay:{end:.2f}s"'

    # legend
    lx = left + grid_w - len(PALETTE) * STEP - 34
    out.append(f'<g class="f"{fade}>')
    out.append(f'<text x="{lx - 8:.1f}" y="{legend_y + 10}" fill="{TEXT}" font-size="11" text-anchor="end">Less</text>')
    for i, c in enumerate(PALETTE):
        out.append(f'<rect x="{lx + i * STEP:.1f}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{c}"/>')
    out.append(f'<text x="{lx + len(PALETTE) * STEP + 4:.1f}" y="{legend_y + 10}" fill="{TEXT}" font-size="11">More</text>')

    # stats footer
    best = data.get("best_day", {})
    if data.get("placeholder"):
        out.append(
            f'<text x="{left:.1f}" y="{legend_y + 10}" fill="{STRONG}" font-size="12" font-weight="bold">'
            f'syncing contributions…</text>'
        )
        out.append(
            f'<text x="{left:.1f}" y="{legend_y + 32}" fill="{TEXT}" font-size="11">'
            f'filled in by the daily GitHub Action</text>'
        )
        out.append("</g></g></svg>")
        return "\n".join(out) + "\n"
    out.append(
        f'<text x="{left:.1f}" y="{legend_y + 10}" fill="{STRONG}" font-size="12" font-weight="bold">'
        f'{data["total"]:,} contributions in the last year</text>'
    )
    parts = [
        f'current streak {data.get("current_streak", 0)}d',
        f'longest streak {data.get("longest_streak", 0)}d',
    ]
    if best.get("count"):
        parts.append(f'best day {best["count"]} on {best["date"]}')
    out.append(
        f'<text x="{left:.1f}" y="{legend_y + 32}" fill="{TEXT}" font-size="11">'
        f'{escape("  ·  ".join(parts))}</text>'
    )
    out.append("</g></g></svg>")
    return "\n".join(out) + "\n"


def main():
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build_svg(load(), static=os.environ.get("STATIC") == "1"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
