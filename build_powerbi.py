"""Generate the retail Power BI project from aggregate SQLite exports."""

import csv
import json
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from export_bi import DATA, ROOT, TITLE
from report_design import BLUE, CANVAS, INK, MUTED, NAVY, ORANGE, PERIOD, PURPLE, TEAL, WHITE, report_notes

OUTPUT = ROOT / "powerbi"
NAME = TITLE
MODEL = OUTPUT / f"{NAME}.SemanticModel"
REPORT = OUTPUT / f"{NAME}.Report"
DEFINITION = REPORT / "definition"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"


def save(path, value, schema=None):
    if schema:
        value = {"$schema": f"{SCHEMA}/{schema}/schema.json", **value}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def quoted(text):
    return '"' + text.replace('"', '""') + '"'


def lineage(name):
    return str(uuid5(NAMESPACE_URL, f"{NAME}/{name}"))


def import_table(name, filename, fields):
    types = ", ".join(f'{{"{field}", {mtype}}}' for field, _, mtype in fields)
    names = ", ".join(quoted(field) for field, _, _ in fields)
    with (DATA / filename).open(encoding="utf-8", newline="") as source:
        rows = [
            "        {" + ", ".join(quoted(row[field]) for field, _, _ in fields) + "}"
            for row in csv.DictReader(source)
        ]
    columns = []
    for field, dtype, _ in fields:
        label = field.replace("_", " ").title().replace("Id", "ID").replace("Gbp", "GBP")
        columns.append({
            "name": label, "sourceColumn": field, "dataType": dtype,
            "summarizeBy": "none", "lineageTag": lineage(f"{name}/{field}"),
            **({"formatString": "MMM yyyy"} if field in {"month", "cohort"} else {}),
        })
    return {
        "name": name, "columns": columns, "lineageTag": lineage(name),
        "annotations": [{"name": "PBI_ResultType", "value": "Table"}],
        "partitions": [{"name": name, "mode": "import", "source": {
            "type": "m", "expression": [
                "let",
                f"    RetailRows = #table({{{names}}}, {{",
                ",\n".join(rows),
                "    })",
                f'in Table.TransformColumnTypes(RetailRows, {{{types}}}, "en-GB")',
            ],
        }}],
    }


TEXT = ("string", "type text")
INTEGER = ("int64", "Int64.Type")
DATE = ("dateTime", "type date")
DECIMAL = ("double", "type number")
CURRENCY = ("decimal", "Currency.Type")


def measure(name, expression, fmt="#,0"):
    return {"name": name, "expression": expression, "formatString": fmt}


def literal(value):
    return {"expr": {"Literal": {"Value": value}}}


def fill(color):
    return {"solid": {"color": literal(f"'{color}'")}}


def background(color, page=False):
    properties = {"color": fill(color), "transparency": literal("0D")}
    if not page:
        properties["show"] = literal("true")
    return [{"properties": properties}]


def field(entity, property_name, kind="Column"):
    return {
        "field": {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": property_name}},
        "queryRef": f"{entity}.{property_name}",
        "nativeQueryRef": property_name,
    }


class Page:
    def __init__(self, title, subtitle, accent, definition=DEFINITION):
        self.name = self.key(title)
        self.directory = definition / "pages" / self.name
        self.order = 0
        save(self.directory / "page.json", {
            "name": self.name, "displayName": title, "displayOption": "FitToPage",
            "width": 1280, "height": 720,
            "objects": {"background": background(CANVAS, page=True)},
        }, "item/report/definition/page/2.3.1")
        self.text("Page heading", (24, 18, 1232, 83), [
            (title, "27pt", WHITE), (subtitle, "11pt", "#D9E7F7"),
        ], NAVY)
        self.text("Header accent", (24, 101, 1232, 5), [], accent)

    @staticmethod
    def key(value):
        return sha256(value.encode()).hexdigest()[:20]

    def visual(self, title, box, visual_type, roles=None, objects=None, sort=None, color=WHITE, show_title=True):
        self.order += 1000
        x, y, width, height = box
        name = self.key(title)
        visual = {"visualType": visual_type, "visualContainerObjects": {"background": background(color)}}
        if visual_type != "textbox":
            visual["visualContainerObjects"]["title"] = [{"properties": {
                "show": literal("true" if show_title else "false"), "text": literal(f"'{title}'"),
                "fontColor": fill(INK), "fontSize": literal("13D"), "bold": literal("true"),
            }}]
            visual["drillFilterOtherVisuals"] = True
        if objects:
            visual["objects"] = objects
        if roles:
            visual["query"] = {"queryState": {role: {"projections": projections} for role, projections in roles.items()}}
        if sort:
            projection, direction = sort
            visual["query"]["sortDefinition"] = {"sort": [{"field": projection["field"], "direction": direction}]}
        save(self.directory / "visuals" / name / "visual.json", {
            "name": name, "position": {"x": x, "y": y, "width": width, "height": height,
                                       "z": self.order, "tabOrder": self.order},
            "visual": visual,
        }, "item/report/definition/visualContainer/2.14.0")

    def text(self, title, box, lines, color=CANVAS):
        paragraphs = [{"textRuns": [{"value": text, "textStyle": {"fontSize": size, "color": color}}]}
                      for text, size, color in lines]
        self.visual(title, box, "textbox", objects={"general": [{"properties": {"paragraphs": paragraphs}}]}, color=color)

    def cards(self, measures):
        width = (1232 - (len(measures) - 1) * 16) / len(measures)
        for index, (entity, metric, accent, tint) in enumerate(measures):
            self.visual(metric, (24 + (width + 16) * index, 122, width, 106), "card",
                        {"Values": [field(entity, metric, "Measure")]},
                        objects={
                            "labels": [{"properties": {"fontSize": literal("25D"), "color": fill(accent),
                                                       "labelDisplayUnits": literal("1D")}}],
                            "categoryLabels": [{"properties": {"show": literal("false")}}],
                        }, color=tint)

    def chart(self, title, box, visual_type, category, metric, color):
        objects = {"dataPoint": [{"properties": {"fill": fill(color)}}]}
        if visual_type == "lineChart":
            objects["lineStyles"] = [{"properties": {
                "lineChartType": literal("'linear'"), "strokeWidth": literal("3D"),
            }}]
        else:
            objects["labels"] = [{"properties": {"show": literal("true"), "color": fill(INK)}}]
        self.visual(title, box, visual_type, {"Category": [category], "Y": [metric]},
                    objects=objects, sort=(category, "Ascending") if visual_type == "lineChart" else (metric, "Descending"))


def write_report_shell(output, name):
    report = output / f"{name}.Report"
    model = output / f"{name}.SemanticModel"
    definition = report / "definition"
    save(output / f"{name}.pbip", {
        "version": "1.0", "artifacts": [{"report": {"path": report.name}}],
        "settings": {"enableAutoRecovery": True},
    }, "pbip/pbipProperties/1.0.0")
    save(report / "definition.pbir", {
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{model.name}"}},
    }, "item/report/definitionProperties/2.0.0")
    save(definition / "version.json", {"version": "2.0.0"}, "item/report/definition/versionMetadata/1.0.0")
    theme = "Fluent2-CY26SU10"
    save(definition / "report.json", {
        "themeCollection": {"baseTheme": {
            "name": theme, "type": "SharedResources",
            "reportVersionAtImport": {"visual": "2.14.0", "report": "3.4.0", "page": "2.3.1"},
        }},
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources",
                              "items": [{"name": theme, "path": f"BaseThemes/{theme}.json", "type": "BaseTheme"}]}],
    }, "item/report/definition/report/3.3.0")
    return definition, model


def build_report():
    write_report_shell(OUTPUT, NAME)

    def metric(table, name):
        return field(table, name, "Measure")

    notes = report_notes()
    sales = Page("Sales performance", f"ONLINE RETAIL II   /   {PERIOD}   /   GBP", BLUE)
    sales.cards([
        ("Sales", "Gross sales", BLUE, "#E2ECFF"),
        ("Sales", "Cancellation value", ORANGE, "#FCEBDD"),
        ("Sales", "Net recorded sales", TEAL, "#DFF4EF"),
        ("Sales", "Customer ID coverage", PURPLE, "#EFE5FC"),
    ])
    sales.text("Period comparison", (24, 239, 1232, 35), [(notes["sales"], "12pt", TEAL)], "#E1F4F2")
    sales.chart("Monthly net recorded sales", (24, 284, 1232, 226), "lineChart",
                field("Sales", "Month"), metric("Sales", "Net recorded sales"), TEAL)
    sales.chart("Monthly purchase invoices", (24, 522, 608, 176), "lineChart",
                field("Sales", "Month"), metric("Sales", "Purchase invoices"), BLUE)
    sales.chart("Monthly cancellation value", (648, 522, 608, 176), "lineChart",
                field("Sales", "Month"), metric("Sales", "Cancellation value"), ORANGE)

    mix = Page("Product and market mix", f"TOP 10 STOCK CODES AND COUNTRIES   /   {PERIOD}   /   GBP", TEAL)
    mix.text("Market concentration", (24, 122, 1232, 38), [(notes["mix"], "12pt", TEAL)], "#E1F4F2")
    mix.chart("Stock codes by gross sales", (24, 174, 696, 492), "barChart",
              field("Products", "Product"), metric("Products", "Stock code gross sales"), BLUE)
    mix.chart("Markets by gross sales", (736, 174, 520, 492), "barChart",
              field("Markets", "Country"), metric("Markets", "Market gross sales"), TEAL)
    mix.text("Stock code scope", (24, 672, 1232, 28), [
        ("Stock codes include non-merchandise charges such as Manual and Postage.", "10pt", MUTED),
    ])

    customers = Page("Customer retention", f"IDENTIFIED PURCHASERS   /   {PERIOD}", PURPLE)
    customers.cards([
        ("Repeat", "Identified purchasers", BLUE, "#E2ECFF"),
        ("Repeat", "Repeat purchasers", TEAL, "#DFF4EF"),
        ("Repeat", "Repeat purchase rate", PURPLE, "#EFE5FC"),
    ])
    customers.visual("First purchase cohort", (24, 244, 220, 405), "slicer",
                     {"Values": [field("Cohorts", "Cohort")]})
    customers.chart("Retention by months since first purchase", (260, 244, 996, 405), "lineChart",
                    field("Cohorts", "Elapsed Month"), metric("Cohorts", "Cohort retention"), PURPLE)
    customers.text("Retention denominator", (24, 661, 1232, 37), [
        (notes["retention"] + " The selector filters the trend.", "11pt", PURPLE),
    ], "#EFE5FC")

    save(DEFINITION / "pages" / "pages.json", {
        "pageOrder": [page.name for page in (sales, mix, customers)], "activePageName": sales.name,
    }, "item/report/definition/pagesMetadata/1.1.0")


def build_model():
    sales = import_table("Sales", "sales.csv", [
        ("month", *DATE), ("gross", *CURRENCY), ("cancellations", *CURRENCY), ("net", *CURRENCY),
        ("orders", *INTEGER), ("known_lines", *INTEGER), ("purchase_lines", *INTEGER),
    ])
    products = import_table("Products", "products.csv", [("product", *TEXT), ("product_gross", *CURRENCY)])
    markets = import_table("Markets", "markets.csv", [("country", *TEXT), ("market_gross", *CURRENCY)])
    repeat = import_table("Repeat", "repeat.csv", [("purchasers", *INTEGER), ("returning", *INTEGER)])
    cohorts = import_table("Cohorts", "cohorts.csv", [
        ("cohort", *DATE), ("elapsed_month", *INTEGER), ("cohort_size", *INTEGER), ("active", *INTEGER),
    ])
    currency = "£#,0.00"
    sales["measures"] = [
        measure("Gross sales", "SUM('Sales'[Gross])", currency),
        measure("Cancellation value", "SUM('Sales'[Cancellations])", currency),
        measure("Net recorded sales", "[Gross sales] - [Cancellation value]", currency),
        measure("Purchase invoices", "SUM('Sales'[Orders])"),
        measure("Customer ID coverage", "DIVIDE(SUM('Sales'[Known Lines]), SUM('Sales'[Purchase Lines]))", "0.0%"),
    ]
    products["measures"] = [measure("Stock code gross sales", "SUM('Products'[Product Gross])", currency)]
    markets["measures"] = [measure("Market gross sales", "SUM('Markets'[Market Gross])", currency)]
    repeat["measures"] = [
        measure("Identified purchasers", "SUM('Repeat'[Purchasers])"),
        measure("Repeat purchasers", "SUM('Repeat'[Returning])"),
        measure("Repeat purchase rate", "DIVIDE([Repeat purchasers], [Identified purchasers])", "0.0%"),
    ]
    cohorts["measures"] = [
        measure("Cohort retention", "DIVIDE(SUM('Cohorts'[Active]), SUM('Cohorts'[Cohort Size]))", "0.0%"),
    ]
    save(MODEL / "model.bim", {
        "name": NAME, "compatibilityLevel": 1600,
        "model": {
            "culture": "en-GB", "sourceQueryCulture": "en-GB",
            "defaultPowerBIDataSourceVersion": "powerBI_V3", "discourageImplicitMeasures": True,
            "annotations": [
                {"name": "PBI_QueryOrder", "value": json.dumps(["Sales", "Products", "Markets", "Repeat", "Cohorts"])},
                {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
            ],
            "tables": [sales, products, markets, repeat, cohorts],
        },
    })
    save(MODEL / "definition.pbism", {"version": "4.0", "settings": {}},
         "item/semanticModel/definitionProperties/1.0.0")


if __name__ == "__main__":
    build_model()
    build_report()
