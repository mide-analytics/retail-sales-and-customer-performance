"""Profile the original UCI Online Retail II workbook (requires openpyxl)."""

from argparse import ArgumentParser
from collections import Counter
from hashlib import file_digest
from json import dumps
from pathlib import Path

from openpyxl import load_workbook


HEADERS = (
    "Invoice", "StockCode", "Description", "Quantity", "InvoiceDate",
    "Price", "Customer ID", "Country",
)
EXPECTED_ROWS = 1_067_371
METRICS = (
    "rows", "missing_customer_id", "missing_description", "cancellation_lines",
    "zero_price", "negative_price", "zero_quantity", "negative_quantity",
    "cancellation_nonnegative_quantity", "cancellation_nonpositive_price",
    "noncancellation_negative_quantity", "duplicate_rows_beyond_first",
)


def is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def invoice_rows(sheet):
    rows = sheet.iter_rows(values_only=True)
    headers = next(rows)
    if headers != HEADERS:
        raise ValueError(f"{sheet.title}: unexpected header {headers!r}")
    return rows


def is_cancellation_invoice(invoice):
    return str(invoice).upper().startswith("C")


def profile_sheet(sheet, workbook_rows):
    counts = Counter(dict.fromkeys(METRICS, 0))
    cancellations = set()
    local_rows = set()
    dates = set()
    for row in invoice_rows(sheet):
        invoice, _, description, quantity, date, price, customer, _ = row
        is_cancellation = is_cancellation_invoice(invoice)
        counts["rows"] += 1
        counts["missing_customer_id"] += is_blank(customer)
        counts["missing_description"] += is_blank(description)
        counts["cancellation_lines"] += is_cancellation
        counts["zero_price"] += price == 0
        counts["negative_price"] += price < 0
        counts["zero_quantity"] += quantity == 0
        counts["negative_quantity"] += quantity < 0
        counts["cancellation_nonnegative_quantity"] += is_cancellation and quantity >= 0
        counts["cancellation_nonpositive_price"] += is_cancellation and price <= 0
        counts["noncancellation_negative_quantity"] += not is_cancellation and quantity < 0
        counts["duplicate_rows_beyond_first"] += row in local_rows
        if is_cancellation:
            cancellations.add(str(invoice).upper())
        local_rows.add(row)
        dates.add(date.date())

    shared_rows = len(local_rows & workbook_rows)
    workbook_rows.update(local_rows)
    return counts, cancellations, shared_rows, min(dates).isoformat(), max(dates).isoformat()


def profile(path):
    with path.open("rb") as source:
        sha256 = file_digest(source, "sha256").hexdigest()

    workbook = load_workbook(path, read_only=True, data_only=True)
    combined = Counter()
    all_cancellations = set()
    workbook_rows = set()
    sheets = {}
    cross_sheet_matches = 0
    try:
        for sheet in workbook.worksheets:
            counts, cancellations, shared, start_date, end_date = profile_sheet(sheet, workbook_rows)
            sheets[sheet.title] = {
                **counts, "distinct_cancellation_invoices": len(cancellations),
                "first_date": start_date, "last_date": end_date,
            }
            combined.update(counts)
            all_cancellations.update(cancellations)
            cross_sheet_matches += shared
    finally:
        workbook.close()

    combined["duplicate_rows_beyond_first"] += cross_sheet_matches
    return {
        "workbook_sha256": sha256,
        "sheets": sheets,
        "combined": {
            **combined, "distinct_cancellation_invoices": len(all_cancellations),
            "cross_sheet_exact_matches": cross_sheet_matches,
            "published_rows": EXPECTED_ROWS,
            "difference_from_published_rows": combined["rows"] - EXPECTED_ROWS,
        },
    }


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "workbook", type=Path, nargs="?",
        default=Path(__file__).parent / "data" / "raw" / "online_retail_II.xlsx",
    )
    args = parser.parse_args()
    print(dumps(profile(args.workbook), indent=2))
