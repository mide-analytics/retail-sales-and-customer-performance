"""Export aggregate report inputs from the validated retail SQLite model."""

import csv
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "bi"
TITLE = "Retail Sales and Customer Performance"

QUERIES = {
    "sales": """
        SELECT invoice_month || '-01' AS month, gross_sales_gbp AS gross,
               cancellation_value_gbp AS cancellations, net_recorded_sales_gbp AS net,
               orders, identified_purchase_lines AS known_lines, purchase_lines
        FROM monthly_sales WHERE is_complete_month = 1 ORDER BY month
    """,
    "products": """
        SELECT COALESCE(p.description, 'No description') || ' (' || s.stock_code || ')' AS product,
               ROUND(SUM(s.gross_sales_gbp), 4) AS product_gross
        FROM monthly_product_sales AS s JOIN dim_product AS p USING (stock_code)
        WHERE s.is_complete_month = 1
        GROUP BY s.stock_code, p.description ORDER BY product_gross DESC, product LIMIT 10
    """,
    "markets": """
        SELECT country, ROUND(SUM(gross_sales_gbp), 4) AS market_gross
        FROM monthly_country_sales WHERE is_complete_month = 1
        GROUP BY country ORDER BY market_gross DESC, country LIMIT 10
    """,
    "repeat": 'SELECT identified_purchasers AS purchasers, repeat_purchasers AS "returning" FROM repeat_purchase',
    "cohorts": """
        SELECT cohort_month || '-01' AS cohort, months_since_first_purchase AS elapsed_month,
               cohort_size, active_customers AS active
        FROM cohort_retention ORDER BY cohort, elapsed_month
    """,
}


def export():
    source = ROOT / "data/model/retail.sqlite"
    DATA.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as db:
        with db:
            db.execute("BEGIN")
            for name, sql in QUERIES.items():
                rows = db.execute(sql)
                with (DATA / f"{name}.csv").open("w", encoding="utf-8", newline="") as output:
                    writer = csv.writer(output)
                    writer.writerow(column[0] for column in rows.description)
                    writer.writerows(rows)


if __name__ == "__main__":
    export()
