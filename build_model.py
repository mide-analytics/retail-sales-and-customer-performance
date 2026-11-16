"""Build a local SQLite model from UCI Online Retail II."""

from argparse import ArgumentParser
from contextlib import closing
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from openpyxl import load_workbook

from profile_workbook import EXPECTED_ROWS, invoice_rows, is_blank, is_cancellation_invoice


PROJECT = Path(__file__).resolve().parent
PRICE_SCALE = 10_000


def stage_rows(workbook):
    seen = set()
    for sheet in workbook.worksheets:
        for number, row in enumerate(invoice_rows(sheet), start=2):
            invoice, stock, description, quantity, timestamp, price, customer, country = row
            scaled_price = Decimal(str(price)) * PRICE_SCALE
            if scaled_price != int(scaled_price):
                raise ValueError(f"{sheet.title} row {number}: unsupported price precision {price}")
            duplicate = row in seen
            seen.add(row)
            yield (
                sheet.title, number, str(invoice), str(stock), description, quantity,
                timestamp.isoformat(sep=" "), int(scaled_price),
                None if is_blank(customer) else str(customer), country,
                is_cancellation_invoice(invoice), duplicate,
            )


def calendar_rows(first, last):
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        following = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
        complete = day.replace(day=1) >= first and following - timedelta(days=1) <= last
        yield day.isoformat(), day.strftime("%Y-%m"), complete


def build(source, destination):
    if source.resolve() == destination.resolve():
        raise ValueError("The source workbook and SQLite output must use different paths.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Build beside the destination so a failed refresh leaves the prior database usable.
    with TemporaryDirectory(dir=destination.parent) as temp:
        pending = Path(temp) / "model.sqlite"
        with closing(sqlite3.connect(pending)) as db:
            db.execute("PRAGMA foreign_keys = ON")
            db.executescript("""
                CREATE TABLE stage_invoice_line (
                    line_id INTEGER PRIMARY KEY,
                    source_sheet TEXT NOT NULL,
                    source_row INTEGER NOT NULL,
                    invoice TEXT NOT NULL,
                    stock_code TEXT NOT NULL,
                    description TEXT,
                    quantity INTEGER NOT NULL,
                    invoice_time TEXT NOT NULL,
                    price_units INTEGER NOT NULL,
                    customer_id TEXT,
                    country TEXT NOT NULL,
                    is_cancellation INTEGER NOT NULL,
                    is_duplicate INTEGER NOT NULL,
                    UNIQUE(source_sheet, source_row)
                );
                CREATE TABLE dim_date (
                    invoice_date TEXT PRIMARY KEY,
                    invoice_month TEXT NOT NULL,
                    is_complete_month INTEGER NOT NULL
                );
            """)
            with closing(load_workbook(source, read_only=True, data_only=True)) as workbook:
                db.executemany("""
                    INSERT INTO stage_invoice_line (
                        source_sheet, source_row, invoice, stock_code, description,
                        quantity, invoice_time, price_units, customer_id, country,
                        is_cancellation, is_duplicate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, stage_rows(workbook))
            count, first, last = db.execute("""
                SELECT COUNT(*), DATE(MIN(invoice_time)), DATE(MAX(invoice_time))
                FROM stage_invoice_line
            """).fetchone()
            if count != EXPECTED_ROWS:
                raise ValueError(f"Expected {EXPECTED_ROWS:,} source rows, loaded {count:,}.")
            db.executemany(
                "INSERT INTO dim_date VALUES (?, ?, ?)",
                calendar_rows(date.fromisoformat(first), date.fromisoformat(last)),
            )
            db.executescript((PROJECT / "model.sql").read_text(encoding="utf-8"))
            db.commit()
            if db.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("The model contains a broken dimension link.")
        pending.replace(destination)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=PROJECT / "data/raw/online_retail_II.xlsx")
    parser.add_argument("--output", type=Path, default=PROJECT / "data/model/retail.sqlite")
    args = parser.parse_args()
    build(args.source, args.output)
    print(f"Built {args.output}")
