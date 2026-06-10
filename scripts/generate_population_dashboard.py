import csv
import json
from pathlib import Path


INPUT_PATH = Path("data/real/inkar_2025_municipality_population_observations.csv")
HOUSING_PRICE_INPUT_PATH = Path("data/real/neighborhood_housing_prices.csv")
MARKET_INDICATOR_INPUT_PATH = Path("data/real/inkar_2025_municipality_market_indicators.csv")
OUTPUT_PATH = Path("output/population_growth_dashboard.html")

PRICE_METRIC_COLUMNS = {
    "median_housing_price": "Median official guideline value",
    "mean_housing_price": "Mean official guideline value",
    "stddev_housing_price": "Standard deviation of guideline values",
}


def main() -> int:
    observations = []
    with INPUT_PATH.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["metric"] != "population":
                continue
            observations.append(
                {
                    "city": row["city"],
                    "city_id": row["city_id"],
                    "year": int(row["year"]),
                    "value": float(row["value"]),
                }
            )

    if not observations:
        raise SystemExit(f"No population observations found in {INPUT_PATH}")

    housing_prices = read_housing_price_observations()
    market_indicators = read_market_indicator_observations()
    years = sorted({item["year"] for item in observations})
    cities = sorted({item["city"] for item in observations})
    default_start = max(years[0], years[-1] - 9)
    payload = {
        "observations": observations,
        "metadata": {
            "source": "BBSR INKAR 2025",
            "metric": "population",
            "unit": "people",
            "city_count": len(cities),
            "year_min": years[0],
            "year_max": years[-1],
            "default_start": default_start,
            "default_end": years[-1],
            "generated_from": str(INPUT_PATH),
            "housing_price_input": str(HOUSING_PRICE_INPUT_PATH),
            "market_indicator_input": str(MARKET_INDICATOR_INPUT_PATH),
            "housing_price_loaded": bool(housing_prices),
            "market_indicators_loaded": bool(market_indicators),
        },
        "housing_prices": housing_prices,
        "market_indicators": market_indicators,
    }

    html = build_html(payload)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(observations)} population observations.")
    return 0


def read_housing_price_observations() -> list:
    if not HOUSING_PRICE_INPUT_PATH.exists():
        return []

    observations = []
    with HOUSING_PRICE_INPUT_PATH.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"city", "area", "year", *PRICE_METRIC_COLUMNS}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise SystemExit(
                f"{HOUSING_PRICE_INPUT_PATH} is missing required columns: "
                f"{', '.join(sorted(missing))}"
            )

        for row in reader:
            observation = {
                "city": row["city"].strip(),
                "city_id": (row.get("city_id") or "").strip(),
                "area": row["area"].strip(),
                "year": int(row["year"]),
                "unit": (row.get("unit") or "EUR_per_m2").strip(),
                "source": (row.get("source") or "").strip(),
                "price_basis": (row.get("price_basis") or "Housing price").strip(),
                "coverage_level": (row.get("coverage_level") or "area").strip(),
                "source_area": (row.get("source_area") or row["area"]).strip(),
            }
            for metric in PRICE_METRIC_COLUMNS:
                observation[metric] = parse_optional_float(row.get(metric, ""))
            observations.append(observation)

    return observations


def read_market_indicator_observations() -> list:
    if not MARKET_INDICATOR_INPUT_PATH.exists():
        return []

    observations = []
    with MARKET_INDICATOR_INPUT_PATH.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
            "city",
            "city_id",
            "year",
            "metric",
            "value",
            "unit",
            "source",
            "coverage_level",
            "source_area",
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise SystemExit(
                f"{MARKET_INDICATOR_INPUT_PATH} is missing required columns: "
                f"{', '.join(sorted(missing))}"
            )

        for row in reader:
            observations.append(
                {
                    "city": row["city"].strip(),
                    "city_id": row["city_id"].strip(),
                    "year": int(row["year"]),
                    "metric": row["metric"].strip(),
                    "value": float(row["value"]),
                    "unit": row["unit"].strip(),
                    "source": row["source"].strip(),
                    "coverage_level": row["coverage_level"].strip(),
                    "source_area": row["source_area"].strip(),
                }
            )

    return observations


def parse_optional_float(raw: str):
    value = raw.strip()
    if not value:
        return None
    value = value.replace(" ", "")
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")
    return float(value)


def build_html(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>German City Population Growth</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f4ef;
      --surface: #ffffff;
      --surface-2: #f0eee8;
      --ink: #222426;
      --muted: #62686f;
      --line: #d8d4ca;
      --blue: #3168a6;
      --green: #3e7b4f;
      --orange: #bc6c25;
      --red: #a64035;
      --purple: #7057a3;
      --teal: #207c7c;
      --shadow: 0 12px 32px rgba(28, 31, 35, 0.08);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.4;
      overflow: auto;
    }}

    button,
    input,
    select {{
      font: inherit;
    }}

    .app {{
      min-height: 100vh;
      min-height: 100dvh;
      display: grid;
      grid-template-rows: auto auto auto auto auto auto;
      overflow: visible;
    }}

    header {{
      padding: 16px 24px 12px;
      border-bottom: 1px solid var(--line);
      background: #fbfaf7;
    }}

    .title-row {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 18px;
      flex-wrap: wrap;
    }}

    h1 {{
      margin: 0;
      font-size: 22px;
      line-height: 1.1;
      font-weight: 760;
      letter-spacing: 0;
    }}

    .source {{
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}

    .tabs {{
      display: flex;
      gap: 8px;
      padding: 8px 24px 0;
      background: var(--surface);
    }}

    .tab-button {{
      height: 34px;
      border: 1px solid var(--line);
      border-bottom-color: transparent;
      border-radius: 7px 7px 0 0;
      background: #f7f5ef;
      color: var(--muted);
      padding: 0 14px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
    }}

    .tab-button.active {{
      background: var(--ink);
      color: #fff;
      border-color: var(--ink);
    }}

    .toolbar {{
      display: grid;
      grid-template-columns: minmax(170px, 1.2fr) repeat(10, minmax(90px, auto));
      gap: 12px;
      padding: 10px 24px;
      align-items: end;
      border-bottom: 1px solid var(--line);
      background: var(--surface);
    }}

    label {{
      display: grid;
      gap: 5px;
      min-width: 0;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      text-transform: uppercase;
    }}

    input,
    select {{
      height: 38px;
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      color: var(--ink);
      padding: 0 10px;
      outline: none;
    }}

    input:focus,
    select:focus,
    button:focus-visible {{
      border-color: var(--blue);
      box-shadow: 0 0 0 3px rgba(49, 104, 166, 0.14);
    }}

    .segmented {{
      display: inline-grid;
      grid-template-columns: repeat(2, minmax(86px, 1fr));
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 7px;
      overflow: hidden;
      background: var(--surface-2);
    }}

    .segmented button,
    .small-button {{
      border: 0;
      background: transparent;
      color: var(--muted);
      padding: 0 12px;
      cursor: pointer;
      white-space: nowrap;
    }}

    .segmented button.active {{
      background: var(--ink);
      color: #fff;
    }}

    .small-button {{
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      color: var(--ink);
      font-weight: 650;
    }}

    .definitions {{
      padding: 8px 24px;
      border-bottom: 1px solid var(--line);
      background: #fbfaf7;
      color: var(--muted);
      font-size: 12px;
    }}

    .definitions summary {{
      cursor: pointer;
      color: var(--ink);
      font-weight: 760;
    }}

    .definitions-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 8px 18px;
      padding-top: 8px;
    }}

    .definitions-grid b {{
      color: var(--ink);
    }}

    .page {{
      display: grid;
      grid-template-columns: minmax(330px, 430px) minmax(0, 1fr);
      gap: 18px;
      padding: 14px 24px;
      min-height: calc(100vh - 230px);
      overflow: visible;
    }}

    .page[hidden] {{
      display: none;
    }}

    .panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      min-width: 0;
      min-height: 0;
      overflow: hidden;
    }}

    .active-filters {{
      grid-column: 1 / -1;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 7px;
      padding: 9px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfaf7;
      color: var(--muted);
      font-size: 12px;
      box-shadow: var(--shadow);
    }}

    .filter-title {{
      color: var(--ink);
      font-weight: 760;
      margin-right: 2px;
    }}

    .filter-chip {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border: 1px solid #d8d4ca;
      border-radius: 999px;
      background: #fff;
      padding: 3px 8px;
      white-space: nowrap;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 3px 7px;
      color: #fff;
      font-size: 11px;
      font-weight: 760;
      white-space: nowrap;
    }}

    .quality-high {{
      background: var(--green);
    }}

    .quality-medium {{
      background: var(--orange);
    }}

    .quality-low,
    .quality-insufficient {{
      background: var(--red);
    }}

    .rank-panel {{
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr);
    }}

    .rank-panel,
    .chart-panel,
    .classification-panel {{
      min-height: 640px;
    }}

    .panel-head {{
      padding: 14px 16px 10px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}

    h2 {{
      margin: 0;
      font-size: 15px;
      letter-spacing: 0;
    }}

    .count {{
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1px;
      background: var(--line);
      border-bottom: 1px solid var(--line);
    }}

    .stat {{
      background: #fbfaf7;
      padding: 12px 14px;
      min-width: 0;
    }}

    .stat-value {{
      font-size: 20px;
      font-weight: 760;
      white-space: nowrap;
    }}

    .stat-label {{
      color: var(--muted);
      font-size: 12px;
      margin-top: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .table-wrap {{
      overflow: auto;
      min-height: 0;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}

    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: #fbfaf7;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      text-align: right;
      border-bottom: 1px solid var(--line);
      padding: 9px 10px;
    }}

    th:first-child,
    td:first-child {{
      text-align: left;
    }}

    td {{
      border-bottom: 1px solid #ece8de;
      padding: 9px 10px;
      text-align: right;
      white-space: nowrap;
    }}

    td:first-child {{
      max-width: 210px;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    tr {{
      cursor: pointer;
    }}

    tr:hover td {{
      background: #f7f3e8;
    }}

    tr.selected td {{
      background: #eaf1f7;
    }}

    .chart-panel {{
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr) auto;
    }}

    .view-note {{
      padding: 8px 16px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-size: 12px;
      background: #fbfaf7;
    }}

    .chart-frame {{
      min-height: 0;
      padding: 8px 16px 4px;
      overflow: hidden;
      position: relative;
    }}

    svg {{
      display: block;
      width: 100%;
      height: 100%;
      min-height: 0;
    }}

    .grid-line {{
      stroke: #e7e2d7;
      stroke-width: 1;
    }}

    .axis {{
      stroke: #b9b3a8;
      stroke-width: 1;
    }}

    .axis-label {{
      fill: var(--muted);
      font-size: 11px;
    }}

    .series-line {{
      fill: none;
      stroke-width: 2.5;
      stroke-linejoin: round;
      stroke-linecap: round;
    }}

    .series-point {{
      stroke: #fff;
      stroke-width: 1.5;
    }}

    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      padding: 0 16px 14px;
      min-height: 42px;
    }}

    .legend-item {{
      display: inline-flex;
      align-items: center;
      gap: 7px;
      max-width: 260px;
      font-size: 12px;
      color: var(--muted);
    }}

    .swatch {{
      width: 20px;
      height: 3px;
      border-radius: 3px;
      flex: 0 0 auto;
    }}

    .city-name {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .empty {{
      fill: var(--muted);
      font-size: 15px;
      text-anchor: middle;
    }}

    .classification-page {{
      grid-template-columns: minmax(0, 1fr);
    }}

    .housing-page {{
      grid-template-columns: minmax(280px, 340px) minmax(0, 1fr);
    }}

    .classification-panel,
    .housing-chart-panel {{
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr);
    }}

    .classification-note {{
      padding: 9px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfaf7;
      color: var(--muted);
      font-size: 12px;
    }}

    .classification-grid {{
      min-height: 0;
      overflow: auto;
      padding: 14px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
      gap: 12px;
      align-content: start;
    }}

    .classification-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
      display: grid;
      grid-template-rows: auto 220px auto;
      min-width: 0;
    }}

    .classification-card-head {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
      padding: 12px 12px 8px;
      border-bottom: 1px solid #ece8de;
    }}

    .classification-city {{
      font-size: 14px;
      font-weight: 760;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .classification-label {{
      flex: 0 1 auto;
      max-width: 52%;
      border-radius: 999px;
      padding: 4px 8px;
      color: #fff;
      font-size: 11px;
      font-weight: 760;
      line-height: 1.2;
      text-align: right;
    }}

    .label-positive {{
      background: var(--green);
    }}

    .label-negative {{
      background: var(--red);
    }}

    .label-stagnant {{
      background: #6f6a5f;
    }}

    .label-volatile {{
      background: var(--orange);
    }}

    .label-insufficient {{
      background: var(--muted);
    }}

    .mini-chart {{
      min-height: 0;
      padding: 8px 10px 4px;
    }}

    .mini-chart svg {{
      min-height: 0;
    }}

    .classification-meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(92px, 1fr));
      gap: 1px;
      background: var(--line);
      border-top: 1px solid var(--line);
      font-size: 12px;
    }}

    .meta-item {{
      background: #fbfaf7;
      padding: 8px 10px;
      min-width: 0;
    }}

    .meta-value {{
      font-weight: 760;
      white-space: nowrap;
    }}

    .meta-label {{
      color: var(--muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .classification-empty {{
      padding: 24px;
      color: var(--muted);
      font-size: 14px;
    }}

    .housing-controls-panel {{
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr);
    }}

    .housing-controls-panel,
    .housing-chart-panel {{
      min-height: 960px;
    }}

    .housing-controls {{
      display: grid;
      gap: 12px;
      padding: 14px;
      border-bottom: 1px solid var(--line);
      background: #fbfaf7;
    }}

    .housing-city-summary {{
      min-height: 0;
      overflow: auto;
      padding: 14px;
      display: grid;
      gap: 12px;
      align-content: start;
    }}

    .housing-selected-city {{
      font-size: 18px;
      font-weight: 760;
      line-height: 1.2;
    }}

    .housing-summary-note {{
      color: var(--muted);
      font-size: 13px;
    }}

    .housing-metrics {{
      display: grid;
      gap: 1px;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: var(--line);
    }}

    .housing-metric {{
      background: #fbfaf7;
      padding: 10px 12px;
    }}

    .housing-metric-value {{
      font-size: 17px;
      font-weight: 760;
      white-space: normal;
    }}

    .housing-metric-label {{
      color: var(--muted);
      font-size: 12px;
      margin-top: 2px;
    }}

    .housing-empty {{
      padding: 24px;
      color: var(--muted);
      font-size: 14px;
    }}

    .housing-chart-panel {{
      grid-template-rows: auto auto minmax(0, 1fr);
    }}

    .housing-dashboard {{
      min-height: 0;
      display: grid;
      grid-template-rows: minmax(170px, 0.9fr) minmax(190px, 1fr) minmax(190px, 0.95fr) minmax(170px, 0.85fr);
      overflow: visible;
    }}

    .housing-viz {{
      min-height: 0;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      border-bottom: 1px solid var(--line);
    }}

    .housing-viz-head {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 16px 0;
    }}

    .housing-viz-head h3 {{
      margin: 0;
      font-size: 13px;
      font-weight: 760;
      letter-spacing: 0;
    }}

    .housing-chart-frame {{
      min-height: 0;
      padding: 6px 16px 8px;
      overflow: hidden;
    }}

    .housing-ratio-grid {{
      min-height: 0;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      padding: 6px 16px 10px;
    }}

    .housing-ratio-card {{
      min-height: 0;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      border: 1px solid #ece8de;
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }}

    .housing-ratio-title {{
      padding: 7px 10px 0;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}

    .housing-ratio-card .housing-chart-frame {{
      padding: 4px 10px 8px;
    }}

    .housing-stats-legend {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      padding: 0 16px 8px;
      min-height: 25px;
    }}

    .housing-summary-wrap {{
      min-height: 0;
      overflow: auto;
    }}

    .housing-summary-table th,
    .housing-summary-table td {{
      font-size: 12px;
    }}

    .housing-summary-table td:first-child {{
      max-width: 90px;
    }}

    .housing-summary-table tr {{
      cursor: default;
    }}

    .opportunity-page {{
      grid-template-columns: minmax(430px, 640px) minmax(0, 1fr);
    }}

    .opportunity-panel,
    .opportunity-chart-panel {{
      display: grid;
      grid-template-rows: auto auto auto auto minmax(0, 1fr);
      min-height: 680px;
    }}

    .opportunity-note {{
      padding: 9px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfaf7;
      color: var(--muted);
      font-size: 12px;
    }}

    .opportunity-summary {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 1px;
      background: var(--line);
      border-bottom: 1px solid var(--line);
    }}

    .opportunity-controls {{
      display: grid;
      grid-template-columns: repeat(2, minmax(130px, 1fr));
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }}

    .opportunity-stat {{
      background: #fbfaf7;
      padding: 10px 12px;
      min-width: 0;
    }}

    .opportunity-stat-value {{
      font-size: 18px;
      font-weight: 760;
      white-space: nowrap;
    }}

    .opportunity-stat-label {{
      color: var(--muted);
      font-size: 12px;
      margin-top: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .signal-badge {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 3px 7px;
      color: #fff;
      font-size: 11px;
      font-weight: 760;
      white-space: nowrap;
    }}

    .signal-decreasing {{
      background: var(--green);
    }}

    .signal-stable {{
      background: var(--teal);
    }}

    .signal-rising {{
      background: var(--orange);
    }}

    .opportunity-table td:first-child {{
      max-width: 170px;
    }}

    .opportunity-chart-panel {{
      grid-template-rows: auto auto minmax(0, 1fr) auto;
    }}

    .investment-page {{
      grid-template-columns: minmax(520px, 0.95fr) minmax(0, 1.05fr);
    }}

    .investment-panel,
    .investment-chart-panel {{
      display: grid;
      grid-template-rows: auto auto auto minmax(0, 1fr);
      min-height: 780px;
    }}

    .investment-note {{
      padding: 9px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfaf7;
      color: var(--muted);
      font-size: 12px;
    }}

    .investment-summary {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 1px;
      background: var(--line);
      border-bottom: 1px solid var(--line);
    }}

    .investment-stat {{
      background: #fbfaf7;
      padding: 10px 12px;
      min-width: 0;
    }}

    .investment-stat-value {{
      font-size: 17px;
      font-weight: 760;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .investment-stat-label {{
      color: var(--muted);
      font-size: 12px;
      margin-top: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .investment-table th,
    .investment-table td {{
      font-size: 11px;
    }}

    .investment-table td:first-child {{
      max-width: 56px;
    }}

    .investment-table td:nth-child(2) {{
      max-width: 180px;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .investment-dashboard {{
      min-height: 0;
      display: grid;
      grid-template-rows: minmax(270px, 1fr) minmax(270px, 1fr);
      overflow: visible;
    }}

    .investment-viz {{
      min-height: 0;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      border-bottom: 1px solid var(--line);
    }}

    .investment-viz-head {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 16px 0;
    }}

    .investment-viz-head h3 {{
      margin: 0;
      font-size: 13px;
      font-weight: 760;
    }}

    .chart-tooltip {{
      position: absolute;
      z-index: 5;
      max-width: 260px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      box-shadow: var(--shadow);
      padding: 9px 10px;
      color: var(--ink);
      font-size: 12px;
      line-height: 1.35;
      pointer-events: none;
    }}

    .chart-tooltip[hidden] {{
      display: none;
    }}

    .tooltip-title {{
      font-weight: 760;
      margin-bottom: 4px;
    }}

    .tooltip-row {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      color: var(--muted);
    }}

    .tooltip-row b {{
      color: var(--ink);
      font-weight: 760;
    }}

    footer {{
      padding: 8px 24px 10px;
      color: var(--muted);
      font-size: 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    @media (max-width: 980px) {{
      body {{
        overflow: auto;
      }}

      .app {{
        height: auto;
        min-height: 100vh;
        min-height: 100dvh;
        overflow: visible;
      }}

      .toolbar {{
        grid-template-columns: 1fr 1fr;
      }}

      .page {{
        grid-template-columns: 1fr;
        overflow: visible;
      }}

      .rank-panel,
      .chart-panel {{
        min-height: 520px;
      }}

      .housing-controls-panel,
      .housing-chart-panel {{
        min-height: 420px;
      }}

      .housing-ratio-grid {{
        grid-template-columns: 1fr;
      }}

      .chart-frame {{
        min-height: 340px;
      }}

      .table-wrap {{
        max-height: 440px;
      }}
    }}

    @media (max-width: 620px) {{
      header,
      .tabs,
      .toolbar,
      .page,
      footer {{
        padding-left: 14px;
        padding-right: 14px;
      }}

      .toolbar {{
        grid-template-columns: 1fr;
      }}

      .segmented {{
        width: 100%;
      }}

      .title-row {{
        align-items: flex-start;
      }}

      .source {{
        white-space: normal;
      }}

      h1 {{
        font-size: 22px;
      }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <header>
      <div class="title-row">
        <h1>German City Population Growth</h1>
      <div class="source">BBSR INKAR 2025 | Municipalities | 2014-2023</div>
      </div>
    </header>

    <nav class="tabs" aria-label="Pages">
      <button id="populationTab" type="button" class="tab-button active" data-tab="population">Population Growth</button>
      <button id="classificationTab" type="button" class="tab-button" data-tab="classification">Growth Classification</button>
      <button id="opportunityTab" type="button" class="tab-button" data-tab="opportunity">Growth + Price/Rent Signals</button>
      <button id="investmentTab" type="button" class="tab-button" data-tab="investment">Investment Potential</button>
      <button id="housingTab" type="button" class="tab-button" data-tab="housing">Housing Price Trends</button>
    </nav>

    <section class="toolbar" aria-label="Dashboard controls">
      <label>
        Search
        <input id="search" type="search" autocomplete="off" placeholder="City name">
      </label>
      <label>
        Start
        <select id="startYear"></select>
      </label>
      <label>
        End
        <select id="endYear"></select>
      </label>
      <label>
        Sort
        <select id="sortMode">
          <option value="abs-desc">Absolute population growth</option>
          <option value="cagr-desc">CAGR</option>
          <option value="pct-desc">Percentage population growth</option>
          <option value="cagr-asc">Lowest CAGR</option>
          <option value="start-pop-desc">Start population</option>
          <option value="end-pop-desc">End population</option>
          <option value="median-price-growth-desc">Median housing price YoY</option>
          <option value="investment-score-desc">Investment score</option>
          <option value="demand-score-desc">Demand score</option>
          <option value="supply-score-desc">Supply constraint score</option>
          <option value="yield-score-desc">Gross rental yield</option>
          <option value="price-to-rent-asc">Price-to-rent ratio</option>
          <option value="absorption-desc">Absorption ratio</option>
          <option value="pipeline-asc">Pipeline rate</option>
          <option value="data-quality-desc">Data quality</option>
        </select>
      </label>
      <label>
        Population Size Filter
        <select id="populationBand">
          <option value="all">All sizes</option>
          <option value="small">Small &lt;10k</option>
          <option value="medium">Medium 10k-100k</option>
          <option value="large">Large 100k-1M</option>
          <option value="very-large">Very large &gt;1M</option>
          <option value="custom">Custom range</option>
        </select>
      </label>
      <label>
        Min pop.
        <input id="minPopulation" type="number" min="0" step="1000" inputmode="numeric" placeholder="No min">
      </label>
      <label>
        Max pop.
        <input id="maxPopulation" type="number" min="0" step="1000" inputmode="numeric" placeholder="No max">
      </label>
      <label>
        Rows
        <select id="rowLimit">
          <option value="25">Top 25</option>
          <option value="10">Top 10</option>
          <option value="50">Top 50</option>
          <option value="all">All</option>
        </select>
      </label>
      <label>
        Granularity
        <select id="granularityMode">
          <option value="best">Best available data</option>
          <option value="conservative">Conservative comparable mode</option>
        </select>
      </label>
      <label>
        View
        <span class="segmented" role="group" aria-label="Chart view">
          <button id="indexView" type="button" class="active" data-view="index">Indexed</button>
          <button id="absoluteView" type="button" data-view="absolute">Raw</button>
        </span>
      </label>
      <button id="reset" type="button" class="small-button">Reset</button>
    </section>

    <details class="definitions">
      <summary>Metric Definitions</summary>
      <div class="definitions-grid">
        <div><b>Absolute growth</b>: end value minus start value.</div>
        <div><b>Percentage growth</b>: absolute growth divided by start value.</div>
        <div><b>CAGR</b>: annualized growth rate across the selected years.</div>
        <div><b>Median housing price</b>: middle value across source records for a year.</div>
        <div><b>Mean housing price</b>: average value across source records for a year.</div>
        <div><b>Standard deviation</b>: spread of housing values across source records.</div>
        <div><b>Housing price YoY</b>: annualized median-price change across the selected years.</div>
        <div><b>Gross rental yield</b>: annual rent per m2 divided by purchase price per m2.</div>
        <div><b>Price-to-rent ratio</b>: purchase price per m2 divided by annual rent per m2.</div>
        <div><b>Absorption ratio</b>: population change divided by completed apartments.</div>
        <div><b>Pipeline rate</b>: building permits divided by completed apartments.</div>
        <div><b>Building permits per 1,000 residents</b>: supply pipeline intensity.</div>
        <div><b>Completed apartments per 1,000 residents</b>: recent new housing supply intensity.</div>
        <div><b>Investment score</b>: weighted, explainable score from demand, supply, yield, affordability, and data risk.</div>
        <div><b>Demand score</b>: population CAGR, absolute growth, and starting population base.</div>
        <div><b>Supply constraint score</b>: absorption pressure adjusted by pipeline rate.</div>
        <div><b>Yield score</b>: gross rental yield and price-to-rent reasonableness.</div>
        <div><b>Affordability score</b>: purchase-price discipline relative to rent and demand.</div>
        <div><b>Data quality / risk score</b>: completeness, granularity, and missing yield/supply risk.</div>
        <div><b>Coverage level / granularity</b>: whether observations are municipality, district, or fine-grained area records.</div>
        <div><b>Conservative comparable mode</b>: penalizes less comparable fine-grained and fallback records in rankings.</div>
        <div><b>Population bands</b>: small &lt;10k, medium 10k-100k, large 100k-1M, very large &gt;1M.</div>
        <div><b>Indexed mode</b>: sets each selected series to 100 in the first selected year.</div>
      </div>
    </details>

    <main id="populationPage" class="page population-page">
      <div id="populationActiveFilters" class="active-filters"></div>
      <section class="panel rank-panel">
        <div class="panel-head">
          <h2>Ranked Cities</h2>
          <span id="rowCount" class="count"></span>
        </div>
        <div class="stats">
          <div class="stat">
            <div id="fastestCity" class="stat-value"></div>
            <div class="stat-label">Fastest abs. change</div>
          </div>
          <div class="stat">
            <div id="medianGrowth" class="stat-value"></div>
            <div class="stat-label">Median start pop.</div>
          </div>
          <div class="stat">
            <div id="growingCount" class="stat-value"></div>
            <div class="stat-label">Growing cities</div>
          </div>
          <div class="stat">
            <div id="decliningCount" class="stat-value"></div>
            <div class="stat-label">Declining cities</div>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>City</th>
                <th>Start pop.</th>
                <th>End pop.</th>
                <th>Abs. change</th>
                <th>Growth %</th>
                <th>CAGR</th>
                <th>Price YoY</th>
                <th>Quality</th>
              </tr>
            </thead>
            <tbody id="rankBody"></tbody>
          </table>
        </div>
      </section>

      <section class="panel chart-panel">
        <div class="panel-head">
          <h2 id="chartTitle">Population Index</h2>
          <span id="periodLabel" class="count"></span>
        </div>
        <div id="viewNote" class="view-note"></div>
        <div class="chart-frame">
          <svg id="chart" role="img" aria-labelledby="chartTitle"></svg>
        </div>
        <div id="legend" class="legend"></div>
      </section>
    </main>

    <main id="classificationPage" class="page classification-page" hidden>
      <div id="classificationActiveFilters" class="active-filters"></div>
      <section class="panel classification-panel">
        <div class="panel-head">
          <h2>Growth Classification</h2>
          <span id="classificationPeriod" class="count"></span>
        </div>
        <div class="classification-note">
          Uses the selected cities and selected year window. Labels combine direction, trend shape, population-size context, and a data-quality badge. Curves use the shared Raw/Indexed view toggle.
        </div>
        <div id="classificationGrid" class="classification-grid"></div>
      </section>
    </main>

    <main id="opportunityPage" class="page opportunity-page" hidden>
      <div id="opportunityActiveFilters" class="active-filters"></div>
      <section class="panel opportunity-panel">
        <div class="panel-head">
          <h2>Growing Cities With Stable Prices</h2>
          <span id="opportunityCount" class="count"></span>
        </div>
        <div class="opportunity-note">
          Screens cities with rising population and stable or decreasing purchase-price or asking-rent signals over the selected years. The chart shows every city with the selected signal so the highlighted candidates stay in context.
        </div>
        <div class="opportunity-controls">
          <label>
            Signal metric
            <select id="opportunitySignalMetric">
              <option value="best">Best available price/rent signal</option>
              <option value="purchase">Purchase-price signal only</option>
              <option value="rent">Asking-rent signal only</option>
            </select>
          </label>
          <label>
            Min pop. CAGR %
            <input id="opportunityMinGrowth" type="number" step="0.1" value="0" inputmode="decimal">
          </label>
          <label>
            Max signal YoY %
            <input id="opportunityMaxPriceGrowth" type="number" step="0.1" value="1" inputmode="decimal">
          </label>
        </div>
        <div id="opportunitySummary" class="opportunity-summary"></div>
        <div class="table-wrap">
          <table class="opportunity-table">
            <thead>
              <tr>
                <th>City</th>
                <th>Signal</th>
                <th>Start pop.</th>
                <th>Abs. pop</th>
                <th>Pop CAGR</th>
                <th>Signal basis</th>
                <th>Start signal</th>
                <th>End signal</th>
                <th>Signal YoY</th>
                <th>Median rent</th>
                <th>Rent YoY</th>
                <th>Gross yield</th>
                <th>Price/rent</th>
                <th>Absorption</th>
                <th>Supply pressure</th>
                <th>Coverage</th>
                <th>Spread</th>
                <th>Quality</th>
              </tr>
            </thead>
            <tbody id="opportunityBody"></tbody>
          </table>
        </div>
      </section>

      <section class="panel opportunity-chart-panel">
        <div class="panel-head">
          <h2 id="opportunityChartTitle">Population Growth vs Housing Price YoY</h2>
          <span id="opportunityPeriod" class="count"></span>
        </div>
        <div class="view-note">
          Each point is a city. Higher is stronger population growth. Farther left is flatter or falling median housing prices. The shaded screening area is price YoY at or below +1% with positive population growth.
        </div>
        <div class="chart-frame">
          <svg id="opportunityChart" role="img" aria-labelledby="opportunityChartTitle"></svg>
          <div id="opportunityTooltip" class="chart-tooltip" hidden></div>
        </div>
        <div id="opportunityLegend" class="legend"></div>
      </section>
    </main>

    <main id="investmentPage" class="page investment-page" hidden>
      <div id="investmentActiveFilters" class="active-filters"></div>
      <section class="panel investment-panel">
        <div class="panel-head">
          <h2>Investment Potential</h2>
          <span id="investmentCount" class="count"></span>
        </div>
        <div class="investment-note">
          Ranks municipalities with an explainable score. Missing fundamentals are shown as unavailable and reduce score completeness; asking rent is never treated as purchase price.
        </div>
        <div id="investmentSummary" class="investment-summary"></div>
        <div class="table-wrap">
          <table class="investment-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Municipality</th>
                <th>Investment score</th>
                <th>Demand score</th>
                <th>Supply score</th>
                <th>Yield score</th>
                <th>Affordability score</th>
                <th>Risk/data score</th>
                <th>Completeness</th>
                <th>Start pop.</th>
                <th>Pop CAGR</th>
                <th>Abs. pop</th>
                <th>Gross yield</th>
                <th>Price/rent</th>
                <th>Median purchase</th>
                <th>Median rent</th>
                <th>Absorption</th>
                <th>Pipeline</th>
                <th>Coverage</th>
                <th>Data quality</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody id="investmentBody"></tbody>
          </table>
        </div>
      </section>

      <section class="panel investment-chart-panel">
        <div class="panel-head">
          <h2>Investment Diagnostics</h2>
          <span id="investmentPeriod" class="count"></span>
        </div>
        <div class="view-note">
          Charts render the top filtered municipalities to stay readable. Tooltips show the underlying metrics behind each point.
        </div>
        <div class="investment-dashboard">
          <section class="investment-viz">
            <div class="investment-viz-head">
              <h3>Yield vs Demand</h3>
              <span class="count">x: gross yield, y: population CAGR</span>
            </div>
            <div class="chart-frame">
              <svg id="investmentYieldDemandChart" role="img" aria-label="Gross rental yield versus population CAGR"></svg>
            </div>
          </section>
          <section class="investment-viz">
            <div class="investment-viz-head">
              <h3>Supply-Demand Pressure</h3>
              <span class="count">x: population CAGR, y: absorption ratio</span>
            </div>
            <div class="chart-frame">
              <svg id="investmentSupplyChart" role="img" aria-label="Population CAGR versus absorption ratio"></svg>
            </div>
          </section>
        </div>
      </section>
    </main>

    <main id="housingPage" class="page housing-page" hidden>
      <div id="housingActiveFilters" class="active-filters"></div>
      <section class="panel housing-controls-panel">
        <div class="panel-head">
          <h2>Housing Price Trends</h2>
          <span id="housingDataStatus" class="count"></span>
        </div>
        <div class="housing-controls">
          <label>
            City
            <select id="housingCity"></select>
          </label>
        </div>
        <div id="housingCitySummary" class="housing-city-summary"></div>
      </section>

      <section class="panel housing-chart-panel">
        <div class="panel-head">
          <h2 id="housingChartTitle">Housing Price Trends</h2>
          <span id="housingPeriod" class="count"></span>
        </div>
        <div id="housingNote" class="view-note"></div>
        <div class="housing-dashboard">
          <section class="housing-viz">
            <div class="housing-viz-head">
              <h3>Population Over Years</h3>
              <span id="housingPopulationLabel" class="count"></span>
            </div>
            <div class="housing-chart-frame">
              <svg id="housingPopulationChart" role="img" aria-label="Selected city population over years"></svg>
            </div>
          </section>
          <section class="housing-viz">
            <div class="housing-viz-head">
              <h3>Housing Price Statistics Over Years</h3>
              <span class="count">EUR/m2</span>
            </div>
            <div class="housing-chart-frame">
              <svg id="housingPriceChart" role="img" aria-label="Selected city housing price statistics over years"></svg>
            </div>
            <div id="housingStatsLegend" class="housing-stats-legend"></div>
          </section>
          <section class="housing-viz">
            <div class="housing-viz-head">
              <h3>Yield and Price-to-Rent Over Years</h3>
              <span class="count">computed only from overlapping purchase + rent years</span>
            </div>
            <div class="housing-ratio-grid">
              <div class="housing-ratio-card">
                <div class="housing-ratio-title">Gross rental yield</div>
                <div class="housing-chart-frame">
                  <svg id="housingYieldChart" role="img" aria-label="Selected city gross rental yield over years"></svg>
                </div>
              </div>
              <div class="housing-ratio-card">
                <div class="housing-ratio-title">Price-to-rent ratio</div>
                <div class="housing-chart-frame">
                  <svg id="housingPriceRentChart" role="img" aria-label="Selected city price-to-rent ratio over years"></svg>
                </div>
              </div>
            </div>
          </section>
          <div class="housing-summary-wrap">
            <table class="housing-summary-table">
              <thead>
                <tr>
                  <th>Year</th>
                  <th>Population</th>
                  <th>Pop YoY change</th>
                  <th>Pop YoY %</th>
                  <th>Purchase median</th>
                  <th>Asking rent</th>
                  <th>Gross yield</th>
                  <th>Price/rent</th>
                  <th>Purchase YoY</th>
                  <th>Rent YoY</th>
                </tr>
              </thead>
              <tbody id="housingSummaryBody"></tbody>
            </table>
          </div>
        </div>
      </section>
    </main>

    <footer>
      Source: BBSR INKAR 2025 population indicator xbev at municipality level. Values use INKAR's 2023 regional boundary.
    </footer>
  </div>

  <script id="population-data" type="application/json">{data_json}</script>
  <script>
    const payload = JSON.parse(document.getElementById("population-data").textContent);
    const observations = payload.observations;
    const housingPrices = payload.housing_prices || [];
    const marketIndicators = payload.market_indicators || [];
    const metadata = payload.metadata;
    const colors = ["#3168a6", "#3e7b4f", "#bc6c25", "#7057a3", "#207c7c", "#a64035", "#6f6a5f"];
    const stablePriceYoYThreshold = 1.0;
    const investmentWeights = {{
      demand: 0.30,
      supply: 0.25,
      yield: 0.20,
      affordability: 0.15,
      dataQuality: 0.10
    }};

    const byCity = new Map();
    const years = Array.from(new Set(observations.map(d => d.year))).sort((a, b) => a - b);
    observations.forEach(d => {{
      const key = populationPlaceKey(d);
      if (!byCity.has(key)) {{
        byCity.set(key, {{ key, city: d.city, city_id: d.city_id || "", series: [] }});
      }}
      byCity.get(key).series.push(d);
    }});
    byCity.forEach(entry => entry.series.sort((a, b) => a.year - b.year));

    const populationCityById = new Map();
    const populationCityByNameKey = new Map();
    byCity.forEach((entry, key) => {{
      if (entry.city_id) populationCityById.set(entry.city_id, key);
      const nameKey = cityKey(entry.city);
      if (!populationCityByNameKey.has(nameKey)) populationCityByNameKey.set(nameKey, key);
    }});

    const housingByCity = new Map();
    housingPrices.forEach(row => {{
      const key = housingPlaceKey(row);
      if (!housingByCity.has(key)) {{
        housingByCity.set(key, {{ key, city: row.city, city_id: row.city_id || "", areas: new Map() }});
      }}
      const cityAreas = housingByCity.get(key).areas;
      if (!cityAreas.has(row.area)) cityAreas.set(row.area, []);
      cityAreas.get(row.area).push(row);
    }});
    housingByCity.forEach(entry => {{
      entry.areas.forEach(series => series.sort((a, b) => a.year - b.year));
    }});

    const marketByCity = new Map();
    marketIndicators.forEach(row => {{
      const key = populationPlaceKey(row);
      if (!marketByCity.has(key)) {{
        marketByCity.set(key, {{ key, city: row.city, city_id: row.city_id || "", metrics: new Map() }});
      }}
      const entry = marketByCity.get(key);
      if (!entry.metrics.has(row.metric)) entry.metrics.set(row.metric, []);
      entry.metrics.get(row.metric).push(row);
    }});
    marketByCity.forEach(entry => {{
      entry.metrics.forEach(series => series.sort((a, b) => a.year - b.year));
    }});

    const state = {{
      startYear: metadata.default_start,
      endYear: metadata.default_end,
      view: "index",
      activeTab: "population",
      sortMode: "abs-desc",
      rowLimit: "25",
      populationBand: "all",
      minPopulation: "",
      maxPopulation: "",
      granularityMode: "best",
      opportunitySignalMetric: "best",
      opportunityMinGrowth: 0,
      opportunityMaxPriceGrowth: 1,
      housingCity: "",
      search: "",
      selected: new Set()
    }};

    const elements = {{
      populationTab: document.getElementById("populationTab"),
      classificationTab: document.getElementById("classificationTab"),
      opportunityTab: document.getElementById("opportunityTab"),
      investmentTab: document.getElementById("investmentTab"),
      housingTab: document.getElementById("housingTab"),
      populationPage: document.getElementById("populationPage"),
      classificationPage: document.getElementById("classificationPage"),
      opportunityPage: document.getElementById("opportunityPage"),
      investmentPage: document.getElementById("investmentPage"),
      housingPage: document.getElementById("housingPage"),
      search: document.getElementById("search"),
      startYear: document.getElementById("startYear"),
      endYear: document.getElementById("endYear"),
      sortMode: document.getElementById("sortMode"),
      populationBand: document.getElementById("populationBand"),
      minPopulation: document.getElementById("minPopulation"),
      maxPopulation: document.getElementById("maxPopulation"),
      granularityMode: document.getElementById("granularityMode"),
      rowLimit: document.getElementById("rowLimit"),
      indexView: document.getElementById("indexView"),
      absoluteView: document.getElementById("absoluteView"),
      reset: document.getElementById("reset"),
      rankBody: document.getElementById("rankBody"),
      rowCount: document.getElementById("rowCount"),
      fastestCity: document.getElementById("fastestCity"),
      medianGrowth: document.getElementById("medianGrowth"),
      growingCount: document.getElementById("growingCount"),
      decliningCount: document.getElementById("decliningCount"),
      chartTitle: document.getElementById("chartTitle"),
      viewNote: document.getElementById("viewNote"),
      periodLabel: document.getElementById("periodLabel"),
      chart: document.getElementById("chart"),
      legend: document.getElementById("legend"),
      classificationPeriod: document.getElementById("classificationPeriod"),
      classificationGrid: document.getElementById("classificationGrid"),
      populationActiveFilters: document.getElementById("populationActiveFilters"),
      classificationActiveFilters: document.getElementById("classificationActiveFilters"),
      opportunityActiveFilters: document.getElementById("opportunityActiveFilters"),
      opportunityCount: document.getElementById("opportunityCount"),
      opportunitySummary: document.getElementById("opportunitySummary"),
      opportunityBody: document.getElementById("opportunityBody"),
      opportunityChartTitle: document.getElementById("opportunityChartTitle"),
      opportunityPeriod: document.getElementById("opportunityPeriod"),
      opportunityChart: document.getElementById("opportunityChart"),
      opportunityLegend: document.getElementById("opportunityLegend"),
      opportunityTooltip: document.getElementById("opportunityTooltip"),
      opportunitySignalMetric: document.getElementById("opportunitySignalMetric"),
      opportunityMinGrowth: document.getElementById("opportunityMinGrowth"),
      opportunityMaxPriceGrowth: document.getElementById("opportunityMaxPriceGrowth"),
      investmentActiveFilters: document.getElementById("investmentActiveFilters"),
      investmentCount: document.getElementById("investmentCount"),
      investmentSummary: document.getElementById("investmentSummary"),
      investmentBody: document.getElementById("investmentBody"),
      investmentPeriod: document.getElementById("investmentPeriod"),
      investmentYieldDemandChart: document.getElementById("investmentYieldDemandChart"),
      investmentSupplyChart: document.getElementById("investmentSupplyChart"),
      housingActiveFilters: document.getElementById("housingActiveFilters"),
      housingDataStatus: document.getElementById("housingDataStatus"),
      housingCity: document.getElementById("housingCity"),
      housingCitySummary: document.getElementById("housingCitySummary"),
      housingChartTitle: document.getElementById("housingChartTitle"),
      housingPeriod: document.getElementById("housingPeriod"),
      housingNote: document.getElementById("housingNote"),
      housingPopulationLabel: document.getElementById("housingPopulationLabel"),
      housingPopulationChart: document.getElementById("housingPopulationChart"),
      housingPriceChart: document.getElementById("housingPriceChart"),
      housingYieldChart: document.getElementById("housingYieldChart"),
      housingPriceRentChart: document.getElementById("housingPriceRentChart"),
      housingStatsLegend: document.getElementById("housingStatsLegend"),
      housingSummaryBody: document.getElementById("housingSummaryBody")
    }};

    function init() {{
      years.forEach(year => {{
        elements.startYear.appendChild(new Option(year, year));
        elements.endYear.appendChild(new Option(year, year));
      }});
      elements.startYear.value = state.startYear;
      elements.endYear.value = state.endYear;
      initHousingControls();

      [elements.populationTab, elements.classificationTab, elements.opportunityTab, elements.investmentTab, elements.housingTab].forEach(button => {{
        button.addEventListener("click", () => {{
          state.activeTab = button.dataset.tab;
          render();
        }});
      }});

      elements.search.addEventListener("input", event => {{
        state.search = event.target.value.trim().toLowerCase();
        render();
      }});
      elements.startYear.addEventListener("change", event => {{
        state.startYear = Number(event.target.value);
        if (state.startYear >= state.endYear) {{
          state.endYear = Math.min(metadata.year_max, state.startYear + 1);
          elements.endYear.value = state.endYear;
        }}
        render();
      }});
      elements.endYear.addEventListener("change", event => {{
        state.endYear = Number(event.target.value);
        if (state.endYear <= state.startYear) {{
          state.startYear = Math.max(metadata.year_min, state.endYear - 1);
          elements.startYear.value = state.startYear;
        }}
        render();
      }});
      elements.sortMode.addEventListener("change", event => {{
        state.sortMode = event.target.value;
        state.selected.clear();
        render();
      }});
      elements.populationBand.addEventListener("change", event => {{
        state.populationBand = event.target.value;
        if (state.populationBand !== "custom") {{
          state.minPopulation = "";
          state.maxPopulation = "";
          elements.minPopulation.value = "";
          elements.maxPopulation.value = "";
        }}
        render();
      }});
      elements.minPopulation.addEventListener("input", event => {{
        state.minPopulation = event.target.value;
        state.populationBand = "custom";
        elements.populationBand.value = state.populationBand;
        render();
      }});
      elements.maxPopulation.addEventListener("input", event => {{
        state.maxPopulation = event.target.value;
        state.populationBand = "custom";
        elements.populationBand.value = state.populationBand;
        render();
      }});
      elements.rowLimit.addEventListener("change", event => {{
        state.rowLimit = event.target.value;
        render();
      }});
      elements.granularityMode.addEventListener("change", event => {{
        state.granularityMode = event.target.value;
        render();
      }});
      elements.opportunitySignalMetric.addEventListener("change", event => {{
        state.opportunitySignalMetric = event.target.value;
        render();
      }});
      elements.opportunityMinGrowth.addEventListener("input", event => {{
        state.opportunityMinGrowth = parseOptionalNumber(event.target.value) ?? 0;
        render();
      }});
      elements.opportunityMaxPriceGrowth.addEventListener("input", event => {{
        state.opportunityMaxPriceGrowth = parseOptionalNumber(event.target.value) ?? stablePriceYoYThreshold;
        render();
      }});
      elements.housingCity.addEventListener("change", event => {{
        state.housingCity = event.target.value;
        render();
      }});
      [elements.indexView, elements.absoluteView].forEach(button => {{
        button.addEventListener("click", () => {{
          state.view = button.dataset.view;
          elements.indexView.classList.toggle("active", state.view === "index");
          elements.absoluteView.classList.toggle("active", state.view === "absolute");
          render();
        }});
      }});
      elements.reset.addEventListener("click", () => {{
        state.startYear = metadata.default_start;
        state.endYear = metadata.default_end;
        state.search = "";
        state.view = "index";
        state.sortMode = "abs-desc";
        state.rowLimit = "25";
        state.populationBand = "all";
        state.minPopulation = "";
      state.maxPopulation = "";
      state.granularityMode = "best";
      state.opportunitySignalMetric = "best";
      state.opportunityMinGrowth = 0;
      state.opportunityMaxPriceGrowth = stablePriceYoYThreshold;
        state.selected.clear();
        elements.search.value = "";
        elements.startYear.value = state.startYear;
        elements.endYear.value = state.endYear;
        elements.sortMode.value = state.sortMode;
        elements.rowLimit.value = state.rowLimit;
        elements.populationBand.value = state.populationBand;
        elements.minPopulation.value = "";
      elements.maxPopulation.value = "";
      elements.granularityMode.value = state.granularityMode;
      elements.opportunitySignalMetric.value = state.opportunitySignalMetric;
      elements.opportunityMinGrowth.value = state.opportunityMinGrowth;
        elements.opportunityMaxPriceGrowth.value = state.opportunityMaxPriceGrowth;
        elements.indexView.classList.add("active");
        elements.absoluteView.classList.remove("active");
        render();
      }});

      render();
    }}

    function initHousingControls() {{
      syncHousingOptions();
    }}

    function render() {{
      const rankings = computeRankings();
      const validKeys = new Set(rankings.map(row => row.key));
      Array.from(state.selected).forEach(key => {{
        if (!validKeys.has(key)) state.selected.delete(key);
      }});
      if (state.selected.size === 0) {{
        rankings.slice(0, 5).forEach(row => state.selected.add(row.key));
      }}

      const filtered = rankings.filter(row => row.city.toLowerCase().includes(state.search));
      const visible = applyRowLimit(filtered);
      syncHousingOptions();
      renderTabs();
      renderActiveFilters(rankings);
      renderStats(rankings);
      renderTable(visible, filtered.length);
      if (state.activeTab === "classification") {{
        renderClassification(rankings);
      }} else if (state.activeTab === "opportunity") {{
        renderOpportunitySignals(rankings);
      }} else if (state.activeTab === "investment") {{
        renderInvestmentPotential(rankings);
      }} else if (state.activeTab === "housing") {{
        renderHousingPriceTrends();
      }} else {{
        renderChart(rankings);
      }}
    }}

    function renderTabs() {{
      const isPopulation = state.activeTab === "population";
      const isClassification = state.activeTab === "classification";
      const isOpportunity = state.activeTab === "opportunity";
      const isInvestment = state.activeTab === "investment";
      const isHousing = state.activeTab === "housing";
      elements.populationTab.classList.toggle("active", isPopulation);
      elements.classificationTab.classList.toggle("active", isClassification);
      elements.opportunityTab.classList.toggle("active", isOpportunity);
      elements.investmentTab.classList.toggle("active", isInvestment);
      elements.housingTab.classList.toggle("active", isHousing);
      elements.populationPage.hidden = !isPopulation;
      elements.classificationPage.hidden = !isClassification;
      elements.opportunityPage.hidden = !isOpportunity;
      elements.investmentPage.hidden = !isInvestment;
      elements.housingPage.hidden = !isHousing;
    }}

    function computeRankings() {{
      const rows = [];
      const expectedYears = state.endYear - state.startYear + 1;
      byCity.forEach(entry => {{
        const series = entry.series;
        const window = series.filter(d => d.year >= state.startYear && d.year <= state.endYear);
        if (window.length < 2) return;
        const first = window.find(d => d.year === state.startYear);
        const last = window.find(d => d.year === state.endYear);
        if (!first || !last) return;
        if (!passesPopulationFilter(first.value)) return;
        const yearsElapsed = last.year - first.year;
        if (yearsElapsed <= 0 || first.value <= 0 || last.value <= 0) return;
        const cagr = (Math.pow(last.value / first.value, 1 / yearsElapsed) - 1) * 100;
        const total = ((last.value - first.value) / first.value) * 100;
        const absChange = last.value - first.value;
        const latest = latestYoy(window);
        const medianPriceMetrics = medianHousingPriceMetrics(entry.key);
        rows.push({{
          key: entry.key,
          city: entry.city,
          city_id: entry.city_id,
          series: window,
          start: first.value,
          end: last.value,
          absChange,
          cagr,
          total,
          latest,
          medianPriceGrowth: medianPriceMetrics?.pctChange ?? null,
          medianPriceCagr: medianPriceMetrics?.cagr ?? null,
          medianPriceAnnualChange: medianPriceMetrics?.annualChange ?? null,
          medianPriceStart: medianPriceMetrics?.start ?? null,
          medianPriceEnd: medianPriceMetrics?.end ?? null,
          medianPriceQuality: medianPriceMetrics?.quality ?? null,
          sizeBand: populationSizeBand(first.value),
          quality: dataQuality(window.length, expectedYears)
        }});
      }});
      rows.sort(compareRows);
      return rows;
    }}

    function compareRows(a, b) {{
      if (state.sortMode === "cagr-asc") return a.cagr - b.cagr || a.total - b.total || a.city.localeCompare(b.city);
      if (state.sortMode === "pct-desc") return b.total - a.total || b.absChange - a.absChange || a.city.localeCompare(b.city);
      if (state.sortMode === "start-pop-desc") return b.start - a.start || b.absChange - a.absChange || a.city.localeCompare(b.city);
      if (state.sortMode === "end-pop-desc") return b.end - a.end || b.absChange - a.absChange || a.city.localeCompare(b.city);
      if (state.sortMode === "median-price-growth-desc") return nullableDesc(a.medianPriceCagr, b.medianPriceCagr) || b.absChange - a.absChange || a.city.localeCompare(b.city);
      if (state.sortMode === "cagr-desc") return b.cagr - a.cagr || b.absChange - a.absChange || a.city.localeCompare(b.city);
      return b.absChange - a.absChange || b.cagr - a.cagr || a.city.localeCompare(b.city);
    }}

    function nullableDesc(a, b) {{
      if (a == null && b == null) return 0;
      if (a == null) return 1;
      if (b == null) return -1;
      return b - a;
    }}

    function nullableAsc(a, b) {{
      if (a == null && b == null) return 0;
      if (a == null) return 1;
      if (b == null) return -1;
      return a - b;
    }}

    function applyRowLimit(rows) {{
      if (state.rowLimit === "all") return rows;
      return rows.slice(0, Number(state.rowLimit));
    }}

    function syncHousingOptions() {{
      const cities = Array.from(housingByCity.values())
        .filter(entry => populationKeyForHousingEntry(entry))
        .filter(entry => housingEntryPassesPopulationFilter(entry))
        .sort((a, b) => a.city.localeCompare(b.city));
      const previous = state.housingCity;
      elements.housingCity.textContent = "";

      if (!cities.length) {{
        elements.housingCity.appendChild(new Option("No city matches the active filters", ""));
        elements.housingCity.disabled = true;
        state.housingCity = "";
        return;
      }}

      cities.forEach(entry => elements.housingCity.appendChild(new Option(entry.city, entry.key)));
      elements.housingCity.disabled = false;
      state.housingCity = cities.some(entry => entry.key === previous) ? previous : cities[0].key;
      elements.housingCity.value = state.housingCity;
    }}

    function renderActiveFilters(rankings) {{
      const selectedLabel = selectedItemsLabel(rankings);
      const common = [
        ["Start year", state.startYear],
        ["End year", state.endYear],
        ["Population filter", populationFilterLabel()],
        ["Trend view", state.view === "index" ? "Indexed values" : "Raw values"],
        ["Granularity", granularityModeLabel()]
      ];
      elements.populationActiveFilters.innerHTML = activeFilterMarkup([
        ...common,
        ["Sort", sortModeLabel()],
        ["Selected cities", selectedLabel]
      ]);
      elements.classificationActiveFilters.innerHTML = activeFilterMarkup([
        ...common,
        ["Selected cities", selectedLabel]
      ]);
      elements.opportunityActiveFilters.innerHTML = activeFilterMarkup([
        ...common,
        ["Signal metric", opportunitySignalMetricLabel()],
        ["Screen", `Population CAGR >= ${{signedPercent(state.opportunityMinGrowth)}} and signal YoY <= ${{signedPercent(state.opportunityMaxPriceGrowth)}}`],
        ["Chart", "All cities with selected signal; matching candidates highlighted"]
      ]);
      elements.investmentActiveFilters.innerHTML = activeFilterMarkup([
        ...common,
        ["Sort", sortModeLabel()],
        ["Score", "Demand, supply, yield, affordability, data risk"]
      ]);
      elements.housingActiveFilters.innerHTML = activeFilterMarkup([
        ...common,
        ["Selected city", housingCityLabel() || "None"],
        ["Housing metrics", "Purchase, rent, yield, price-to-rent"]
      ]);
    }}

    function activeFilterMarkup(filters) {{
      const chips = filters.map(([label, value]) =>
        `<span class="filter-chip"><b>${{escapeHtml(label)}}:</b>&nbsp;${{escapeHtml(value)}}</span>`
      ).join("");
      return `<span class="filter-title">Active Filters</span>${{chips}}`;
    }}

    function selectedItemsLabel(rankings) {{
      const selectedRows = rankings.filter(row => state.selected.has(row.key));
      if (!selectedRows.length) return "None";
      const names = selectedRows.slice(0, 3).map(row => row.city);
      return selectedRows.length > 3
        ? `${{names.join(", ")}} + ${{selectedRows.length - 3}} more`
        : names.join(", ");
    }}

    function sortModeLabel() {{
      const labels = {{
        "abs-desc": "Absolute population growth",
        "cagr-desc": "CAGR",
        "pct-desc": "Percentage population growth",
        "cagr-asc": "Lowest CAGR",
        "start-pop-desc": "Start population",
        "end-pop-desc": "End population",
        "median-price-growth-desc": "Median housing price YoY",
        "investment-score-desc": "Investment score",
        "demand-score-desc": "Demand score",
        "supply-score-desc": "Supply constraint score",
        "yield-score-desc": "Gross rental yield",
        "price-to-rent-asc": "Price-to-rent ratio",
        "absorption-desc": "Absorption ratio",
        "pipeline-asc": "Pipeline rate",
        "data-quality-desc": "Data quality"
      }};
      return labels[state.sortMode] || state.sortMode;
    }}

    function opportunitySignalMetricLabel() {{
      const labels = {{
        best: "Best available price/rent signal",
        purchase: "Purchase-price signal only",
        rent: "Asking-rent signal only"
      }};
      return labels[state.opportunitySignalMetric] || labels.best;
    }}

    function opportunitySignalAxisLabel() {{
      const labels = {{
        best: "Price/rent signal",
        purchase: "Purchase-price signal",
        rent: "Asking-rent signal"
      }};
      return labels[state.opportunitySignalMetric] || labels.best;
    }}

    function granularityModeLabel() {{
      return state.granularityMode === "conservative"
        ? "Conservative comparable mode"
        : "Best available data";
    }}

    function housingEntryPassesPopulationFilter(entry) {{
      const populationKey = populationKeyForHousingEntry(entry);
      const startPopulation = startPopulationForPopulationKey(populationKey);
      return passesPopulationFilter(startPopulation);
    }}

    function startPopulationForPopulationKey(key) {{
      if (!key || !byCity.has(key)) return null;
      return byCity.get(key).series.find(d => d.year === state.startYear)?.value ?? null;
    }}

    function passesPopulationFilter(value) {{
      if (value == null || Number.isNaN(value)) return false;
      if (state.populationBand === "custom") {{
        const min = parseOptionalNumber(state.minPopulation);
        const max = parseOptionalNumber(state.maxPopulation);
        if (min != null && value < min) return false;
        if (max != null && value > max) return false;
        return true;
      }}
      if (state.populationBand === "all") return true;
      return populationSizeBand(value) === state.populationBand;
    }}

    function populationFilterLabel() {{
      if (state.populationBand === "custom") {{
        const min = parseOptionalNumber(state.minPopulation);
        const max = parseOptionalNumber(state.maxPopulation);
        const minLabel = min == null ? "no min" : number(min);
        const maxLabel = max == null ? "no max" : number(max);
        return `Custom range: ${{minLabel}} to ${{maxLabel}} start-year population`;
      }}
      if (state.populationBand === "all") return "All start-year populations";
      return `${{populationSizeBandLabel(state.populationBand)}} start-year population`;
    }}

    function populationSizeBand(value) {{
      if (value < 10000) return "small";
      if (value < 100000) return "medium";
      if (value < 1000000) return "large";
      return "very-large";
    }}

    function populationSizeBandLabel(band) {{
      const labels = {{
        small: "Small",
        medium: "Medium",
        large: "Large",
        "very-large": "Very large"
      }};
      return labels[band] || "Custom";
    }}

    function housingEntryForPopulationKey(populationKey) {{
      if (!populationKey) return null;
      if (housingByCity.has(populationKey)) return housingByCity.get(populationKey);
      return Array.from(housingByCity.values()).find(entry => populationKeyForHousingEntry(entry) === populationKey) || null;
    }}

    function medianHousingPriceMetrics(populationKey) {{
      const entry = housingEntryForPopulationKey(populationKey);
      if (!entry) return null;
      const stats = aggregateHousingStatsByYearForEntry(entry);
      const start = stats.get(state.startYear)?.purchaseMedian ?? null;
      const end = stats.get(state.endYear)?.purchaseMedian ?? null;
      const metrics = growthMetrics(start, end, state.endYear - state.startYear);
      if (!metrics.valid) return null;
      const expectedYears = state.endYear - state.startYear + 1;
      const availableYears = Array.from(stats.values()).filter(row => row.purchaseRecordCount > 0).length;
      const maxRecordCount = Math.max(0, ...Array.from(stats.values()).map(row => row.purchaseRecordCount));
      return {{
        ...metrics,
        start,
        end,
        annualChange: metrics.absChange / Math.max(1, state.endYear - state.startYear),
        quality: dataQuality(availableYears, expectedYears, maxRecordCount)
      }};
    }}

    function growthMetrics(startValue, endValue, yearsElapsed) {{
      const absChange = startValue != null && endValue != null ? endValue - startValue : null;
      if (startValue == null || endValue == null || yearsElapsed <= 0 || startValue <= 0 || endValue <= 0) {{
        return {{ valid: false, absChange, pctChange: null, cagr: null }};
      }}
      return {{
        valid: true,
        absChange,
        pctChange: ((endValue - startValue) / startValue) * 100,
        cagr: (Math.pow(endValue / startValue, 1 / yearsElapsed) - 1) * 100
      }};
    }}

    function dataQuality(validYears, expectedYears, recordCount = Infinity) {{
      if (validYears < 2 || expectedYears <= 0) {{
        return {{ label: "Insufficient", className: "quality-insufficient" }};
      }}
      const completeness = validYears / expectedYears;
      if (completeness >= 0.9 && recordCount >= 5) {{
        return {{ label: "High", className: "quality-high" }};
      }}
      if (completeness >= 0.6 && recordCount >= 1) {{
        return {{ label: "Medium", className: "quality-medium" }};
      }}
      return {{ label: "Low", className: "quality-low" }};
    }}

    function combinedQuality(...qualities) {{
      const labels = qualities.filter(Boolean).map(item => item.label);
      if (!labels.length || labels.includes("Insufficient")) {{
        return {{ label: "Insufficient", className: "quality-insufficient" }};
      }}
      if (labels.includes("Low")) return {{ label: "Low", className: "quality-low" }};
      if (labels.includes("Medium")) return {{ label: "Medium", className: "quality-medium" }};
      return {{ label: "High", className: "quality-high" }};
    }}

    function qualityBadge(quality) {{
      const badge = quality || {{ label: "Insufficient", className: "quality-insufficient" }};
      return `<span class="badge ${{badge.className}}">${{escapeHtml(badge.label)}}</span>`;
    }}

    function parseOptionalNumber(value) {{
      if (value === "" || value == null) return null;
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    }}

    function latestYoy(series) {{
      if (series.length < 2) return null;
      const previous = series[series.length - 2];
      const current = series[series.length - 1];
      if (previous.value <= 0) return null;
      const gap = current.year - previous.year;
      if (gap <= 0) return null;
      return (Math.pow(current.value / previous.value, 1 / gap) - 1) * 100;
    }}

    function renderStats(rankings) {{
      const fastest = rankings.slice().sort((a, b) => b.absChange - a.absChange)[0];
      const startValues = rankings.map(row => row.start).sort((a, b) => a - b);
      elements.fastestCity.textContent = fastest ? signedNumber(fastest.absChange) : "";
      elements.fastestCity.title = fastest ? fastest.city : "";
      elements.medianGrowth.textContent = startValues.length ? number(median(startValues)) : "";
      elements.growingCount.textContent = rankings.filter(row => row.cagr > 0).length.toLocaleString();
      elements.decliningCount.textContent = rankings.filter(row => row.cagr < 0).length.toLocaleString();
      elements.periodLabel.textContent = `${{state.startYear}}-${{state.endYear}}`;
    }}

    function renderTable(rows, filteredCount) {{
      elements.rankBody.textContent = "";
      elements.rowCount.textContent = `${{rows.length.toLocaleString()}} of ${{filteredCount.toLocaleString()}} cities`;
      const fragment = document.createDocumentFragment();
      rows.forEach(row => {{
        const tr = document.createElement("tr");
        tr.className = state.selected.has(row.key) ? "selected" : "";
        tr.innerHTML = `
          <td title="${{escapeAttribute(row.city)}}">${{escapeHtml(row.city)}}</td>
          <td>${{number(row.start)}}</td>
          <td>${{number(row.end)}}</td>
          <td>${{signedNumber(row.absChange)}}</td>
          <td>${{signedPercent(row.total)}}</td>
          <td>${{signedPercent(row.cagr)}}</td>
          <td title="${{escapeAttribute(priceYoYTitle(row))}}">${{formatPriceYoY(row)}}</td>
          <td>${{qualityBadge(row.quality)}}</td>
        `;
        tr.addEventListener("click", () => {{
          if (state.selected.has(row.key)) {{
            state.selected.delete(row.key);
          }} else {{
            if (state.selected.size >= 7) {{
              state.selected.delete(Array.from(state.selected)[0]);
            }}
            state.selected.add(row.key);
          }}
          render();
        }});
        fragment.appendChild(tr);
      }});
      elements.rankBody.appendChild(fragment);
    }}

    function renderChart(rankings) {{
      const selectedRows = rankings.filter(row => state.selected.has(row.key)).slice(0, 7);
      elements.chartTitle.textContent = state.view === "index" ? "Population Index" : "Population";
      elements.viewNote.textContent = state.view === "index"
        ? "Index view sets each selected city to 100 in the chosen start year, so the lines show relative growth."
        : "Population view plots the actual resident count, so larger cities dominate the vertical scale.";
      const svg = elements.chart;
      const frame = svg.parentElement;
      const frameRect = frame.getBoundingClientRect();
      const width = Math.max(360, Math.floor(frameRect.width || svg.clientWidth || 720));
      const height = Math.max(280, Math.floor(frameRect.height || svg.clientHeight || 430));
      const margin = {{ top: 24, right: 28, bottom: 38, left: state.view === "index" ? 54 : 78 }};
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      svg.setAttribute("width", width);
      svg.setAttribute("height", height);
      svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
      svg.textContent = "";

      if (!selectedRows.length) {{
        svg.appendChild(text(width / 2, height / 2, "Select a city from the table", "empty"));
        renderLegend([]);
        return;
      }}

      const points = selectedRows.flatMap(row => {{
        const base = row.series[0].value;
        return row.series.map(d => ({{
          city: row.city,
          year: d.year,
          value: state.view === "index" ? (d.value / base) * 100 : d.value
        }}));
      }});

      const xMin = state.startYear;
      const xMax = state.endYear;
      const yExtent = extent(points.map(d => d.value));
      const yPad = (yExtent[1] - yExtent[0]) * 0.08 || 1;
      const yMin = Math.max(0, yExtent[0] - yPad);
      const yMax = yExtent[1] + yPad;

      const x = year => margin.left + ((year - xMin) / (xMax - xMin || 1)) * plotWidth;
      const y = value => margin.top + (1 - ((value - yMin) / (yMax - yMin || 1))) * plotHeight;

      const yTicks = ticks(yMin, yMax, 5);
      yTicks.forEach(tick => {{
        svg.appendChild(line(margin.left, y(tick), width - margin.right, y(tick), "grid-line"));
        const label = state.view === "index" ? tick.toFixed(0) : compact(tick);
        svg.appendChild(text(margin.left - 10, y(tick) + 4, label, "axis-label", "end"));
      }});

      const xTicks = years.filter(year => year >= xMin && year <= xMax && (year === xMin || year === xMax || year % 2 === 0));
      xTicks.forEach(tick => {{
        svg.appendChild(text(x(tick), height - margin.bottom + 24, String(tick), "axis-label", "middle"));
      }});

      svg.appendChild(line(margin.left, margin.top, margin.left, height - margin.bottom, "axis"));
      svg.appendChild(line(margin.left, height - margin.bottom, width - margin.right, height - margin.bottom, "axis"));
      svg.appendChild(text(margin.left, margin.top - 8, state.view === "index" ? "Index, start year = 100" : "Population", "axis-label"));
      svg.appendChild(text(width - margin.right, height - 6, "Year", "axis-label", "end"));

      selectedRows.forEach((row, index) => {{
        const base = row.series[0].value;
        const chartPoints = row.series.map(d => [
          x(d.year),
          y(state.view === "index" ? (d.value / base) * 100 : d.value)
        ]);
        svg.appendChild(path(chartPoints, colors[index % colors.length]));
        row.series.forEach(d => {{
          const plotted = state.view === "index" ? (d.value / base) * 100 : d.value;
          const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
          circle.setAttribute("cx", x(d.year));
          circle.setAttribute("cy", y(plotted));
          circle.setAttribute("r", "3.5");
          circle.setAttribute("fill", colors[index % colors.length]);
          circle.setAttribute("class", "series-point");
          circle.appendChild(document.createElementNS("http://www.w3.org/2000/svg", "title")).textContent =
            `${{row.city}}\\n${{d.year}}: ${{number(d.value)}} people`;
          svg.appendChild(circle);
        }});
      }});

      renderLegend(selectedRows);
    }}

    function renderOpportunitySignals(rankings) {{
      const allSignalRows = opportunitySignalRows(rankings);
      const filtered = allSignalRows.filter(row => row.city.toLowerCase().includes(state.search));
      const matching = filtered.filter(row => row.matchesOpportunity);
      const visible = applyRowLimit(matching);
      elements.opportunityChartTitle.textContent = `Population Growth vs ${{opportunitySignalAxisLabel()}} YoY`;
      elements.opportunityPeriod.textContent = `${{state.startYear}}-${{state.endYear}}`;
      renderOpportunitySummary(matching, filtered);
      renderOpportunityTable(visible, matching.length);
      renderOpportunityScatter(elements.opportunityChart, filtered);
      renderOpportunityLegend();
      elements.opportunityCount.textContent = `${{matching.length.toLocaleString()}} matching of ${{filtered.length.toLocaleString()}} charted`;
    }}

    function opportunitySignalRows(rankings) {{
      return rankings
        .filter(row => row.cagr >= state.opportunityMinGrowth)
        .map(row => {{
          const housingSignals = housingSignalsForPopulationKey(row.key);
          const signal = opportunitySignalForRow(row, housingSignals);
          if (!signal) return null;
          const supply = computeSupplyDemandMetrics(row);
          const matchesOpportunity = signal.cagr <= state.opportunityMaxPriceGrowth;
          return {{
            ...row,
            signalBasis: signal.basis,
            signalLabel: signal.label,
            signalStart: signal.start,
            signalEnd: signal.end,
            signalGrowth: signal.growth,
            signalCagr: signal.cagr,
            signalAnnualChange: signal.annualChange,
            signalQuality: signal.quality,
            matchesOpportunity,
            medianAskingRent: housingSignals.endAskingRent,
            rentGrowthPct: housingSignals.rentGrowth?.cagr ?? null,
            grossRentalYieldPct: housingSignals.grossRentalYieldPct,
            priceToRentRatio: housingSignals.priceToRentRatio,
            absorptionRatioDisplay: supply.absorptionRatioDisplay,
            absorptionLabel: supply.absorptionLabel,
            coverageLevel: summarizeDistinct([housingSignals.coverageLevel, supply.coverageLevel].filter(Boolean)),
            opportunitySignal: signal.cagr < 0 ? `Growth + decreasing ${{signal.label}}` : matchesOpportunity ? `Growth + stable ${{signal.label}}` : `Growth + rising ${{signal.label}}`,
            opportunityClass: signal.cagr < 0 ? "signal-decreasing" : matchesOpportunity ? "signal-stable" : "signal-rising",
            opportunitySpread: row.cagr - signal.cagr,
            opportunityQuality: combinedQuality(row.quality, signal.quality, housingSignals.grossRentalYieldPct == null ? {{ label: "Medium", className: "quality-medium" }} : null)
          }};
        }})
        .filter(Boolean)
        .sort((a, b) =>
          Number(b.matchesOpportunity) - Number(a.matchesOpportunity) ||
          b.opportunitySpread - a.opportunitySpread ||
          b.absChange - a.absChange ||
          a.city.localeCompare(b.city)
        );
    }}

    function opportunitySignalForRow(row, housingSignals) {{
      const purchaseSignal = row.medianPriceCagr == null ? null : {{
        basis: "Purchase price",
        label: "purchase price",
        start: row.medianPriceStart,
        end: row.medianPriceEnd,
        growth: row.medianPriceGrowth,
        cagr: row.medianPriceCagr,
        annualChange: row.medianPriceAnnualChange,
        quality: row.medianPriceQuality
      }};
      const rentSignal = housingSignals.rentGrowth?.valid ? {{
        basis: "Asking rent",
        label: "asking rent",
        start: housingSignals.startAskingRent,
        end: housingSignals.endAskingRent,
        growth: housingSignals.rentGrowth.pctChange,
        cagr: housingSignals.rentGrowth.cagr,
        annualChange: housingSignals.rentGrowth.absChange / Math.max(1, state.endYear - state.startYear),
        quality: housingSignals.rentQuality
      }} : null;

      if (state.opportunitySignalMetric === "purchase") return purchaseSignal;
      if (state.opportunitySignalMetric === "rent") return rentSignal;
      return purchaseSignal || rentSignal;
    }}

    function renderOpportunitySummary(matchingRows, chartRows) {{
      const decreasing = matchingRows.filter(row => row.signalCagr < 0).length;
      const stable = matchingRows.length - decreasing;
      const charted = chartRows.length;
      const aboveThreshold = chartRows.filter(row => !row.matchesOpportunity).length;
      const best = matchingRows[0];
      const medianSpreadValues = matchingRows.map(row => row.opportunitySpread).sort((a, b) => a - b);
      const signalLabel = opportunitySignalAxisLabel().toLowerCase();
      elements.opportunitySummary.innerHTML = `
        <div class="opportunity-stat">
          <div class="opportunity-stat-value">${{matchingRows.length.toLocaleString()}}</div>
          <div class="opportunity-stat-label">Matching cities</div>
        </div>
        <div class="opportunity-stat">
          <div class="opportunity-stat-value">${{charted.toLocaleString()}}</div>
          <div class="opportunity-stat-label">Charted cities with ${{escapeHtml(signalLabel)}}</div>
        </div>
        <div class="opportunity-stat">
          <div class="opportunity-stat-value">${{aboveThreshold.toLocaleString()}}</div>
          <div class="opportunity-stat-label">Above signal threshold</div>
        </div>
        <div class="opportunity-stat">
          <div class="opportunity-stat-value" title="${{best ? escapeAttribute(best.city) : ""}}">${{medianSpreadValues.length ? signedPercent(median(medianSpreadValues)) : "--"}}</div>
          <div class="opportunity-stat-label">Median growth-signal spread</div>
        </div>
      `;
    }}

    function renderOpportunityTable(rows, filteredCount) {{
      elements.opportunityBody.textContent = "";
      if (!rows.length) {{
        elements.opportunityBody.innerHTML = `<tr><td colspan="18">No cities match positive population growth with stable or decreasing ${{escapeHtml(opportunitySignalAxisLabel().toLowerCase())}} for the active filters. The chart may still show cities above the signal threshold.</td></tr>`;
        return;
      }}
      const fragment = document.createDocumentFragment();
      rows.forEach(row => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td title="${{escapeAttribute(row.city)}}">${{escapeHtml(row.city)}}</td>
          <td><span class="signal-badge ${{row.opportunityClass}}">${{escapeHtml(row.opportunitySignal)}}</span></td>
          <td>${{number(row.start)}}</td>
          <td>${{signedNumber(row.absChange)}}</td>
          <td>${{signedPercent(row.cagr)}}</td>
          <td>${{escapeHtml(row.signalBasis)}}</td>
          <td>${{row.signalStart == null ? "--" : money(row.signalStart)}}</td>
          <td>${{row.signalEnd == null ? "--" : money(row.signalEnd)}}</td>
          <td title="${{escapeAttribute(signalYoYTitle(row))}}">${{formatSignalYoY(row)}}</td>
          <td>${{row.medianAskingRent == null ? "Unavailable" : money(row.medianAskingRent)}}</td>
          <td>${{row.rentGrowthPct == null ? "Unavailable" : signedPercent(row.rentGrowthPct)}}</td>
          <td>${{row.grossRentalYieldPct == null ? "Unavailable" : signedPercent(row.grossRentalYieldPct).replace("+", "")}}</td>
          <td>${{row.priceToRentRatio == null ? "Unavailable" : numberDecimal(row.priceToRentRatio, 1)}}</td>
          <td title="${{escapeAttribute(row.absorptionLabel)}}">${{row.absorptionRatioDisplay}}</td>
          <td>${{escapeHtml(row.absorptionLabel)}}</td>
          <td>${{escapeHtml(row.coverageLevel || "Unavailable")}}</td>
          <td>${{signedPercent(row.opportunitySpread)}}</td>
          <td>${{qualityBadge(row.opportunityQuality)}}</td>
        `;
        tr.addEventListener("click", () => {{
          const housingEntry = housingEntryForPopulationKey(row.key);
          if (housingEntry) {{
            state.housingCity = housingEntry.key;
            state.activeTab = "housing";
            render();
          }}
        }});
        fragment.appendChild(tr);
      }});
      elements.opportunityBody.appendChild(fragment);
      elements.opportunityCount.textContent = `${{rows.length.toLocaleString()}} of ${{filteredCount.toLocaleString()}} matching candidates`;
    }}

    function renderOpportunityScatter(svg, rows) {{
      hideOpportunityTooltip();
      if (!rows.length) {{
        drawEmptySvg(svg, "No matching cities for the active filters");
        return;
      }}
      const frame = svg.parentElement;
      const frameRect = frame.getBoundingClientRect();
      const width = Math.max(520, Math.floor(frameRect.width || svg.clientWidth || 820));
      const height = Math.max(360, Math.floor(frameRect.height || svg.clientHeight || 520));
      const margin = {{ top: 28, right: 28, bottom: 44, left: 72 }};
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      const xValues = rows.map(row => row.signalCagr);
      const yValues = rows.map(row => row.cagr);
      const xExtent = extent([...xValues, -1, 0, state.opportunityMaxPriceGrowth]);
      const yExtent = extent([...yValues, 0]);
      const xPad = (xExtent[1] - xExtent[0]) * 0.12 || 1;
      const yPad = (yExtent[1] - yExtent[0]) * 0.12 || 1;
      const xMin = xExtent[0] - xPad;
      const xMax = Math.max(state.opportunityMaxPriceGrowth + 0.4, xExtent[1] + xPad);
      const yMin = Math.min(0, yExtent[0] - yPad);
      const yMax = yExtent[1] + yPad;
      const x = value => margin.left + ((value - xMin) / (xMax - xMin || 1)) * plotWidth;
      const y = value => margin.top + (1 - ((value - yMin) / (yMax - yMin || 1))) * plotHeight;

      svg.setAttribute("width", width);
      svg.setAttribute("height", height);
      svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
      svg.textContent = "";

      const target = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      target.setAttribute("x", x(xMin));
      target.setAttribute("y", y(yMax));
      target.setAttribute("width", Math.max(0, x(state.opportunityMaxPriceGrowth) - x(xMin)));
      target.setAttribute("height", Math.max(0, y(state.opportunityMinGrowth) - y(yMax)));
      target.setAttribute("fill", "rgba(62, 123, 79, 0.08)");
      svg.appendChild(target);

      ticks(xMin, xMax, 6).forEach(tick => {{
        svg.appendChild(line(x(tick), margin.top, x(tick), height - margin.bottom, "grid-line"));
        svg.appendChild(text(x(tick), height - margin.bottom + 24, signedPercent(tick), "axis-label", "middle"));
      }});
      ticks(yMin, yMax, 5).forEach(tick => {{
        svg.appendChild(line(margin.left, y(tick), width - margin.right, y(tick), "grid-line"));
        svg.appendChild(text(margin.left - 10, y(tick) + 4, signedPercent(tick), "axis-label", "end"));
      }});

      svg.appendChild(line(x(0), margin.top, x(0), height - margin.bottom, "axis"));
      svg.appendChild(line(x(state.opportunityMaxPriceGrowth), margin.top, x(state.opportunityMaxPriceGrowth), height - margin.bottom, "axis"));
      svg.appendChild(line(margin.left, y(state.opportunityMinGrowth), width - margin.right, y(state.opportunityMinGrowth), "axis"));
      svg.appendChild(text(margin.left, margin.top - 8, "Population CAGR", "axis-label"));
      svg.appendChild(text(width - margin.right, height - 8, `${{opportunitySignalAxisLabel()}} YoY`, "axis-label", "end"));
      svg.appendChild(text(x(state.opportunityMaxPriceGrowth) + 4, margin.top + 12, `${{signedPercent(state.opportunityMaxPriceGrowth)}} signal threshold`, "axis-label"));

      rows.forEach(row => {{
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", x(row.signalCagr));
        circle.setAttribute("cy", y(row.cagr));
        circle.setAttribute("r", row.start > 1000000 ? "6.5" : row.start > 100000 ? "5.2" : "4.2");
        circle.setAttribute("fill", !row.matchesOpportunity ? "var(--orange)" : row.signalCagr < 0 ? "var(--green)" : "var(--teal)");
        circle.setAttribute("opacity", row.matchesOpportunity ? "0.84" : "0.36");
        circle.setAttribute("class", "series-point");
        circle.setAttribute("tabindex", "0");
        circle.setAttribute("aria-label", `${{row.city}}. Population CAGR ${{signedPercent(row.cagr)}}. ${{row.signalBasis}} YoY ${{signedPercent(row.signalCagr)}}.`);
        circle.appendChild(document.createElementNS("http://www.w3.org/2000/svg", "title")).textContent =
          `${{row.city}}\\nPopulation CAGR: ${{signedPercent(row.cagr)}}\\n${{row.signalBasis}} YoY: ${{signedPercent(row.signalCagr)}}\\nSpread: ${{signedPercent(row.opportunitySpread)}}`;
        circle.addEventListener("mouseenter", event => showOpportunityTooltip(row, event, circle));
        circle.addEventListener("mousemove", event => moveOpportunityTooltip(event, circle));
        circle.addEventListener("mouseleave", hideOpportunityTooltip);
        circle.addEventListener("focus", event => showOpportunityTooltip(row, event, circle));
        circle.addEventListener("blur", hideOpportunityTooltip);
        svg.appendChild(circle);
      }});
    }}

    function showOpportunityTooltip(row, event, circle) {{
      elements.opportunityTooltip.innerHTML = `
        <div class="tooltip-title">${{escapeHtml(row.city)}}</div>
        <div class="tooltip-row"><span>Population CAGR</span><b>${{signedPercent(row.cagr)}}</b></div>
        <div class="tooltip-row"><span>Signal basis</span><b>${{escapeHtml(row.signalBasis)}}</b></div>
        <div class="tooltip-row"><span>Signal YoY</span><b>${{signedPercent(row.signalCagr)}}</b></div>
        <div class="tooltip-row"><span>Growth-signal spread</span><b>${{signedPercent(row.opportunitySpread)}}</b></div>
        <div class="tooltip-row"><span>Start population</span><b>${{number(row.start)}}</b></div>
        <div class="tooltip-row"><span>Status</span><b>${{row.matchesOpportunity ? "Matches screen" : "Above threshold"}}</b></div>
      `;
      elements.opportunityTooltip.hidden = false;
      moveOpportunityTooltip(event, circle);
    }}

    function moveOpportunityTooltip(event, circle) {{
      if (elements.opportunityTooltip.hidden) return;
      const frame = elements.opportunityTooltip.parentElement;
      const frameRect = frame.getBoundingClientRect();
      const tooltipRect = elements.opportunityTooltip.getBoundingClientRect();
      let left;
      let top;
      if (event && event.clientX != null && event.clientY != null) {{
        left = event.clientX - frameRect.left + 12;
        top = event.clientY - frameRect.top + 12;
      }} else {{
        left = Number(circle.getAttribute("cx")) + 14;
        top = Number(circle.getAttribute("cy")) + 14;
      }}
      left = Math.min(Math.max(8, left), Math.max(8, frameRect.width - tooltipRect.width - 8));
      top = Math.min(Math.max(8, top), Math.max(8, frameRect.height - tooltipRect.height - 8));
      elements.opportunityTooltip.style.left = `${{left}}px`;
      elements.opportunityTooltip.style.top = `${{top}}px`;
    }}

    function hideOpportunityTooltip() {{
      elements.opportunityTooltip.hidden = true;
    }}

    function renderOpportunityLegend() {{
      elements.opportunityLegend.innerHTML = `
        <div class="legend-item"><span class="swatch" style="background:var(--green)"></span><span>Population growth + decreasing selected signal</span></div>
        <div class="legend-item"><span class="swatch" style="background:var(--teal)"></span><span>Population growth + stable selected signal</span></div>
        <div class="legend-item"><span class="swatch" style="background:var(--orange); opacity:0.36"></span><span>Population growth + signal above threshold</span></div>
      `;
    }}

    function renderInvestmentPotential(rankings) {{
      const rows = computeInvestmentRows(rankings)
        .filter(row => row.city.toLowerCase().includes(state.search));
      const visible = applyRowLimit(rows);
      elements.investmentPeriod.textContent = `${{state.startYear}}-${{state.endYear}}`;
      elements.investmentCount.textContent = `${{rows.length.toLocaleString()}} municipalities`;
      renderInvestmentSummary(rows);
      renderInvestmentTable(visible, rows.length);
      renderInvestmentYieldDemandChart(elements.investmentYieldDemandChart, rows.slice(0, 120));
      renderInvestmentSupplyChart(elements.investmentSupplyChart, rows.slice(0, 120));
    }}

    function computeInvestmentRows(rankings) {{
      const rows = rankings.map(row => computeInvestmentRow(row)).filter(Boolean);
      rows.sort(compareInvestmentRows);
      rows.forEach((row, index) => row.rank = index + 1);
      return rows;
    }}

    function compareInvestmentRows(a, b) {{
      if (state.sortMode === "demand-score-desc") return nullableDesc(a.demandScore, b.demandScore) || b.investmentScore - a.investmentScore;
      if (state.sortMode === "supply-score-desc") return nullableDesc(a.supplyScore, b.supplyScore) || b.investmentScore - a.investmentScore;
      if (state.sortMode === "yield-score-desc") return nullableDesc(a.grossRentalYieldPct, b.grossRentalYieldPct) || b.investmentScore - a.investmentScore;
      if (state.sortMode === "price-to-rent-asc") return nullableAsc(a.priceToRentRatio, b.priceToRentRatio) || b.investmentScore - a.investmentScore;
      if (state.sortMode === "population-cagr-desc" || state.sortMode === "cagr-desc") return b.populationCagrPct - a.populationCagrPct || b.investmentScore - a.investmentScore;
      if (state.sortMode === "abs-desc") return b.absolutePopulationChange - a.absolutePopulationChange || b.investmentScore - a.investmentScore;
      if (state.sortMode === "absorption-desc") return nullableDesc(a.absorptionRatioScoreValue, b.absorptionRatioScoreValue) || b.investmentScore - a.investmentScore;
      if (state.sortMode === "pipeline-asc") return nullableAsc(a.pipelineRateScoreValue, b.pipelineRateScoreValue) || b.investmentScore - a.investmentScore;
      if (state.sortMode === "data-quality-desc") return b.dataQualityScore - a.dataQualityScore || b.investmentScore - a.investmentScore;
      return b.investmentScore - a.investmentScore || b.scoreCompleteness - a.scoreCompleteness || a.city.localeCompare(b.city);
    }}

    function computeInvestmentRow(row) {{
      const housingSignals = housingSignalsForPopulationKey(row.key);
      const supply = computeSupplyDemandMetrics(row);
      const demandScore = scoreDemand(row);
      const supplyScore = scoreSupplyConstraint(supply);
      const yieldScore = scoreYield(housingSignals);
      const affordabilityScore = scoreAffordability(row, housingSignals);
      const dataQualityScore = scoreDataQuality(row, supply, housingSignals);
      const score = computeInvestmentScore({{
        demandScore,
        supplyScore,
        yieldScore,
        affordabilityScore,
        dataQualityScore
      }});
      const coverageLevel = summarizeDistinct([
        housingSignals.coverageLevel,
        supply.coverageLevel
      ].filter(Boolean));
      const dataQuality = investmentDataQuality(score.scoreCompleteness, dataQualityScore);
      return {{
        city: row.city,
        city_id: row.city_id,
        key: row.key,
        rank: null,
        investmentScore: score.value,
        demandScore,
        supplyScore,
        yieldScore,
        affordabilityScore,
        dataQualityScore,
        scoreCompleteness: score.scoreCompleteness,
        scoreCompletenessLabel: score.scoreCompletenessLabel,
        reasonLabel: investmentReasonLabel(row, supply, housingSignals, score),
        dataQuality,
        coverageLevel,
        sourceArea: summarizeDistinct([housingSignals.sourceArea, supply.sourceArea].filter(Boolean)),
        startPopulation: row.start,
        endPopulation: row.end,
        absolutePopulationChange: row.absChange,
        populationCagrPct: row.cagr,
        populationGrowthPct: row.total,
        medianPurchasePrice: housingSignals.endPurchaseMedian,
        medianAskingRent: housingSignals.endAskingRent,
        purchasePriceGrowthPct: housingSignals.purchaseGrowth?.pctChange ?? null,
        rentGrowthPct: housingSignals.rentGrowth?.pctChange ?? null,
        grossRentalYieldPct: housingSignals.grossRentalYieldPct,
        priceToRentRatio: housingSignals.priceToRentRatio,
        absorptionRatio: supply.absorptionRatio,
        absorptionRatioDisplay: supply.absorptionRatioDisplay,
        absorptionRatioScoreValue: supply.absorptionRatioScoreValue,
        absorptionLabel: supply.absorptionLabel,
        pipelineRate: supply.pipelineRate,
        pipelineRateDisplay: supply.pipelineRateDisplay,
        pipelineRateScoreValue: supply.pipelineRateScoreValue,
        pipelineLabel: supply.pipelineLabel,
        totalCompletions: supply.totalCompletions,
        totalPermits: supply.totalPermits,
        supplyDataStatus: supply.status,
        yieldAvailable: housingSignals.grossRentalYieldPct != null,
        purchaseAvailable: housingSignals.endPurchaseMedian != null,
        rentAvailable: housingSignals.endAskingRent != null
      }};
    }}

    function housingSignalsForPopulationKey(populationKey) {{
      const housingEntry = housingEntryForPopulationKey(populationKey);
      const purchaseStats = aggregateHousingStatsByYearForEntry(housingEntry);
      const marketRent = metricByYear(populationKey, "asking_rent_eur_per_m2");
      const yearsElapsed = state.endYear - state.startYear;
      const startPurchaseMedian = purchaseStats.get(state.startYear)?.purchaseMedian ?? null;
      const endPurchaseMedian = purchaseStats.get(state.endYear)?.purchaseMedian ?? null;
      const startRent = marketRent.get(state.startYear)?.value ?? purchaseStats.get(state.startYear)?.rentMedian ?? null;
      const endRent = marketRent.get(state.endYear)?.value ?? purchaseStats.get(state.endYear)?.rentMedian ?? null;
      const yieldMetrics = computeYieldMetrics(endPurchaseMedian, endRent);
      const purchaseCoverage = purchaseStats.get(state.endYear)?.coverageSummary || null;
      const rentCoverage = marketRent.get(state.endYear)?.coverage_level || purchaseStats.get(state.endYear)?.coverageSummary || null;
      const rentSourceArea = marketRent.get(state.endYear)?.source_area || purchaseStats.get(state.endYear)?.sourceAreaSummary || null;
      const expectedYears = state.endYear - state.startYear + 1;
      const rentAvailableYears = Array.from({{ length: expectedYears }}, (_, index) => state.startYear + index)
        .filter(year => marketRent.has(year) || purchaseStats.get(year)?.rentRecordCount > 0)
        .length;
      return {{
        startPurchaseMedian,
        endPurchaseMedian,
        startAskingRent: startRent,
        endAskingRent: endRent,
        grossRentalYieldPct: yieldMetrics?.grossRentalYieldPct ?? null,
        priceToRentRatio: yieldMetrics?.priceToRentRatio ?? null,
        purchaseGrowth: growthMetrics(startPurchaseMedian, endPurchaseMedian, yearsElapsed),
        rentGrowth: growthMetrics(startRent, endRent, yearsElapsed),
        rentQuality: dataQuality(rentAvailableYears, expectedYears),
        coverageLevel: summarizeDistinct([purchaseCoverage, rentCoverage].filter(Boolean)) || "Unavailable",
        sourceArea: summarizeDistinct([purchaseStats.get(state.endYear)?.sourceAreaSummary, rentSourceArea].filter(Boolean)),
        hasPurchase: endPurchaseMedian != null,
        hasRent: endRent != null
      }};
    }}

    function computeYieldMetrics(purchasePricePerM2, monthlyRentPerM2) {{
      if (purchasePricePerM2 == null || monthlyRentPerM2 == null || purchasePricePerM2 <= 0 || monthlyRentPerM2 <= 0) return null;
      const annualRentPerM2 = monthlyRentPerM2 * 12;
      return {{
        annualRentPerM2,
        grossRentalYieldPct: (annualRentPerM2 / purchasePricePerM2) * 100,
        priceToRentRatio: purchasePricePerM2 / annualRentPerM2
      }};
    }}

    function computeSupplyDemandMetrics(row) {{
      const permitSeries = metricByYear(row.key, "building_permits_per_1000_residents");
      const completionSeries = metricByYear(row.key, "completed_new_apartments_per_1000_residents");
      const populationByYear = new Map(row.series.map(point => [point.year, point.value]));
      let totalCompletions = 0;
      let totalPermits = 0;
      let completionYears = 0;
      let permitYears = 0;
      let completionRateSum = 0;
      let permitRateSum = 0;
      const coverageLevels = new Set();
      const sourceAreas = new Set();
      for (let year = state.startYear; year <= state.endYear; year += 1) {{
        const population = populationByYear.get(year);
        const completion = completionSeries.get(year);
        const permit = permitSeries.get(year);
        if (population != null && completion?.value != null) {{
          totalCompletions += population * completion.value / 1000;
          completionYears += 1;
          completionRateSum += completion.value;
          coverageLevels.add(completion.coverage_level || "municipality");
          sourceAreas.add(completion.source_area || row.city);
        }}
        if (population != null && permit?.value != null) {{
          totalPermits += population * permit.value / 1000;
          permitYears += 1;
          permitRateSum += permit.value;
          coverageLevels.add(permit.coverage_level || "municipality");
          sourceAreas.add(permit.source_area || row.city);
        }}
      }}
      const populationChange = row.absChange;
      const hasSupplyData = completionYears > 0 || permitYears > 0;
      let absorptionRatio = null;
      let absorptionRatioDisplay = "Insufficient supply data";
      let absorptionRatioScoreValue = null;
      if (completionYears > 0 && totalCompletions > 0) {{
        absorptionRatio = populationChange / totalCompletions;
        absorptionRatioScoreValue = absorptionRatio;
        absorptionRatioDisplay = numberDecimal(absorptionRatio, 2);
      }} else if (populationChange > 0 && totalCompletions === 0 && hasSupplyData) {{
        absorptionRatioScoreValue = 10;
        absorptionRatioDisplay = "No completions";
      }}

      let pipelineRate = null;
      let pipelineRateDisplay = "Unavailable";
      let pipelineRateScoreValue = null;
      if (totalCompletions > 0) {{
        pipelineRate = totalPermits / totalCompletions;
        pipelineRateScoreValue = pipelineRate;
        pipelineRateDisplay = numberDecimal(pipelineRate, 2);
      }} else if (totalPermits > 0) {{
        pipelineRateScoreValue = 10;
        pipelineRateDisplay = "Unbounded";
      }}

      return {{
        totalCompletions,
        totalPermits,
        completionYears,
        permitYears,
        completionRateAvg: completionYears ? completionRateSum / completionYears : null,
        permitRateAvg: permitYears ? permitRateSum / permitYears : null,
        absorptionRatio,
        absorptionRatioDisplay,
        absorptionRatioScoreValue,
        absorptionLabel: absorptionPressureLabel(absorptionRatio, absorptionRatioDisplay, populationChange),
        pipelineRate,
        pipelineRateDisplay,
        pipelineRateScoreValue,
        pipelineLabel: pipelineLabel(pipelineRate, pipelineRateDisplay),
        coverageLevel: summarizeDistinct(Array.from(coverageLevels)) || "Unavailable",
        sourceArea: summarizeDistinct(Array.from(sourceAreas)) || "",
        status: hasSupplyData ? "Available" : "Insufficient supply data"
      }};
    }}

    function metricByYear(populationKey, metric) {{
      const entry = marketByCity.get(populationKey);
      const result = new Map();
      if (!entry || !entry.metrics.has(metric)) return result;
      entry.metrics.get(metric).forEach(row => {{
        if (row.year >= state.startYear && row.year <= state.endYear) result.set(row.year, row);
      }});
      return result;
    }}

    function scoreDemand(row) {{
      const cagrScore = clamp(((row.cagr + 1) / 3) * 55, 0, 55);
      const absRate = row.absChange / Math.max(1, row.start);
      const absScore = clamp(absRate * 180, 0, 25);
      const baseScore = clamp((Math.log10(Math.max(1000, row.start)) - 3) / 3 * 20, 0, 20);
      const smallPenalty = row.start < 10000 && state.populationBand !== "small" && state.populationBand !== "custom" ? 12 : 0;
      return clamp(cagrScore + absScore + baseScore - smallPenalty, 0, 100);
    }}

    function scoreSupplyConstraint(supply) {{
      if (supply.absorptionRatioScoreValue == null) return null;
      let score = piecewise(supply.absorptionRatioScoreValue, [
        [0, 0],
        [0.7, 25],
        [1.2, 45],
        [2.0, 75],
        [3.0, 100]
      ]);
      if (supply.pipelineRateScoreValue != null) {{
        if (supply.pipelineRateScoreValue > 1.25) {{
          score -= clamp((supply.pipelineRateScoreValue - 1.25) / 1.25 * 10, 0, 10);
        }} else if (supply.pipelineRateScoreValue < 0.75) {{
          score += clamp((0.75 - supply.pipelineRateScoreValue) / 0.75 * 10, 0, 10);
        }}
      }}
      return clamp(score, 0, 100);
    }}

    function scoreYield(housingSignals) {{
      const yieldPct = housingSignals.grossRentalYieldPct;
      if (yieldPct == null) return null;
      const yieldScore = piecewise(yieldPct, [
        [0, 0],
        [2.0, 25],
        [3.5, 55],
        [5.0, 85],
        [7.0, 95]
      ]);
      const ratio = housingSignals.priceToRentRatio;
      const ratioModifier = ratio == null ? 0 : ratio <= 18 ? 10 : ratio <= 28 ? 0 : -12;
      return clamp(yieldScore + ratioModifier, 0, 100);
    }}

    function scoreAffordability(row, housingSignals) {{
      if (!housingSignals.purchaseGrowth?.valid && !housingSignals.rentGrowth?.valid) return null;
      let score = 50;
      const purchaseGrowth = housingSignals.purchaseGrowth?.cagr ?? null;
      const rentGrowth = housingSignals.rentGrowth?.cagr ?? null;
      if (purchaseGrowth != null) score += clamp((4 - purchaseGrowth) * 7, -30, 25);
      if (rentGrowth != null) score += clamp(rentGrowth * 8, -25, 25);
      if (purchaseGrowth != null && rentGrowth != null) {{
        score += clamp((rentGrowth - purchaseGrowth) * 8, -25, 25);
      }}
      if (row.cagr > 0 && purchaseGrowth != null && purchaseGrowth <= row.cagr + 2) score += 8;
      if (rentGrowth != null && rentGrowth < -1) score -= 20;
      return clamp(score, 0, 100);
    }}

    function scoreDataQuality(row, supply, housingSignals) {{
      let score = 100;
      if (row.quality.label === "Medium") score -= 10;
      if (row.quality.label === "Low") score -= 25;
      if (supply.status !== "Available") score -= 20;
      if (!housingSignals.hasPurchase) score -= 18;
      if (!housingSignals.hasRent) score -= 18;
      if (housingSignals.grossRentalYieldPct == null) score -= 14;
      const coverageText = `${{housingSignals.coverageLevel}} ${{supply.coverageLevel}}`.toLowerCase();
      if (coverageText.includes("district")) score -= state.granularityMode === "conservative" ? 18 : 8;
      if (coverageText.includes("area")) score -= state.granularityMode === "conservative" ? 14 : 4;
      return clamp(score, 0, 100);
    }}

    function computeInvestmentScore(scores) {{
      const weighted = [
        ["demandScore", investmentWeights.demand],
        ["supplyScore", investmentWeights.supply],
        ["yieldScore", investmentWeights.yield],
        ["affordabilityScore", investmentWeights.affordability],
        ["dataQualityScore", investmentWeights.dataQuality]
      ];
      let availableWeight = 0;
      let total = 0;
      const available = [];
      const missing = [];
      weighted.forEach(([key, weight]) => {{
        if (scores[key] == null || !Number.isFinite(scores[key])) {{
          missing.push(key.replace("Score", ""));
          return;
        }}
        availableWeight += weight;
        total += scores[key] * weight;
        available.push(key.replace("Score", ""));
      }});
      const value = availableWeight > 0 ? total / availableWeight : 0;
      return {{
        value: clamp(value, 0, 100),
        scoreCompleteness: availableWeight,
        scoreCompletenessLabel: `${{Math.round(availableWeight * 100)}}% (${{available.join(", ") || "none"}}${{missing.length ? "; missing " + missing.join(", ") : ""}})`
      }};
    }}

    function investmentReasonLabel(row, supply, housingSignals, score) {{
      if (score.scoreCompleteness < 0.45) return "Insufficient investment data";
      if (row.cagr > 0.5 && supply.absorptionRatioDisplay === "No completions") return "No completions + positive demand";
      if (row.cagr > 0.5 && supply.absorptionRatioScoreValue >= 2) return "High demand + constrained supply";
      if (housingSignals.grossRentalYieldPct != null && housingSignals.grossRentalYieldPct >= 3.5 && row.cagr > 0) return "Good yield + positive demand";
      if (row.cagr > 0 && housingSignals.grossRentalYieldPct == null) return "Strong growth but missing yield";
      if (row.cagr > 0 && housingSignals.grossRentalYieldPct != null && housingSignals.grossRentalYieldPct < 2) return "Growing but low yield";
      if (row.cagr <= 0 && housingSignals.endPurchaseMedian != null) return "Cheap but weak demand";
      if (supply.absorptionRatioScoreValue != null && supply.absorptionRatioScoreValue < 0.7) return "Possible oversupply risk";
      if (`${{housingSignals.coverageLevel}} ${{supply.coverageLevel}}`.toLowerCase().includes("district")) return "High growth but district-level fallback";
      return "Balanced but check fundamentals";
    }}

    function investmentDataQuality(completeness, dataQualityScore) {{
      if (completeness < 0.45 || dataQualityScore < 45) return {{ label: "Low", className: "quality-low" }};
      if (completeness < 0.8 || dataQualityScore < 75) return {{ label: "Medium", className: "quality-medium" }};
      return {{ label: "High", className: "quality-high" }};
    }}

    function absorptionPressureLabel(value, display, populationChange) {{
      if (display === "No completions") return "No completions + positive demand";
      if (value == null) return populationChange < 0 ? "Shrinking population" : "Insufficient supply data";
      if (value > 2.0) return "Severe shortage / high rent pressure";
      if (value >= 1.2) return "Tight / undersupplied";
      if (value >= 0.7) return "Broadly balanced";
      if (value >= 0) return "Potential oversupply";
      return "Shrinking population";
    }}

    function pipelineLabel(value, display) {{
      if (display === "Unbounded") return "Unbounded supply pipeline";
      if (value == null) return "Unavailable";
      if (value > 1.25) return "Expanding supply pipeline";
      if (value >= 0.75) return "Stable pipeline";
      return "Weak / shrinking pipeline";
    }}

    function piecewise(value, points) {{
      if (value <= points[0][0]) return points[0][1];
      for (let index = 1; index < points.length; index += 1) {{
        const [x1, y1] = points[index - 1];
        const [x2, y2] = points[index];
        if (value <= x2) {{
          const ratio = (value - x1) / (x2 - x1 || 1);
          return y1 + ratio * (y2 - y1);
        }}
      }}
      return points[points.length - 1][1];
    }}

    function renderInvestmentSummary(rows) {{
      const top = rows[0];
      const scoreValues = rows.map(row => row.investmentScore).sort((a, b) => a - b);
      const computableYield = rows.filter(row => row.grossRentalYieldPct != null).length;
      const highQuality = rows.filter(row => row.dataQuality.label === "High").length;
      elements.investmentSummary.innerHTML = `
        <div class="investment-stat">
          <div class="investment-stat-value" title="${{top ? escapeAttribute(top.city) : ""}}">${{top ? escapeHtml(top.city) : "--"}}</div>
          <div class="investment-stat-label">Top ranked municipality</div>
        </div>
        <div class="investment-stat">
          <div class="investment-stat-value">${{scoreValues.length ? numberDecimal(median(scoreValues), 1) : "--"}}</div>
          <div class="investment-stat-label">Median investment score</div>
        </div>
        <div class="investment-stat">
          <div class="investment-stat-value">${{rows.length.toLocaleString()}}</div>
          <div class="investment-stat-label">Investable candidates</div>
        </div>
        <div class="investment-stat">
          <div class="investment-stat-value">${{computableYield.toLocaleString()}}</div>
          <div class="investment-stat-label">With computable yield</div>
        </div>
        <div class="investment-stat">
          <div class="investment-stat-value">${{highQuality.toLocaleString()}}</div>
          <div class="investment-stat-label">High data quality</div>
        </div>
      `;
    }}

    function renderInvestmentTable(rows, filteredCount) {{
      elements.investmentBody.textContent = "";
      if (!rows.length) {{
        elements.investmentBody.innerHTML = `<tr><td colspan="21">No municipalities match the active filters.</td></tr>`;
        return;
      }}
      const fragment = document.createDocumentFragment();
      rows.forEach(row => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${{row.rank}}</td>
          <td title="${{escapeAttribute(row.city)}}">${{escapeHtml(row.city)}}</td>
          <td>${{scoreText(row.investmentScore)}}</td>
          <td>${{scoreText(row.demandScore)}}</td>
          <td>${{scoreText(row.supplyScore, "Insufficient supply data")}}</td>
          <td>${{scoreText(row.yieldScore, "Unavailable")}}</td>
          <td>${{scoreText(row.affordabilityScore, "Unavailable")}}</td>
          <td>${{scoreText(row.dataQualityScore)}}</td>
          <td title="${{escapeAttribute(row.scoreCompletenessLabel)}}">${{signedPercent(row.scoreCompleteness * 100).replace("+", "")}}</td>
          <td>${{number(row.startPopulation)}}</td>
          <td>${{signedPercent(row.populationCagrPct)}}</td>
          <td>${{signedNumber(row.absolutePopulationChange)}}</td>
          <td>${{row.grossRentalYieldPct == null ? "Unavailable" : signedPercent(row.grossRentalYieldPct).replace("+", "")}}</td>
          <td>${{row.priceToRentRatio == null ? "Unavailable" : numberDecimal(row.priceToRentRatio, 1)}}</td>
          <td>${{row.medianPurchasePrice == null ? "Unavailable" : money(row.medianPurchasePrice)}}</td>
          <td>${{row.medianAskingRent == null ? "Unavailable" : money(row.medianAskingRent)}}</td>
          <td title="${{escapeAttribute(row.absorptionLabel)}}">${{row.absorptionRatioDisplay}}</td>
          <td title="${{escapeAttribute(row.pipelineLabel)}}">${{row.pipelineRateDisplay}}</td>
          <td title="${{escapeAttribute(row.sourceArea)}}">${{escapeHtml(row.coverageLevel || "Unavailable")}}</td>
          <td>${{qualityBadge(row.dataQuality)}}</td>
          <td title="${{escapeAttribute(row.reasonLabel)}}">${{escapeHtml(row.reasonLabel)}}</td>
        `;
        fragment.appendChild(tr);
      }});
      elements.investmentBody.appendChild(fragment);
      elements.investmentCount.textContent = `${{rows.length.toLocaleString()}} of ${{filteredCount.toLocaleString()}} municipalities`;
    }}

    function renderInvestmentYieldDemandChart(svg, rows) {{
      const points = rows.filter(row => row.grossRentalYieldPct != null);
      renderInvestmentScatter(svg, points, {{
        xValue: row => row.grossRentalYieldPct,
        yValue: row => row.populationCagrPct,
        xLabel: "Gross rental yield %",
        yLabel: "Population CAGR %",
        empty: "No rows with computable gross rental yield",
        tooltip: row => `${{row.city}}\\nInvestment score: ${{scoreText(row.investmentScore)}}\\nGross yield: ${{signedPercent(row.grossRentalYieldPct)}}\\nPopulation CAGR: ${{signedPercent(row.populationCagrPct)}}\\nAbsorption: ${{row.absorptionRatioDisplay}}\\nData quality: ${{row.dataQuality.label}}`
      }});
    }}

    function renderInvestmentSupplyChart(svg, rows) {{
      const points = rows.filter(row => row.absorptionRatioScoreValue != null);
      renderInvestmentScatter(svg, points, {{
        xValue: row => row.populationCagrPct,
        yValue: row => Math.min(10, row.absorptionRatioScoreValue),
        xLabel: "Population CAGR %",
        yLabel: "Absorption ratio",
        empty: "No rows with supply-demand data",
        tooltip: row => `${{row.city}}\\nPopulation change: ${{signedNumber(row.absolutePopulationChange)}}\\nTotal completions: ${{number(row.totalCompletions)}}\\nAbsorption: ${{row.absorptionRatioDisplay}}\\nPipeline: ${{row.pipelineRateDisplay}}`
      }});
    }}

    function renderInvestmentScatter(svg, rows, config) {{
      if (!rows.length) {{
        drawEmptySvg(svg, config.empty);
        return;
      }}
      const frame = svg.parentElement;
      const frameRect = frame.getBoundingClientRect();
      const width = Math.max(460, Math.floor(frameRect.width || svg.clientWidth || 760));
      const height = Math.max(260, Math.floor(frameRect.height || svg.clientHeight || 340));
      const margin = {{ top: 26, right: 28, bottom: 42, left: 70 }};
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      const xValues = rows.map(config.xValue);
      const yValues = rows.map(config.yValue);
      const xExtent = extent([...xValues, 0]);
      const yExtent = extent([...yValues, 0]);
      const xPad = (xExtent[1] - xExtent[0]) * 0.12 || 1;
      const yPad = (yExtent[1] - yExtent[0]) * 0.12 || 1;
      const xMin = Math.min(0, xExtent[0] - xPad);
      const xMax = xExtent[1] + xPad;
      const yMin = Math.min(0, yExtent[0] - yPad);
      const yMax = yExtent[1] + yPad;
      const x = value => margin.left + ((value - xMin) / (xMax - xMin || 1)) * plotWidth;
      const y = value => margin.top + (1 - ((value - yMin) / (yMax - yMin || 1))) * plotHeight;
      svg.setAttribute("width", width);
      svg.setAttribute("height", height);
      svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
      svg.textContent = "";
      ticks(xMin, xMax, 5).forEach(tick => {{
        svg.appendChild(line(x(tick), margin.top, x(tick), height - margin.bottom, "grid-line"));
        svg.appendChild(text(x(tick), height - margin.bottom + 24, numberDecimal(tick, 1), "axis-label", "middle"));
      }});
      ticks(yMin, yMax, 5).forEach(tick => {{
        svg.appendChild(line(margin.left, y(tick), width - margin.right, y(tick), "grid-line"));
        svg.appendChild(text(margin.left - 10, y(tick) + 4, numberDecimal(tick, 1), "axis-label", "end"));
      }});
      svg.appendChild(line(margin.left, height - margin.bottom, width - margin.right, height - margin.bottom, "axis"));
      svg.appendChild(line(margin.left, margin.top, margin.left, height - margin.bottom, "axis"));
      svg.appendChild(text(margin.left, margin.top - 8, config.yLabel, "axis-label"));
      svg.appendChild(text(width - margin.right, height - 8, config.xLabel, "axis-label", "end"));
      rows.forEach(row => {{
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", x(config.xValue(row)));
        circle.setAttribute("cy", y(config.yValue(row)));
        circle.setAttribute("r", row.investmentScore >= 75 ? "6" : "4.5");
        circle.setAttribute("fill", row.dataQuality.label === "High" ? "var(--green)" : row.dataQuality.label === "Medium" ? "var(--orange)" : "var(--red)");
        circle.setAttribute("opacity", "0.78");
        circle.setAttribute("class", "series-point");
        circle.appendChild(document.createElementNS("http://www.w3.org/2000/svg", "title")).textContent = config.tooltip(row);
        svg.appendChild(circle);
      }});
    }}

    function renderClassification(rankings) {{
      const selectedRows = rankings.filter(row => state.selected.has(row.key)).slice(0, 7);
      elements.classificationPeriod.textContent = `${{state.startYear}}-${{state.endYear}}`;
      elements.classificationGrid.textContent = "";

      if (!selectedRows.length) {{
        const empty = document.createElement("div");
        empty.className = "classification-empty";
        empty.textContent = "Select one or more cities from the ranked table to classify their growth curves.";
        elements.classificationGrid.appendChild(empty);
        return;
      }}

      selectedRows.forEach((row, index) => {{
        const result = classifyTrend(row);
        const color = colors[index % colors.length];
        const card = document.createElement("article");
        card.className = "classification-card";
        card.innerHTML = `
          <div class="classification-card-head">
            <div class="classification-city" title="${{escapeAttribute(row.city)}}">${{escapeHtml(row.city)}}</div>
            <div class="classification-label ${{result.className}}">${{result.label}}</div>
          </div>
          <div class="mini-chart">
            <svg role="img" aria-label="${{escapeAttribute(row.city)}} population curve"></svg>
          </div>
          <div class="classification-meta">
            <div class="meta-item">
              <div class="meta-value">${{number(row.start)}}</div>
              <div class="meta-label">Start pop.</div>
            </div>
            <div class="meta-item">
              <div class="meta-value">${{number(row.end)}}</div>
              <div class="meta-label">End pop.</div>
            </div>
            <div class="meta-item">
              <div class="meta-value">${{signedNumber(row.absChange)}}</div>
              <div class="meta-label">Abs. change</div>
            </div>
            <div class="meta-item">
              <div class="meta-value">${{signedPercent(row.total)}}</div>
              <div class="meta-label">Growth %</div>
            </div>
            <div class="meta-item">
              <div class="meta-value">${{signedPercent(row.cagr)}}</div>
              <div class="meta-label">CAGR</div>
            </div>
            <div class="meta-item">
              <div class="meta-value">${{populationSizeBandLabel(row.sizeBand)}}</div>
              <div class="meta-label">Size band</div>
            </div>
            <div class="meta-item">
              <div class="meta-value">${{qualityBadge(row.quality)}}</div>
              <div class="meta-label">Quality</div>
            </div>
          </div>
        `;
        elements.classificationGrid.appendChild(card);
        renderMiniChart(card.querySelector("svg"), row, color);
      }});
    }}

    function classifyTrend(row) {{
      const bandContext = `${{populationSizeBandLabel(row.sizeBand).toLowerCase()}} population base`;
      if (row.series.length < 3 || row.start == null || row.end == null || row.start <= 0 || row.end <= 0) {{
        return {{ label: `Insufficient data - ${{bandContext}}`, className: "label-insufficient" }};
      }}

      const yearlyRates = [];
      for (let index = 1; index < row.series.length; index += 1) {{
        const previous = row.series[index - 1].value;
        const current = row.series[index].value;
        if (previous > 0 && current > 0) yearlyRates.push(((current - previous) / previous) * 100);
      }}
      const directionSigns = yearlyRates
        .map(value => Math.abs(value) < 0.05 ? 0 : Math.sign(value))
        .filter(value => value !== 0);
      const signFlips = directionSigns.slice(1).filter((value, index) => value !== directionSigns[index]).length;
      const rateSpread = yearlyRates.length ? standardDeviation(yearlyRates) : 0;
      const averageRate = yearlyRates.length ? mean(yearlyRates) : 0;

      if (row.quality.label === "Low" || (yearlyRates.length >= 4 && signFlips >= 2 && rateSpread > Math.max(0.35, Math.abs(averageRate) * 1.8))) {{
        return {{ label: `Volatile / unstable growth - ${{bandContext}}`, className: "label-volatile" }};
      }}

      if (Math.abs(row.cagr) < 0.1 || Math.abs(row.total) < 1.0) {{
        return {{ label: `Stagnant growth - ${{bandContext}}`, className: "label-stagnant" }};
      }}

      const linearFit = linearRegressionForRow(row);
      const expFit = exponentialRegressionForRow(row);
      const exponentialWins = expFit && expFit.r2 >= linearFit.r2 + 0.03;
      const direction = row.cagr >= 0 ? "Positive" : "Negative";
      const shape = exponentialWins ? "exponential" : "linear";

      return {{
        label: `${{direction}} ${{shape}} growth - ${{bandContext}}`,
        className: row.cagr >= 0 ? "label-positive" : "label-negative"
      }};
    }}

    function linearRegressionForRow(row) {{
      const startYear = row.series[0].year;
      const xs = row.series.map(d => d.year - startYear);
      const ys = row.series.map(d => d.value);
      return linearRegression(xs, ys);
    }}

    function exponentialRegressionForRow(row) {{
      if (row.series.some(d => d.value <= 0)) return null;
      const startYear = row.series[0].year;
      const xs = row.series.map(d => d.year - startYear);
      const ys = row.series.map(d => Math.log(d.value));
      return linearRegression(xs, ys);
    }}

    function linearRegression(xs, ys) {{
      const xMean = mean(xs);
      const yMean = mean(ys);
      const denominator = xs.reduce((sum, xValue) => sum + Math.pow(xValue - xMean, 2), 0);
      if (denominator === 0) return {{ slope: 0, intercept: yMean, r2: 0 }};
      const slope = xs.reduce((sum, xValue, index) => sum + (xValue - xMean) * (ys[index] - yMean), 0) / denominator;
      const intercept = yMean - slope * xMean;
      const predicted = xs.map(xValue => intercept + slope * xValue);
      return {{ slope, intercept, r2: rSquared(ys, predicted) }};
    }}

    function rSquared(actual, predicted) {{
      const actualMean = mean(actual);
      const total = actual.reduce((sum, value) => sum + Math.pow(value - actualMean, 2), 0);
      if (total === 0) return 1;
      const residual = actual.reduce((sum, value, index) => sum + Math.pow(value - predicted[index], 2), 0);
      return Math.max(0, Math.min(1, 1 - residual / total));
    }}

    function renderMiniChart(svg, row, color) {{
      const width = 420;
      const height = 190;
      const margin = {{ top: 16, right: 12, bottom: 26, left: 54 }};
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      const xMin = row.series[0].year;
      const xMax = row.series[row.series.length - 1].year;
      const base = row.series[0].value;
      const values = row.series.map(d => state.view === "index" ? (d.value / base) * 100 : d.value);
      const yExtent = extent(values);
      const yPad = (yExtent[1] - yExtent[0]) * 0.1 || Math.max(1, yExtent[0] * 0.01);
      const yMin = Math.max(0, yExtent[0] - yPad);
      const yMax = yExtent[1] + yPad;
      const x = year => margin.left + ((year - xMin) / (xMax - xMin || 1)) * plotWidth;
      const y = value => margin.top + (1 - ((value - yMin) / (yMax - yMin || 1))) * plotHeight;

      svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
      svg.textContent = "";

      ticks(yMin, yMax, 3).forEach(tick => {{
        svg.appendChild(line(margin.left, y(tick), width - margin.right, y(tick), "grid-line"));
        const label = state.view === "index" ? tick.toFixed(0) : compact(tick);
        svg.appendChild(text(margin.left - 8, y(tick) + 4, label, "axis-label", "end"));
      }});
      svg.appendChild(line(margin.left, margin.top, margin.left, height - margin.bottom, "axis"));
      svg.appendChild(line(margin.left, height - margin.bottom, width - margin.right, height - margin.bottom, "axis"));
      svg.appendChild(text(margin.left, margin.top - 6, state.view === "index" ? "Index" : "Population", "axis-label"));
      svg.appendChild(text(x(xMin), height - 7, String(xMin), "axis-label", "middle"));
      svg.appendChild(text(x(xMax), height - 7, String(xMax), "axis-label", "middle"));
      svg.appendChild(text(width - margin.right, height - 7, "Year", "axis-label", "end"));

      const chartPoints = row.series.map((d, index) => [x(d.year), y(values[index])]);
      svg.appendChild(path(chartPoints, color));
      row.series.forEach((d, index) => {{
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", x(d.year));
        circle.setAttribute("cy", y(values[index]));
        circle.setAttribute("r", "3");
        circle.setAttribute("fill", color);
        circle.setAttribute("class", "series-point");
        circle.appendChild(document.createElementNS("http://www.w3.org/2000/svg", "title")).textContent =
          `${{row.city}}\\n${{d.year}}: ${{number(d.value)}} people`;
        svg.appendChild(circle);
      }});
    }}

    function renderHousingPriceTrends() {{
      elements.housingPeriod.textContent = `${{state.startYear}}-${{state.endYear}}`;
      const housingEntry = housingByCity.get(state.housingCity);
      elements.housingChartTitle.textContent = housingEntry ? `${{housingEntry.city}} Housing Price Trends` : "Housing Price Trends";
      elements.housingSummaryBody.textContent = "";
      elements.housingStatsLegend.textContent = "";
      elements.housingPopulationLabel.textContent = "";
      elements.housingPopulationChart.textContent = "";
      elements.housingPriceChart.textContent = "";
      elements.housingYieldChart.textContent = "";
      elements.housingPriceRentChart.textContent = "";

      if (!housingPrices.length) {{
        elements.housingDataStatus.textContent = "No data loaded";
        elements.housingNote.textContent = `Add ${{metadata.housing_price_input}} with city, area, year, median_housing_price, mean_housing_price, and stddev_housing_price columns to enable this page.`;
        elements.housingCitySummary.innerHTML = `<div class="housing-empty">No neighborhood-level housing price data is currently loaded.</div>`;
        elements.housingSummaryBody.innerHTML = `<tr><td colspan="10">No housing price data loaded.</td></tr>`;
        drawEmptySvg(elements.housingPopulationChart, "No housing price data loaded");
        drawEmptySvg(elements.housingPriceChart, "No housing price data loaded");
        drawEmptySvg(elements.housingYieldChart, "No yield data loaded");
        drawEmptySvg(elements.housingPriceRentChart, "No price-to-rent data loaded");
        return;
      }}

      const selectableCities = Array.from(housingByCity.values())
        .filter(entry => populationKeyForHousingEntry(entry))
        .filter(entry => housingEntryPassesPopulationFilter(entry));
      elements.housingDataStatus.textContent = `${{selectableCities.length.toLocaleString()}} cities`;
      const cityData = selectedHousingCityData();

      if (!cityData || !cityData.populationSeries.length) {{
        elements.housingCitySummary.innerHTML = `<div class="housing-empty">Select a city with population and housing price data.</div>`;
        elements.housingSummaryBody.innerHTML = `<tr><td colspan="10">No matching population data for this selected city.</td></tr>`;
        drawEmptySvg(elements.housingPopulationChart, "No matching population data");
        drawEmptySvg(elements.housingPriceChart, "No matching housing data");
        drawEmptySvg(elements.housingYieldChart, "No matching yield data");
        drawEmptySvg(elements.housingPriceRentChart, "No matching price-to-rent data");
        return;
      }}

      elements.housingNote.textContent = `Selected city: ${{cityData.city}}. The city selector controls every chart and row. ${{cityData.availabilityNote}} Coverage: ${{cityData.coverageSummary}}. Source: ${{cityData.sourceSummary}}.`;
      renderHousingCitySummary(cityData);
      renderHousingPopulationChart(elements.housingPopulationChart, cityData);
      renderHousingStatsChart(elements.housingPriceChart, cityData.yearlyRows);
      renderHousingYieldTrendCharts(cityData.yearlyRows);
      renderHousingYearlyTable(cityData.yearlyRows);
    }}

    function selectedHousingCityData() {{
      if (!state.housingCity || !housingByCity.has(state.housingCity)) return null;
      const housingEntry = housingByCity.get(state.housingCity);
      const populationKey = populationKeyForHousingEntry(housingEntry);
      const populationEntry = byCity.get(populationKey);
      const populationSeries = (populationEntry?.series || [])
        .filter(d => d.year >= state.startYear && d.year <= state.endYear);
      const housingStatsByYear = aggregateHousingStatsByYear(state.housingCity);
      const marketRentByYear = metricByYear(populationKey, "asking_rent_eur_per_m2");
      const housingRows = Array.from(housingEntry.areas.values()).flat();
      const yearlyRows = [];
      let previousPopulation = null;
      let previousPurchase = null;
      let previousRent = null;
      for (let year = state.startYear; year <= state.endYear; year += 1) {{
        const population = populationSeries.find(d => d.year === year)?.value ?? null;
        const stats = housingStatsByYear.get(year) || null;
        const purchaseMedian = stats?.purchaseMedian ?? null;
        const rentMedian = marketRentByYear.get(year)?.value ?? stats?.rentMedian ?? null;
        const yieldMetrics = computeYieldMetrics(purchaseMedian, rentMedian);
        const populationYoyChange = previousPopulation != null && population != null ? population - previousPopulation : null;
        const purchaseYoyChange = previousPurchase != null && purchaseMedian != null ? purchaseMedian - previousPurchase : null;
        const rentYoyChange = previousRent != null && rentMedian != null ? rentMedian - previousRent : null;
        yearlyRows.push({{
          year,
          population,
          purchaseMedian,
          purchaseMean: stats?.purchaseMean ?? null,
          purchaseStddev: stats?.purchaseStddev ?? null,
          rentMedian,
          rentMean: stats?.rentMean ?? rentMedian,
          rentStddev: stats?.rentStddev ?? null,
          grossRentalYieldPct: yieldMetrics?.grossRentalYieldPct ?? null,
          priceToRentRatio: yieldMetrics?.priceToRentRatio ?? null,
          recordCount: Math.max(stats?.purchaseRecordCount ?? 0, stats?.rentRecordCount ?? 0, marketRentByYear.has(year) ? 1 : 0),
          populationYoyChange,
          populationYoy: yoy(population, previousPopulation),
          purchaseYoyChange,
          purchaseYoy: yoy(purchaseMedian, previousPurchase),
          rentYoyChange,
          rentYoy: yoy(rentMedian, previousRent)
        }});
        previousPopulation = population ?? null;
        previousPurchase = purchaseMedian ?? null;
        previousRent = rentMedian ?? null;
      }}
      const expectedYears = state.endYear - state.startYear + 1;
      const completeHousingYears = yearlyRows.filter(row => row.recordCount > 0).length;
      const maxRecordCount = Math.max(0, ...yearlyRows.map(row => row.recordCount));
      const startRow = yearlyRows.find(row => row.year === state.startYear) || null;
      const endRow = yearlyRows.find(row => row.year === state.endYear) || null;
      const hasPurchase = yearlyRows.some(row => row.purchaseMedian != null);
      const hasRent = yearlyRows.some(row => row.rentMedian != null);
      return {{
        city: housingEntry.city,
        city_id: housingEntry.city_id,
        populationCity: populationEntry?.city || "",
        populationSeries,
        yearlyRows,
        quality: dataQuality(Math.min(populationSeries.length, completeHousingYears), expectedYears, maxRecordCount),
        populationGrowth: growthMetrics(startRow?.population ?? null, endRow?.population ?? null, state.endYear - state.startYear),
        medianPriceGrowth: growthMetrics(startRow?.purchaseMedian ?? null, endRow?.purchaseMedian ?? null, state.endYear - state.startYear),
        rentGrowth: growthMetrics(startRow?.rentMedian ?? null, endRow?.rentMedian ?? null, state.endYear - state.startYear),
        areaCount: housingEntry.areas.size,
        housingRecordCount: housingRows.length,
        hasPurchase,
        hasRent,
        availabilityNote: housingAvailabilityNote(hasPurchase, hasRent),
        priceBasisSummary: summarizeDistinct(housingRows.map(row => row.price_basis || "Housing signal")),
        coverageSummary: summarizeDistinct(housingRows.map(row => row.coverage_level || "area")),
        sourceSummary: summarizeDistinct(housingRows.map(row => row.source || "loaded housing data"))
      }};
    }}

    function aggregateHousingStatsByYear(city) {{
      return aggregateHousingStatsByYearForEntry(housingByCity.get(city));
    }}

    function aggregateHousingStatsByYearForEntry(entry) {{
      const result = new Map();
      if (!entry) return result;
      const cityAreas = entry.areas;
      const byYear = new Map();
      cityAreas.forEach(series => {{
        series.forEach(row => {{
          if (row.year < state.startYear || row.year > state.endYear) return;
          if (!byYear.has(row.year)) {{
            byYear.set(row.year, {{
              purchaseMedianValues: [],
              purchaseMeanValues: [],
              rentMedianValues: [],
              rentMeanValues: [],
              coverageLevels: new Set(),
              sourceAreas: new Set(),
              sources: new Set()
            }});
          }}
          const bucket = byYear.get(row.year);
          bucket.coverageLevels.add(row.coverage_level || "unknown");
          bucket.sourceAreas.add(row.source_area || row.area || "unknown");
          bucket.sources.add(row.source || "loaded housing data");
          if (isRentBasis(row.price_basis)) {{
            if (row.median_housing_price != null) bucket.rentMedianValues.push(row.median_housing_price);
            if (row.mean_housing_price != null) bucket.rentMeanValues.push(row.mean_housing_price);
          }} else if (isPurchaseBasis(row.price_basis)) {{
            if (row.median_housing_price != null) bucket.purchaseMedianValues.push(row.median_housing_price);
            if (row.mean_housing_price != null) bucket.purchaseMeanValues.push(row.mean_housing_price);
          }}
        }});
      }});

      byYear.forEach((bucket, year) => {{
        const purchaseMedianValues = bucket.purchaseMedianValues.slice().sort((a, b) => a - b);
        const purchaseMeanValues = bucket.purchaseMeanValues;
        const rentMedianValues = bucket.rentMedianValues.slice().sort((a, b) => a - b);
        const rentMeanValues = bucket.rentMeanValues;
        if (!purchaseMedianValues.length && !purchaseMeanValues.length && !rentMedianValues.length && !rentMeanValues.length) return;
        const purchaseMedian = purchaseMedianValues.length ? median(purchaseMedianValues) : null;
        const rentMedian = rentMedianValues.length ? median(rentMedianValues) : null;
        const yieldMetrics = computeYieldMetrics(purchaseMedian, rentMedian);
        result.set(year, {{
          purchaseMedian,
          purchaseMean: purchaseMeanValues.length ? mean(purchaseMeanValues) : null,
          purchaseStddev: purchaseMedianValues.length ? standardDeviation(purchaseMedianValues) : null,
          purchaseRecordCount: Math.max(purchaseMedianValues.length, purchaseMeanValues.length),
          rentMedian,
          rentMean: rentMeanValues.length ? mean(rentMeanValues) : null,
          rentStddev: rentMedianValues.length ? standardDeviation(rentMedianValues) : null,
          rentRecordCount: Math.max(rentMedianValues.length, rentMeanValues.length),
          grossRentalYieldPct: yieldMetrics?.grossRentalYieldPct ?? null,
          priceToRentRatio: yieldMetrics?.priceToRentRatio ?? null,
          coverageSummary: summarizeDistinct(Array.from(bucket.coverageLevels)),
          sourceAreaSummary: summarizeDistinct(Array.from(bucket.sourceAreas)),
          sourceSummary: summarizeDistinct(Array.from(bucket.sources))
        }});
      }});
      return result;
    }}

    function isRentBasis(priceBasis) {{
      return String(priceBasis || "").toLowerCase().includes("rent");
    }}

    function isPurchaseBasis(priceBasis) {{
      return !isRentBasis(priceBasis);
    }}

    function housingAvailabilityNote(hasPurchase, hasRent) {{
      if (hasPurchase && hasRent) {{
        return "Purchase-price and asking-rent signals are both available, so gross yield can be computed where years overlap.";
      }}
      if (hasRent && !hasPurchase) {{
        return "This municipality has asking-rent fallback data but no purchase-price series, so gross yield cannot be computed.";
      }}
      if (hasPurchase && !hasRent) {{
        return "This municipality has purchase-price data but no rent series, so gross yield cannot be computed.";
      }}
      return "No purchase-price or asking-rent series is available for the selected period.";
    }}

    function renderHousingCitySummary(cityData) {{
      const latestPopulation = lastValue(cityData.yearlyRows.map(row => row.population));
      const latestPurchase = lastValue(cityData.yearlyRows.map(row => row.purchaseMedian));
      const latestRent = lastValue(cityData.yearlyRows.map(row => row.rentMedian));
      const latestYield = lastValue(cityData.yearlyRows.map(row => row.grossRentalYieldPct));
      const housingYears = cityData.yearlyRows.filter(row => row.recordCount > 0).map(row => row.year);
      const housingYearLabel = housingYears.length ? `${{Math.min(...housingYears)}}-${{Math.max(...housingYears)}}` : "No housing years";
      elements.housingPopulationLabel.textContent = cityData.populationCity || "";
      elements.housingCitySummary.innerHTML = `
        <div>
          <div class="housing-selected-city">${{escapeHtml(cityData.city)}}</div>
          <div class="housing-summary-note">This city controls every chart and row on this page. Data quality: ${{qualityBadge(cityData.quality)}}</div>
        </div>
        <div class="housing-metrics">
          <div class="housing-metric">
            <div class="housing-metric-value">${{latestPopulation == null ? "--" : number(latestPopulation)}}</div>
            <div class="housing-metric-label">Latest population in range</div>
          </div>
          <div class="housing-metric">
            <div class="housing-metric-value">${{formatGrowthSummary(cityData.populationGrowth, "population")}}</div>
            <div class="housing-metric-label">Population change over selected period</div>
          </div>
          <div class="housing-metric">
            <div class="housing-metric-value">${{latestPurchase == null ? "Unavailable" : money(latestPurchase)}}</div>
            <div class="housing-metric-label">Latest purchase-price signal EUR/m2</div>
          </div>
          <div class="housing-metric">
            <div class="housing-metric-value">${{formatGrowthSummary(cityData.medianPriceGrowth, "money")}}</div>
            <div class="housing-metric-label">Purchase-price change over selected period</div>
          </div>
          <div class="housing-metric">
            <div class="housing-metric-value">${{latestRent == null ? "Unavailable" : money(latestRent)}}</div>
            <div class="housing-metric-label">Latest asking rent EUR/m2/month</div>
          </div>
          <div class="housing-metric">
            <div class="housing-metric-value">${{formatAnnualGrowthSummary(cityData.rentGrowth, "money")}}</div>
            <div class="housing-metric-label">Estimated asking-rent YoY</div>
          </div>
          <div class="housing-metric">
            <div class="housing-metric-value">${{latestYield == null ? "Unavailable" : signedPercent(latestYield).replace("+", "")}}</div>
            <div class="housing-metric-label">Latest gross rental yield</div>
          </div>
          <div class="housing-metric">
            <div class="housing-metric-value">${{cityData.areaCount.toLocaleString()}}</div>
            <div class="housing-metric-label">Price series in source</div>
          </div>
          <div class="housing-metric">
            <div class="housing-metric-value">${{housingYearLabel}}</div>
            <div class="housing-metric-label">Housing years in selected range</div>
          </div>
        </div>
      `;
    }}

    function renderHousingPopulationChart(svg, cityData) {{
      const series = cityData.populationSeries.map(d => ({{ year: d.year, value: d.value }}));
      if (!series.length) {{
        drawEmptySvg(svg, "No population data for this period");
        return;
      }}
      const frame = svg.parentElement;
      const frameRect = frame.getBoundingClientRect();
      const width = Math.max(420, Math.floor(frameRect.width || svg.clientWidth || 760));
      const height = Math.max(170, Math.floor(frameRect.height || svg.clientHeight || 250));
      const margin = {{ top: 18, right: 28, bottom: 32, left: 78 }};
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      const yExtent = extent(series.map(d => d.value));
      const yPad = (yExtent[1] - yExtent[0]) * 0.08 || Math.max(1, yExtent[0] * 0.01);
      const yMin = Math.max(0, yExtent[0] - yPad);
      const yMax = yExtent[1] + yPad;
      const xMin = state.startYear;
      const xMax = state.endYear;
      const x = year => margin.left + ((year - xMin) / (xMax - xMin || 1)) * plotWidth;
      const y = value => margin.top + (1 - ((value - yMin) / (yMax - yMin || 1))) * plotHeight;

      svg.setAttribute("width", width);
      svg.setAttribute("height", height);
      svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
      svg.textContent = "";

      ticks(yMin, yMax, 4).forEach(tick => {{
        svg.appendChild(line(margin.left, y(tick), width - margin.right, y(tick), "grid-line"));
        svg.appendChild(text(margin.left - 10, y(tick) + 4, compact(tick), "axis-label", "end"));
      }});
      renderYearTicks(svg, x, height, margin);
      svg.appendChild(line(margin.left, margin.top, margin.left, height - margin.bottom, "axis"));
      svg.appendChild(line(margin.left, height - margin.bottom, width - margin.right, height - margin.bottom, "axis"));
      svg.appendChild(text(margin.left, margin.top - 6, "Population", "axis-label"));
      svg.appendChild(text(width - margin.right, height - 6, "Year", "axis-label", "end"));

      const color = colors[0];
      svg.appendChild(path(series.map(d => [x(d.year), y(d.value)]), color));
      series.forEach(d => {{
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", x(d.year));
        circle.setAttribute("cy", y(d.value));
        circle.setAttribute("r", "3.5");
        circle.setAttribute("fill", color);
        circle.setAttribute("class", "series-point");
        circle.appendChild(document.createElementNS("http://www.w3.org/2000/svg", "title")).textContent =
          `${{cityData.city}}\\n${{d.year}}: ${{number(d.value)}} people`;
        svg.appendChild(circle);
      }});
    }}

    function renderHousingStatsChart(svg, rows) {{
      const hasPurchase = rows.some(row => row.purchaseMedian != null || row.purchaseMean != null);
      const seriesSpec = hasPurchase ? [
        {{ key: "purchaseMedian", label: "Purchase median", color: colors[0] }},
        {{ key: "purchaseMean", label: "Purchase mean", color: colors[1] }},
        {{ key: "purchaseStddev", label: "Purchase std dev", color: colors[2] }}
      ] : [
        {{ key: "rentMedian", label: "Asking rent median", color: colors[0] }},
        {{ key: "rentMean", label: "Asking rent mean", color: colors[1] }},
        {{ key: "rentStddev", label: "Asking rent std dev", color: colors[2] }}
      ];
      const series = seriesSpec.map(item => ({{
        ...item,
        points: rows.filter(row => row[item.key] != null).map(row => ({{ year: row.year, value: row[item.key] }}))
      }}));
      const values = series.flatMap(item => item.points.map(point => point.value));
      if (!values.length) {{
        drawEmptySvg(svg, "No purchase-price or rent data for this period");
        renderHousingStatsLegend([]);
        return;
      }}

      const frame = svg.parentElement;
      const frameRect = frame.getBoundingClientRect();
      const width = Math.max(420, Math.floor(frameRect.width || svg.clientWidth || 760));
      const height = Math.max(190, Math.floor(frameRect.height || svg.clientHeight || 260));
      const margin = {{ top: 18, right: 28, bottom: 32, left: 78 }};
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      const yExtent = extent(values);
      const yPad = (yExtent[1] - yExtent[0]) * 0.08 || Math.max(1, yExtent[0] * 0.05);
      const yMin = Math.max(0, yExtent[0] - yPad);
      const yMax = yExtent[1] + yPad;
      const xMin = state.startYear;
      const xMax = state.endYear;
      const x = year => margin.left + ((year - xMin) / (xMax - xMin || 1)) * plotWidth;
      const y = value => margin.top + (1 - ((value - yMin) / (yMax - yMin || 1))) * plotHeight;

      svg.setAttribute("width", width);
      svg.setAttribute("height", height);
      svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
      svg.textContent = "";

      ticks(yMin, yMax, 4).forEach(tick => {{
        svg.appendChild(line(margin.left, y(tick), width - margin.right, y(tick), "grid-line"));
        svg.appendChild(text(margin.left - 10, y(tick) + 4, money(tick), "axis-label", "end"));
      }});
      renderYearTicks(svg, x, height, margin);
      svg.appendChild(line(margin.left, margin.top, margin.left, height - margin.bottom, "axis"));
      svg.appendChild(line(margin.left, height - margin.bottom, width - margin.right, height - margin.bottom, "axis"));
      svg.appendChild(text(margin.left, margin.top - 6, hasPurchase ? "Purchase EUR/m2" : "Rent EUR/m2/month", "axis-label"));
      svg.appendChild(text(width - margin.right, height - 6, "Year", "axis-label", "end"));

      series.forEach(item => {{
        if (!item.points.length) return;
        const chartPoints = item.points.map(d => [x(d.year), y(d.value)]);
        svg.appendChild(path(chartPoints, item.color));
        item.points.forEach(d => {{
          const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
          circle.setAttribute("cx", x(d.year));
          circle.setAttribute("cy", y(d.value));
          circle.setAttribute("r", "3.5");
          circle.setAttribute("fill", item.color);
          circle.setAttribute("class", "series-point");
          circle.appendChild(document.createElementNS("http://www.w3.org/2000/svg", "title")).textContent =
            `${{housingCityLabel()}} ${{item.label}}\\n${{d.year}}: ${{money(d.value)}}`;
          svg.appendChild(circle);
        }});
      }});

      renderHousingStatsLegend(series);
    }}

    function renderHousingYieldTrendCharts(rows) {{
      renderHousingSingleMetricChart(elements.housingYieldChart, rows, {{
        key: "grossRentalYieldPct",
        label: "Gross rental yield",
        axisLabel: "Yield %",
        color: colors[3],
        emptyMessage: "Unavailable: purchase + rent years do not overlap",
        valueFormatter: value => signedPercent(value).replace("+", ""),
        tickFormatter: value => `${{numberDecimal(value, 1)}}%`
      }});
      renderHousingSingleMetricChart(elements.housingPriceRentChart, rows, {{
        key: "priceToRentRatio",
        label: "Price-to-rent ratio",
        axisLabel: "Ratio",
        color: colors[4],
        emptyMessage: "Unavailable: purchase + rent years do not overlap",
        valueFormatter: value => numberDecimal(value, 1),
        tickFormatter: value => numberDecimal(value, 1)
      }});
    }}

    function renderHousingSingleMetricChart(svg, rows, config) {{
      const points = rows
        .filter(row => row[config.key] != null && Number.isFinite(row[config.key]))
        .map(row => ({{ year: row.year, value: row[config.key] }}));
      if (!points.length) {{
        drawEmptySvg(svg, config.emptyMessage);
        return;
      }}

      const frame = svg.parentElement;
      const frameRect = frame.getBoundingClientRect();
      const width = Math.max(260, Math.floor(frameRect.width || svg.clientWidth || 360));
      const height = Math.max(150, Math.floor(frameRect.height || svg.clientHeight || 180));
      const margin = {{ top: 18, right: 18, bottom: 30, left: 58 }};
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      const yExtent = extent(points.map(d => d.value));
      const yPad = (yExtent[1] - yExtent[0]) * 0.12 || Math.max(0.5, Math.abs(yExtent[0]) * 0.08);
      const yMin = Math.max(0, yExtent[0] - yPad);
      const yMax = yExtent[1] + yPad;
      const xMin = state.startYear;
      const xMax = state.endYear;
      const x = year => margin.left + ((year - xMin) / (xMax - xMin || 1)) * plotWidth;
      const y = value => margin.top + (1 - ((value - yMin) / (yMax - yMin || 1))) * plotHeight;

      svg.setAttribute("width", width);
      svg.setAttribute("height", height);
      svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
      svg.textContent = "";

      ticks(yMin, yMax, 4).forEach(tick => {{
        svg.appendChild(line(margin.left, y(tick), width - margin.right, y(tick), "grid-line"));
        svg.appendChild(text(margin.left - 8, y(tick) + 4, config.tickFormatter(tick), "axis-label", "end"));
      }});
      renderYearTicks(svg, x, height, margin);
      svg.appendChild(line(margin.left, margin.top, margin.left, height - margin.bottom, "axis"));
      svg.appendChild(line(margin.left, height - margin.bottom, width - margin.right, height - margin.bottom, "axis"));
      svg.appendChild(text(margin.left, margin.top - 6, config.axisLabel, "axis-label"));
      svg.appendChild(text(width - margin.right, height - 6, "Year", "axis-label", "end"));

      svg.appendChild(path(points.map(d => [x(d.year), y(d.value)]), config.color));
      points.forEach(d => {{
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", x(d.year));
        circle.setAttribute("cy", y(d.value));
        circle.setAttribute("r", "3.5");
        circle.setAttribute("fill", config.color);
        circle.setAttribute("class", "series-point");
        circle.appendChild(document.createElementNS("http://www.w3.org/2000/svg", "title")).textContent =
          `${{housingCityLabel()}} ${{config.label}}\\n${{d.year}}: ${{config.valueFormatter(d.value)}}`;
        svg.appendChild(circle);
      }});
    }}

    function renderYearTicks(svg, x, height, margin) {{
      const xTicks = years.filter(year => year >= state.startYear && year <= state.endYear && (year === state.startYear || year === state.endYear || year % 2 === 0));
      xTicks.forEach(tick => svg.appendChild(text(x(tick), height - margin.bottom + 22, String(tick), "axis-label", "middle")));
    }}

    function renderHousingStatsLegend(series) {{
      elements.housingStatsLegend.textContent = "";
      const fragment = document.createDocumentFragment();
      series.forEach(item => {{
        const legend = document.createElement("div");
        legend.className = "legend-item";
        legend.innerHTML = `<span class="swatch" style="background:${{item.color}}"></span><span>${{escapeHtml(item.label)}}</span>`;
        fragment.appendChild(legend);
      }});
      elements.housingStatsLegend.appendChild(fragment);
    }}

    function renderHousingYearlyTable(rows) {{
      elements.housingSummaryBody.textContent = "";
      const fragment = document.createDocumentFragment();
      rows.forEach(row => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${{row.year}}</td>
          <td>${{row.population == null ? "--" : number(row.population)}}</td>
          <td>${{row.populationYoyChange == null ? "--" : signedNumber(row.populationYoyChange)}}</td>
          <td>${{row.populationYoy == null ? "--" : signedPercent(row.populationYoy)}}</td>
          <td>${{row.purchaseMedian == null ? "Unavailable" : money(row.purchaseMedian)}}</td>
          <td>${{row.rentMedian == null ? "Unavailable" : money(row.rentMedian)}}</td>
          <td>${{row.grossRentalYieldPct == null ? "Unavailable" : signedPercent(row.grossRentalYieldPct).replace("+", "")}}</td>
          <td>${{row.priceToRentRatio == null ? "Unavailable" : numberDecimal(row.priceToRentRatio, 1)}}</td>
          <td>${{row.purchaseYoy == null ? "Unavailable" : signedPercent(row.purchaseYoy)}}</td>
          <td>${{row.rentYoy == null ? "Unavailable" : signedPercent(row.rentYoy)}}</td>
        `;
        fragment.appendChild(tr);
      }});
      elements.housingSummaryBody.appendChild(fragment);
    }}

    function drawEmptySvg(svg, message) {{
      const frame = svg.parentElement;
      const frameRect = frame.getBoundingClientRect();
      const width = Math.max(360, Math.floor(frameRect.width || 720));
      const height = Math.max(260, Math.floor(frameRect.height || 360));
      svg.setAttribute("width", width);
      svg.setAttribute("height", height);
      svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
      svg.textContent = "";
      svg.appendChild(text(width / 2, height / 2, message, "empty"));
    }}

    function renderLegend(rows) {{
      elements.legend.textContent = "";
      rows.forEach((row, index) => {{
        const item = document.createElement("div");
        item.className = "legend-item";
        item.innerHTML = `<span class="swatch" style="background:${{colors[index % colors.length]}}"></span><span class="city-name">${{escapeHtml(row.city)}}</span>`;
        elements.legend.appendChild(item);
      }});
    }}

    function line(x1, y1, x2, y2, className) {{
      const item = document.createElementNS("http://www.w3.org/2000/svg", "line");
      item.setAttribute("x1", x1);
      item.setAttribute("y1", y1);
      item.setAttribute("x2", x2);
      item.setAttribute("y2", y2);
      item.setAttribute("class", className);
      return item;
    }}

    function path(points, color) {{
      const item = document.createElementNS("http://www.w3.org/2000/svg", "path");
      item.setAttribute("d", points.map((point, index) => `${{index === 0 ? "M" : "L"}}${{point[0].toFixed(2)}},${{point[1].toFixed(2)}}`).join(" "));
      item.setAttribute("stroke", color);
      item.setAttribute("class", "series-line");
      return item;
    }}

    function text(x, y, value, className, anchor) {{
      const item = document.createElementNS("http://www.w3.org/2000/svg", "text");
      item.setAttribute("x", x);
      item.setAttribute("y", y);
      item.setAttribute("class", className);
      if (anchor) item.setAttribute("text-anchor", anchor);
      item.textContent = value;
      return item;
    }}

    function extent(values) {{
      return [Math.min(...values), Math.max(...values)];
    }}

    function ticks(min, max, count) {{
      if (min === max) return [min];
      const step = niceStep((max - min) / Math.max(1, count - 1));
      const start = Math.ceil(min / step) * step;
      const result = [];
      for (let value = start; value <= max + step * 0.5; value += step) {{
        result.push(value);
      }}
      return result;
    }}

    function niceStep(raw) {{
      const power = Math.pow(10, Math.floor(Math.log10(raw)));
      const scaled = raw / power;
      if (scaled <= 1) return power;
      if (scaled <= 2) return 2 * power;
      if (scaled <= 5) return 5 * power;
      return 10 * power;
    }}

    function median(values) {{
      const mid = Math.floor(values.length / 2);
      return values.length % 2 ? values[mid] : (values[mid - 1] + values[mid]) / 2;
    }}

    function mean(values) {{
      return values.reduce((sum, value) => sum + value, 0) / values.length;
    }}

    function standardDeviation(values) {{
      if (!values.length) return null;
      const average = mean(values);
      return Math.sqrt(mean(values.map(value => Math.pow(value - average, 2))));
    }}

    function yoy(value, previous) {{
      if (previous == null || previous <= 0 || value == null) return null;
      return ((value - previous) / previous) * 100;
    }}

    function lastValue(values) {{
      for (let index = values.length - 1; index >= 0; index -= 1) {{
        if (values[index] != null) return values[index];
      }}
      return null;
    }}

    function populationPlaceKey(row) {{
      return row.city_id ? `id:${{row.city_id}}` : `name:${{cityKey(row.city)}}`;
    }}

    function housingPlaceKey(row) {{
      return row.city_id ? `id:${{row.city_id}}` : `name:${{cityKey(row.city)}}`;
    }}

    function populationKeyForHousingEntry(entry) {{
      if (!entry) return null;
      if (entry.city_id && populationCityById.has(entry.city_id)) {{
        return populationCityById.get(entry.city_id);
      }}
      return populationCityByNameKey.get(cityKey(entry.city)) || null;
    }}

    function housingCityLabel() {{
      return housingByCity.get(state.housingCity)?.city || "";
    }}

    function cityKey(value) {{
      return String(value).split(",")[0].trim().toLocaleLowerCase("de-DE");
    }}

    function summarizeDistinct(values) {{
      const unique = Array.from(new Set(values.filter(Boolean)));
      if (!unique.length) return "unknown";
      if (unique.length <= 2) return unique.join(" + ");
      return `${{unique.slice(0, 2).join(" + ")}} + ${{unique.length - 2}} more`;
    }}

    function clamp(value, min, max) {{
      return Math.max(min, Math.min(max, value));
    }}

    function scoreText(value, missingLabel = "Unavailable") {{
      return value == null || !Number.isFinite(value) ? missingLabel : numberDecimal(value, 1);
    }}

    function formatGrowthSummary(metrics, kind) {{
      if (!metrics || !metrics.valid) return "Insufficient data";
      const absolute = kind === "money" ? signedMoney(metrics.absChange) : signedNumber(metrics.absChange);
      return `${{absolute}} (${{signedPercent(metrics.pctChange)}}, ${{signedPercent(metrics.cagr)}} CAGR)`;
    }}

    function formatAnnualGrowthSummary(metrics, kind) {{
      if (!metrics || !metrics.valid) return "Insufficient data";
      const yearsElapsed = Math.max(1, state.endYear - state.startYear);
      const annualChange = metrics.annualChange ?? metrics.absChange / yearsElapsed;
      const absolute = kind === "money" ? signedMoney(annualChange) : signedNumber(annualChange);
      return `${{absolute}}/yr (${{signedPercent(metrics.cagr)}})`;
    }}

    function formatPriceYoY(row) {{
      if (row.medianPriceCagr == null || row.medianPriceAnnualChange == null) return "--";
      return `${{signedMoney(row.medianPriceAnnualChange)}}/yr (${{signedPercent(row.medianPriceCagr)}})`;
    }}

    function formatSignalYoY(row) {{
      if (row.signalCagr == null || row.signalAnnualChange == null) return "--";
      return `${{signedMoney(row.signalAnnualChange)}}/yr (${{signedPercent(row.signalCagr)}})`;
    }}

    function priceYoYTitle(row) {{
      if (row.medianPriceCagr == null || row.medianPriceAnnualChange == null) {{
        return "Insufficient housing price data for the selected years.";
      }}
      return [
        `Estimated annualized median housing price change: ${{signedMoney(row.medianPriceAnnualChange)}} per m2 per year`,
        `Annualized YoY: ${{signedPercent(row.medianPriceCagr)}}`,
        `Total selected-period median price change: ${{signedPercent(row.medianPriceGrowth)}}`
      ].join(". ");
    }}

    function signalYoYTitle(row) {{
      if (row.signalCagr == null || row.signalAnnualChange == null) {{
        return "Insufficient signal data for the selected years.";
      }}
      return [
        `${{row.signalBasis}} signal`,
        `Estimated annualized change: ${{signedMoney(row.signalAnnualChange)}} per m2 per year`,
        `Annualized YoY: ${{signedPercent(row.signalCagr)}}`,
        `Total selected-period change: ${{signedPercent(row.signalGrowth)}}`
      ].join(". ");
    }}

    function percent(value) {{
      return `${{value.toFixed(2)}}%`;
    }}

    function signedPercent(value) {{
      if (value == null || !Number.isFinite(value)) return "--";
      const sign = value > 0 ? "+" : "";
      return `${{sign}}${{value.toFixed(2)}}%`;
    }}

    function number(value) {{
      return Math.round(value).toLocaleString();
    }}

    function numberDecimal(value, digits = 1) {{
      if (value == null || !Number.isFinite(value)) return "--";
      return Number(value).toLocaleString("en", {{
        minimumFractionDigits: 0,
        maximumFractionDigits: digits
      }});
    }}

    function signedNumber(value) {{
      if (value == null || !Number.isFinite(value)) return "--";
      const rounded = Math.round(value);
      const sign = rounded > 0 ? "+" : "";
      return `${{sign}}${{rounded.toLocaleString()}}`;
    }}

    function compact(value) {{
      return Intl.NumberFormat("en", {{ notation: "compact", maximumFractionDigits: 1 }}).format(value);
    }}

    function money(value) {{
      const formatted = Intl.NumberFormat("en", {{
        maximumFractionDigits: 0
      }}).format(Math.abs(value));
      return `${{value < 0 ? "-€" : "€"}}${{formatted}}`;
    }}

    function signedMoney(value) {{
      if (value == null || !Number.isFinite(value)) return "--";
      return `${{value > 0 ? "+" : ""}}${{money(value)}}`;
    }}

    function stableId(value) {{
      return String(value).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    }}

    function escapeHtml(value) {{
      return String(value).replace(/[&<>"']/g, char => ({{
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }}[char]));
    }}

    function escapeAttribute(value) {{
      return escapeHtml(value).replace(/"/g, "&quot;");
    }}

    window.addEventListener("resize", render);
    init();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
