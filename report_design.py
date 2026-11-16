"""Shared palette and period commentary for the two retail reports."""

import csv
from datetime import date
from decimal import Decimal

from export_bi import DATA

NAVY = "#11284B"
INK = "#172D4B"
MUTED = "#506581"
CANVAS = "#EFF4FA"
WHITE = "#FFFFFF"
BLUE = "#2358C8"
TEAL = "#007F80"
ORANGE = "#B84D1C"
PURPLE = "#7143B5"

PERIOD = "Dec 2009–Nov 2011"


def read_rows(table):
    with (DATA / f"{table}.csv").open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def report_notes():
    sales = read_rows("sales")
    first, second = (sum(Decimal(row["net"]) for row in block)
                     for block in (sales[:12], sales[12:]))
    peak = max(sales, key=lambda row: Decimal(row["net"]))
    peak_month = date.fromisoformat(peak["month"]).strftime("%b %Y")
    leading_market = read_rows("markets")[0]
    market_share = Decimal(leading_market["market_gross"]) / sum(Decimal(row["gross"]) for row in sales)
    return {
        "sales": f"Second-year net sales {second / first - 1:+.1%}  |  Peak month {peak_month} · £{Decimal(peak['net']) / 1_000_000:.2f}m",
        "mix": f"{leading_market['country']} accounted for {market_share:.1%} of gross sales across all markets.",
        "retention": "Each point uses cohorts with enough follow-up. Month 0 is the first observed purchase month.",
    }
