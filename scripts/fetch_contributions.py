"""Scrape the public contribution calendar into data/contributions.json.

No token needed: https://github.com/users/<user>/contributions is the same
HTML fragment the profile page loads.

  python scripts/fetch_contributions.py [username]
  python scripts/fetch_contributions.py --html saved.html   # parse a local copy
"""

import argparse
import json
import os
import re
from collections import OrderedDict
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "contributions.json")
DEFAULT_USER = os.environ.get("GITHUB_USER", "amr-hammoud")

COUNT_RE = re.compile(r"^\s*([\d,]+)\s+contributions?", re.I)


def fetch_html(user):
    resp = requests.get(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "profile-heatmap-bot"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def parse(html):
    soup = BeautifulSoup(html, "html.parser")

    # tooltips carry the counts: "3 contributions on May 4th." / "No contributions on ..."
    tips = {}
    for tip in soup.find_all("tool-tip"):
        target = tip.get("for")
        if target:
            m = COUNT_RE.match(tip.get_text())
            tips[target] = int(m.group(1).replace(",", "")) if m else 0

    days = []
    for cell in soup.select("td.ContributionCalendar-day[data-date]"):
        level = int(cell.get("data-level", 0) or 0)
        count = tips.get(cell.get("id"))
        if count is None:
            # older markup put the count on the cell itself
            count = int(cell.get("data-count", 0) or 0)
        days.append({"date": cell["data-date"], "count": count, "level": level})
    if not days:
        raise SystemExit("No contribution cells found; GitHub markup may have changed")
    days.sort(key=lambda d: d["date"])

    total = sum(d["count"] for d in days)
    heading = soup.find(id="js-contribution-activity-description")
    if heading:
        m = COUNT_RE.match(heading.get_text())
        if m:
            total = int(m.group(1).replace(",", ""))
    return days, total


def stats(days):
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)

    # current streak may start yesterday if nothing has landed yet today
    current = 0
    tail = list(reversed(days))
    if tail and tail[0]["count"] == 0:
        tail = tail[1:]
    for d in tail:
        if d["count"] == 0:
            break
        current += 1

    best = max(days, key=lambda d: d["count"])
    months = OrderedDict()
    for d in days:
        months[d["date"][:7]] = months.get(d["date"][:7], 0) + d["count"]
    return {
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "active_days": sum(1 for d in days if d["count"] > 0),
        "monthly": months,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("user", nargs="?", default=DEFAULT_USER)
    ap.add_argument("--html", help="parse a saved contributions HTML file instead of fetching")
    args = ap.parse_args()

    if args.html:
        with open(args.html, encoding="utf-8") as f:
            html = f.read()
    else:
        html = fetch_html(args.user)
    days, total = parse(html)

    data = {
        "user": args.user,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": total,
        **stats(days),
        "days": days,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
        f.write("\n")
    print(f"wrote {OUT}: {total} contributions over {len(days)} days")


if __name__ == "__main__":
    main()
