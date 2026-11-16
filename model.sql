CREATE TABLE dim_product (
    stock_code TEXT PRIMARY KEY,
    description TEXT
);

INSERT INTO dim_product
WITH descriptions AS (
    SELECT stock_code, description, ROW_NUMBER() OVER (
        PARTITION BY stock_code
        ORDER BY CASE WHEN NULLIF(TRIM(description), '') IS NULL THEN 1 ELSE 0 END,
                 invoice_time DESC, line_id DESC
    ) AS preference
    FROM stage_invoice_line
    WHERE is_duplicate = 0
)
SELECT stock_code, NULLIF(TRIM(description), '')
FROM descriptions
WHERE preference = 1;

CREATE TABLE dim_customer (
    customer_id TEXT PRIMARY KEY
);

INSERT INTO dim_customer
SELECT DISTINCT customer_id FROM stage_invoice_line WHERE customer_id IS NOT NULL;

CREATE TABLE fact_invoice_line (
    line_id INTEGER PRIMARY KEY REFERENCES stage_invoice_line(line_id),
    invoice TEXT NOT NULL,
    stock_code TEXT NOT NULL REFERENCES dim_product(stock_code),
    invoice_date TEXT NOT NULL REFERENCES dim_date(invoice_date),
    invoice_time TEXT NOT NULL,
    customer_id TEXT REFERENCES dim_customer(customer_id),
    country TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price_units INTEGER NOT NULL,
    line_type TEXT NOT NULL CHECK (line_type IN ('sale', 'cancellation', 'exception'))
);

INSERT INTO fact_invoice_line
SELECT line_id, invoice, stock_code, DATE(invoice_time), invoice_time, customer_id,
       country, quantity, price_units,
       CASE
           WHEN price_units > 0 AND is_cancellation = 0 AND quantity > 0 THEN 'sale'
           WHEN price_units > 0 AND is_cancellation = 1 AND quantity < 0 THEN 'cancellation'
           ELSE 'exception'
       END
FROM stage_invoice_line
WHERE is_duplicate = 0;

CREATE INDEX fact_invoice_line_date ON fact_invoice_line(invoice_date);

CREATE VIEW sales_line AS
SELECT f.*, d.invoice_month, d.is_complete_month,
       CASE WHEN line_type = 'sale' THEN quantity * price_units ELSE 0 END AS gross_units,
       CASE WHEN line_type = 'cancellation' THEN -quantity * price_units ELSE 0 END
           AS cancellation_units
FROM fact_invoice_line AS f
JOIN dim_date AS d USING (invoice_date)
WHERE line_type IN ('sale', 'cancellation');

CREATE VIEW monthly_sales AS
SELECT invoice_month, is_complete_month,
       SUM(gross_units) / 10000.0 AS gross_sales_gbp,
       SUM(cancellation_units) / 10000.0 AS cancellation_value_gbp,
       SUM(gross_units - cancellation_units) / 10000.0 AS net_recorded_sales_gbp,
       COUNT(DISTINCT invoice) FILTER (WHERE line_type = 'sale') AS orders,
       COUNT(*) FILTER (WHERE line_type = 'sale') AS purchase_lines,
       COUNT(customer_id) FILTER (WHERE line_type = 'sale') AS identified_purchase_lines,
       1.0 * COUNT(customer_id) FILTER (WHERE line_type = 'sale')
           / NULLIF(COUNT(*) FILTER (WHERE line_type = 'sale'), 0) AS customer_id_coverage
FROM sales_line
GROUP BY invoice_month, is_complete_month;

CREATE VIEW monthly_product_sales AS
SELECT invoice_month, is_complete_month, stock_code,
       SUM(gross_units) / 10000.0 AS gross_sales_gbp,
       SUM(cancellation_units) / 10000.0 AS cancellation_value_gbp,
       SUM(gross_units - cancellation_units) / 10000.0 AS net_recorded_sales_gbp,
       1.0 * SUM(gross_units)
           / NULLIF(SUM(SUM(gross_units)) OVER (PARTITION BY invoice_month), 0) AS gross_sales_share
FROM sales_line
GROUP BY invoice_month, is_complete_month, stock_code;

CREATE VIEW monthly_country_sales AS
SELECT invoice_month, is_complete_month, country,
       SUM(gross_units) / 10000.0 AS gross_sales_gbp,
       SUM(cancellation_units) / 10000.0 AS cancellation_value_gbp,
       SUM(gross_units - cancellation_units) / 10000.0 AS net_recorded_sales_gbp,
       1.0 * SUM(gross_units)
           / NULLIF(SUM(SUM(gross_units)) OVER (PARTITION BY invoice_month), 0) AS gross_sales_share
FROM sales_line
GROUP BY invoice_month, is_complete_month, country;

CREATE VIEW customer_orders AS
SELECT customer_id, invoice, MIN(invoice_time) AS order_time
FROM sales_line
WHERE line_type = 'sale' AND customer_id IS NOT NULL AND is_complete_month = 1
GROUP BY customer_id, invoice;

CREATE VIEW customer_purchase_summary AS
SELECT customer_id, COUNT(*) AS order_count, SUBSTR(MIN(order_time), 1, 7) AS cohort_month
FROM customer_orders
GROUP BY customer_id;

CREATE VIEW repeat_purchase AS
SELECT COUNT(*) AS identified_purchasers,
       COUNT(*) FILTER (WHERE order_count >= 2) AS repeat_purchasers,
       1.0 * COUNT(*) FILTER (WHERE order_count >= 2) / NULLIF(COUNT(*), 0) AS repeat_rate
FROM customer_purchase_summary;

CREATE VIEW cohort_retention AS
WITH sizes AS (
    SELECT cohort_month, COUNT(*) AS customers
    FROM customer_purchase_summary
    GROUP BY cohort_month
), activity AS (
    SELECT p.cohort_month, SUBSTR(o.order_time, 1, 7) AS activity_month,
           COUNT(DISTINCT o.customer_id) AS active_customers
    FROM customer_orders AS o
    JOIN customer_purchase_summary AS p USING (customer_id)
    GROUP BY p.cohort_month, activity_month
), complete_months AS (
    SELECT DISTINCT invoice_month FROM dim_date WHERE is_complete_month = 1
)
SELECT s.cohort_month, m.invoice_month AS activity_month,
       (CAST(SUBSTR(m.invoice_month, 1, 4) AS INTEGER)
           - CAST(SUBSTR(s.cohort_month, 1, 4) AS INTEGER)) * 12
           + CAST(SUBSTR(m.invoice_month, 6, 2) AS INTEGER)
           - CAST(SUBSTR(s.cohort_month, 6, 2) AS INTEGER) AS months_since_first_purchase,
       s.customers AS cohort_size, COALESCE(a.active_customers, 0) AS active_customers,
       1.0 * COALESCE(a.active_customers, 0) / s.customers AS retention_rate
FROM sizes AS s
JOIN complete_months AS m ON m.invoice_month >= s.cohort_month
LEFT JOIN activity AS a ON a.cohort_month = s.cohort_month AND a.activity_month = m.invoice_month;
