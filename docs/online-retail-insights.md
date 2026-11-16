# Online retail trading and customer insights

**UCI Online Retail II · 24 complete months from December 2009 through November 2011**

The business question is whether the second year’s increase in gross sales carried through to net recorded sales, and what customer behaviour and sales mix help explain the result. The source covers a UK-based online giftware retailer that also sold to wholesalers. [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii)

## Cancellations absorbed most of the increase in gross sales

| Measure | Dec 2009–Nov 2010 | Dec 2010–Nov 2011 | Change |
| --- | ---: | ---: | ---: |
| Gross sales | £9,834,131.64 | £10,004,320.47 | +1.7% |
| Cancellation value | £568,444.45 | £688,890.46 | +21.2% |
| Net recorded sales | £9,265,687.19 | £9,315,430.01 | +0.5% |
| Cancellation value as a share of gross sales | 5.8% | 6.9% | +1.1 pp |
| Purchase invoices, summed across months | 20,117 | 19,141 | −4.9% |
| Eligible purchase lines with a customer ID | 80.1% | 75.1% | −4.9 pp |

Gross sales rose by **£170,189**, while cancellation value increased by **£120,446**. The higher cancellation value absorbed about **71% of the gross increase**, leaving **£49,743** in additional net recorded sales. November was the strongest month in both years, at £1.42m and £1.46m in net recorded sales. An operations review should start with which stock codes and invoice types contributed to the higher cancellation value.

Cancellation value is assigned to the cancellation invoice date. The data contains no direct link to the original purchase invoice for each cancellation, so the percentage above is a period-level value ratio.

## Separate merchandise from administrative codes

The UK accounted for **84.8% of gross sales** over the 24 complete months. Ireland (recorded as EIRE), the Netherlands, Germany, and France were the next four markets by gross sales. These are countries recorded on the invoices.

`Manual` (code `M`) led the all-code gross ranking at **£338,788** but ended at **−£83,733 in net recorded sales** after cancellations. The leading merchandise code was the Regency Cakestand 3 Tier (`22423`), with **£324,596 gross** and **£308,155 net**. The dashboard ranks stock codes by gross sales and includes entries such as Manual and Postage. For a merchandise review, distinguish those entries from saleable products and use net as well as gross sales.

## Repeat purchasing depends on customer ID coverage

Across the complete months, **4,200 of 5,850 identified purchasers (71.8%)** placed at least two eligible orders. **2,118 (36.2%)** placed five or more. Across all eligible purchase lines in those months, **77.6%** had a customer ID. Coverage was lower in the second year, so the observed repeat rate describes identified purchasers.

| Months since first observed purchase | Customers active that month | Eligible cohort members | Retention |
| --- | ---: | ---: | ---: |
| 1 | 1,327 | 5,659 | 23.4% |
| 3 | 1,305 | 5,249 | 24.9% |
| 6 | 1,089 | 4,933 | 22.1% |
| 12 | 968 | 4,266 | 22.7% |

Repeat rate counts purchasers who returned at any point in the reporting window. Cohort retention measures whether they purchased in a specific month after their first observed order. At month 23 only one cohort remains eligible, so interpret the far-right end of the combined curve in light of its smaller denominator. Power BI can isolate first-purchase dates, while Tableau shows the combined curve.

## Reproduce the analysis

The source has **1,067,371 invoice lines** across two overlapping sheets. The model retains **1,033,036 distinct lines** and preserves every source row in staging. Exact matching uses all eight fields. Some repeated lines may be legitimate because the workbook has no line identifier. December 2011 is partial and excluded from the comparisons above. Changes are calculated from unrounded values.

[Power BI report](../powerbi/Retail%20Sales%20and%20Customer%20Performance.pbip) · [Tableau workbook](../tableau/Retail%20Sales%20and%20Customer%20Performance.twbx) · [Data cleaning and rebuild instructions](../README.md)
