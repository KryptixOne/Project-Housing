import csv
import json
from pathlib import Path


INPUT_PATH = Path("data/real/inkar_2025_municipality_population_observations.csv")
HOUSING_PRICE_INPUT_PATH = Path("data/real/neighborhood_housing_prices.csv")
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
            "housing_price_loaded": bool(housing_prices),
        },
        "housing_prices": housing_prices,
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
      grid-template-columns: minmax(170px, 1.2fr) repeat(9, minmax(90px, auto));
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
      min-height: 780px;
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
      grid-template-rows: minmax(170px, 1fr) minmax(190px, 1.05fr) minmax(170px, 0.85fr);
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

    .opportunity-table td:first-child {{
      max-width: 170px;
    }}

    .opportunity-chart-panel {{
      grid-template-rows: auto auto minmax(0, 1fr) auto;
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
      <button id="opportunityTab" type="button" class="tab-button" data-tab="opportunity">Growth Price Signals</button>
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
          Screens cities with rising population and stable or decreasing median housing-price YoY over the selected years. Decreasing prices are highlighted separately. Treat this as a signal for investigation, not a valuation model.
        </div>
        <div class="opportunity-controls">
          <label>
            Min pop. CAGR %
            <input id="opportunityMinGrowth" type="number" step="0.1" value="0" inputmode="decimal">
          </label>
          <label>
            Max price YoY %
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
                <th>Start median</th>
                <th>End median</th>
                <th>Price YoY</th>
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
          <div class="housing-summary-wrap">
            <table class="housing-summary-table">
              <thead>
                <tr>
                  <th>Year</th>
                  <th>Population</th>
                  <th>Pop YoY change</th>
                  <th>Pop YoY %</th>
                  <th>Median price</th>
                  <th>Mean price</th>
                  <th>Std dev</th>
                  <th>Median YoY change</th>
                  <th>Median YoY %</th>
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
    const metadata = payload.metadata;
    const colors = ["#3168a6", "#3e7b4f", "#bc6c25", "#7057a3", "#207c7c", "#a64035", "#6f6a5f"];
    const stablePriceYoYThreshold = 1.0;

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
      housingTab: document.getElementById("housingTab"),
      populationPage: document.getElementById("populationPage"),
      classificationPage: document.getElementById("classificationPage"),
      opportunityPage: document.getElementById("opportunityPage"),
      housingPage: document.getElementById("housingPage"),
      search: document.getElementById("search"),
      startYear: document.getElementById("startYear"),
      endYear: document.getElementById("endYear"),
      sortMode: document.getElementById("sortMode"),
      populationBand: document.getElementById("populationBand"),
      minPopulation: document.getElementById("minPopulation"),
      maxPopulation: document.getElementById("maxPopulation"),
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
      opportunityPeriod: document.getElementById("opportunityPeriod"),
      opportunityChart: document.getElementById("opportunityChart"),
      opportunityLegend: document.getElementById("opportunityLegend"),
      opportunityTooltip: document.getElementById("opportunityTooltip"),
      opportunityMinGrowth: document.getElementById("opportunityMinGrowth"),
      opportunityMaxPriceGrowth: document.getElementById("opportunityMaxPriceGrowth"),
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

      [elements.populationTab, elements.classificationTab, elements.opportunityTab, elements.housingTab].forEach(button => {{
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
      const isHousing = state.activeTab === "housing";
      elements.populationTab.classList.toggle("active", isPopulation);
      elements.classificationTab.classList.toggle("active", isClassification);
      elements.opportunityTab.classList.toggle("active", isOpportunity);
      elements.housingTab.classList.toggle("active", isHousing);
      elements.populationPage.hidden = !isPopulation;
      elements.classificationPage.hidden = !isClassification;
      elements.opportunityPage.hidden = !isOpportunity;
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
        ["Trend view", state.view === "index" ? "Indexed values" : "Raw values"]
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
        ["Screen", `Population CAGR >= ${{signedPercent(state.opportunityMinGrowth)}} and price YoY <= ${{signedPercent(state.opportunityMaxPriceGrowth)}}`],
        ["Price signal", "Stable or decreasing median housing price"]
      ]);
      elements.housingActiveFilters.innerHTML = activeFilterMarkup([
        ...common,
        ["Selected city", housingCityLabel() || "None"],
        ["Housing metrics", "Median, mean, std dev"]
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
        "median-price-growth-desc": "Median housing price YoY"
      }};
      return labels[state.sortMode] || state.sortMode;
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
      const start = stats.get(state.startYear)?.median ?? null;
      const end = stats.get(state.endYear)?.median ?? null;
      const metrics = growthMetrics(start, end, state.endYear - state.startYear);
      if (!metrics.valid) return null;
      const expectedYears = state.endYear - state.startYear + 1;
      const availableYears = Array.from(stats.values()).filter(row => row.recordCount > 0).length;
      const maxRecordCount = Math.max(0, ...Array.from(stats.values()).map(row => row.recordCount));
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
      const allCandidates = opportunityRows(rankings);
      const filtered = allCandidates.filter(row => row.city.toLowerCase().includes(state.search));
      const visible = applyRowLimit(filtered);
      elements.opportunityPeriod.textContent = `${{state.startYear}}-${{state.endYear}}`;
      elements.opportunityCount.textContent = `${{filtered.length.toLocaleString()}} candidates`;
      renderOpportunitySummary(filtered);
      renderOpportunityTable(visible, filtered.length);
      renderOpportunityScatter(elements.opportunityChart, filtered.slice(0, 120));
      renderOpportunityLegend();
    }}

    function opportunityRows(rankings) {{
      return rankings
        .filter(row => row.cagr >= state.opportunityMinGrowth)
        .filter(row => row.medianPriceCagr != null && row.medianPriceCagr <= state.opportunityMaxPriceGrowth)
        .map(row => ({{
          ...row,
          opportunitySignal: row.medianPriceCagr < 0 ? "Growth + decreasing prices" : "Growth + stable prices",
          opportunityClass: row.medianPriceCagr < 0 ? "signal-decreasing" : "signal-stable",
          opportunitySpread: row.cagr - row.medianPriceCagr,
          opportunityQuality: combinedQuality(row.quality, row.medianPriceQuality)
        }}))
        .sort((a, b) =>
          b.opportunitySpread - a.opportunitySpread ||
          b.absChange - a.absChange ||
          a.city.localeCompare(b.city)
        );
    }}

    function renderOpportunitySummary(rows) {{
      const decreasing = rows.filter(row => row.medianPriceCagr < 0).length;
      const stable = rows.length - decreasing;
      const best = rows[0];
      const medianSpreadValues = rows.map(row => row.opportunitySpread).sort((a, b) => a - b);
      elements.opportunitySummary.innerHTML = `
        <div class="opportunity-stat">
          <div class="opportunity-stat-value">${{rows.length.toLocaleString()}}</div>
          <div class="opportunity-stat-label">Matching cities</div>
        </div>
        <div class="opportunity-stat">
          <div class="opportunity-stat-value">${{decreasing.toLocaleString()}}</div>
          <div class="opportunity-stat-label">With decreasing prices</div>
        </div>
        <div class="opportunity-stat">
          <div class="opportunity-stat-value">${{stable.toLocaleString()}}</div>
          <div class="opportunity-stat-label">With stable prices</div>
        </div>
        <div class="opportunity-stat">
          <div class="opportunity-stat-value" title="${{best ? escapeAttribute(best.city) : ""}}">${{medianSpreadValues.length ? signedPercent(median(medianSpreadValues)) : "--"}}</div>
          <div class="opportunity-stat-label">Median growth-price spread</div>
        </div>
      `;
    }}

    function renderOpportunityTable(rows, filteredCount) {{
      elements.opportunityBody.textContent = "";
      if (!rows.length) {{
        elements.opportunityBody.innerHTML = `<tr><td colspan="10">No cities match positive population growth with stable or decreasing median housing prices for the active filters.</td></tr>`;
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
          <td>${{row.medianPriceStart == null ? "--" : money(row.medianPriceStart)}}</td>
          <td>${{row.medianPriceEnd == null ? "--" : money(row.medianPriceEnd)}}</td>
          <td title="${{escapeAttribute(priceYoYTitle(row))}}">${{formatPriceYoY(row)}}</td>
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
      elements.opportunityCount.textContent = `${{rows.length.toLocaleString()}} of ${{filteredCount.toLocaleString()}} candidates`;
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
      const xValues = rows.map(row => row.medianPriceCagr);
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
      svg.appendChild(text(width - margin.right, height - 8, "Median housing price YoY", "axis-label", "end"));
      svg.appendChild(text(x(state.opportunityMaxPriceGrowth) + 4, margin.top + 12, `${{signedPercent(state.opportunityMaxPriceGrowth)}} price threshold`, "axis-label"));

      rows.forEach(row => {{
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", x(row.medianPriceCagr));
        circle.setAttribute("cy", y(row.cagr));
        circle.setAttribute("r", row.start > 1000000 ? "6.5" : row.start > 100000 ? "5.2" : "4.2");
        circle.setAttribute("fill", row.medianPriceCagr < 0 ? "var(--green)" : "var(--teal)");
        circle.setAttribute("opacity", "0.82");
        circle.setAttribute("class", "series-point");
        circle.setAttribute("tabindex", "0");
        circle.setAttribute("aria-label", `${{row.city}}. Population CAGR ${{signedPercent(row.cagr)}}. Median housing price YoY ${{signedPercent(row.medianPriceCagr)}}.`);
        circle.appendChild(document.createElementNS("http://www.w3.org/2000/svg", "title")).textContent =
          `${{row.city}}\\nPopulation CAGR: ${{signedPercent(row.cagr)}}\\nMedian price YoY: ${{signedPercent(row.medianPriceCagr)}}\\nSpread: ${{signedPercent(row.opportunitySpread)}}`;
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
        <div class="tooltip-row"><span>Median price YoY</span><b>${{signedPercent(row.medianPriceCagr)}}</b></div>
        <div class="tooltip-row"><span>Growth-price spread</span><b>${{signedPercent(row.opportunitySpread)}}</b></div>
        <div class="tooltip-row"><span>Start population</span><b>${{number(row.start)}}</b></div>
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
        <div class="legend-item"><span class="swatch" style="background:var(--green)"></span><span>Population growth + decreasing median price</span></div>
        <div class="legend-item"><span class="swatch" style="background:var(--teal)"></span><span>Population growth + stable median price</span></div>
      `;
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

      if (!housingPrices.length) {{
        elements.housingDataStatus.textContent = "No data loaded";
        elements.housingNote.textContent = `Add ${{metadata.housing_price_input}} with city, area, year, median_housing_price, mean_housing_price, and stddev_housing_price columns to enable this page.`;
        elements.housingCitySummary.innerHTML = `<div class="housing-empty">No neighborhood-level housing price data is currently loaded.</div>`;
        elements.housingSummaryBody.innerHTML = `<tr><td colspan="9">No housing price data loaded.</td></tr>`;
        drawEmptySvg(elements.housingPopulationChart, "No housing price data loaded");
        drawEmptySvg(elements.housingPriceChart, "No housing price data loaded");
        return;
      }}

      const selectableCities = Array.from(housingByCity.values())
        .filter(entry => populationKeyForHousingEntry(entry))
        .filter(entry => housingEntryPassesPopulationFilter(entry));
      elements.housingDataStatus.textContent = `${{selectableCities.length.toLocaleString()}} cities`;
      const cityData = selectedHousingCityData();

      if (!cityData || !cityData.populationSeries.length) {{
        elements.housingCitySummary.innerHTML = `<div class="housing-empty">Select a city with population and housing price data.</div>`;
        elements.housingSummaryBody.innerHTML = `<tr><td colspan="9">No matching population data for this selected city.</td></tr>`;
        drawEmptySvg(elements.housingPopulationChart, "No matching population data");
        drawEmptySvg(elements.housingPriceChart, "No matching housing data");
        return;
      }}

      elements.housingNote.textContent = `Selected city: ${{cityData.city}}. The city selector controls the population chart, housing-stat chart, and yearly table. Price basis: ${{cityData.priceBasisSummary}}. Coverage: ${{cityData.coverageSummary}}. Source: ${{cityData.sourceSummary}}.`;
      renderHousingCitySummary(cityData);
      renderHousingPopulationChart(elements.housingPopulationChart, cityData);
      renderHousingStatsChart(elements.housingPriceChart, cityData.yearlyRows);
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
      const housingRows = Array.from(housingEntry.areas.values()).flat();
      const yearlyRows = [];
      let previousPopulation = null;
      let previousMedian = null;
      for (let year = state.startYear; year <= state.endYear; year += 1) {{
        const population = populationSeries.find(d => d.year === year)?.value ?? null;
        const stats = housingStatsByYear.get(year) || null;
        const medianPrice = stats?.median ?? null;
        const populationYoyChange = previousPopulation != null && population != null ? population - previousPopulation : null;
        const medianPriceYoyChange = previousMedian != null && medianPrice != null ? medianPrice - previousMedian : null;
        yearlyRows.push({{
          year,
          population,
          medianPrice,
          meanPrice: stats?.mean ?? null,
          stddevPrice: stats?.stddev ?? null,
          recordCount: stats?.recordCount ?? 0,
          populationYoyChange,
          populationYoy: yoy(population, previousPopulation),
          medianPriceYoyChange,
          medianPriceYoy: yoy(medianPrice, previousMedian)
        }});
        previousPopulation = population ?? null;
        previousMedian = medianPrice ?? null;
      }}
      const expectedYears = state.endYear - state.startYear + 1;
      const completeHousingYears = yearlyRows.filter(row => row.recordCount > 0).length;
      const maxRecordCount = Math.max(0, ...yearlyRows.map(row => row.recordCount));
      const startRow = yearlyRows.find(row => row.year === state.startYear) || null;
      const endRow = yearlyRows.find(row => row.year === state.endYear) || null;
      return {{
        city: housingEntry.city,
        city_id: housingEntry.city_id,
        populationCity: populationEntry?.city || "",
        populationSeries,
        yearlyRows,
        quality: dataQuality(Math.min(populationSeries.length, completeHousingYears), expectedYears, maxRecordCount),
        populationGrowth: growthMetrics(startRow?.population ?? null, endRow?.population ?? null, state.endYear - state.startYear),
        medianPriceGrowth: growthMetrics(startRow?.medianPrice ?? null, endRow?.medianPrice ?? null, state.endYear - state.startYear),
        areaCount: housingEntry.areas.size,
        housingRecordCount: housingRows.length,
        priceBasisSummary: summarizeDistinct(housingRows.map(row => row.price_basis || "Housing price")),
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
          if (!byYear.has(row.year)) byYear.set(row.year, {{ medianValues: [], meanValues: [] }});
          const bucket = byYear.get(row.year);
          if (row.median_housing_price != null) bucket.medianValues.push(row.median_housing_price);
          if (row.mean_housing_price != null) bucket.meanValues.push(row.mean_housing_price);
        }});
      }});

      byYear.forEach((bucket, year) => {{
        const medianValues = bucket.medianValues.slice().sort((a, b) => a - b);
        const meanValues = bucket.meanValues;
        if (!medianValues.length && !meanValues.length) return;
        result.set(year, {{
          median: medianValues.length ? median(medianValues) : null,
          mean: meanValues.length ? mean(meanValues) : null,
          stddev: medianValues.length ? standardDeviation(medianValues) : null,
          recordCount: Math.max(medianValues.length, meanValues.length)
        }});
      }});
      return result;
    }}

    function renderHousingCitySummary(cityData) {{
      const latestPopulation = lastValue(cityData.yearlyRows.map(row => row.population));
      const latestMedian = lastValue(cityData.yearlyRows.map(row => row.medianPrice));
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
            <div class="housing-metric-value">${{latestMedian == null ? "--" : money(latestMedian)}}</div>
            <div class="housing-metric-label">Latest median value EUR/m2</div>
          </div>
          <div class="housing-metric">
            <div class="housing-metric-value">${{formatGrowthSummary(cityData.medianPriceGrowth, "money")}}</div>
            <div class="housing-metric-label">Median price change over selected period</div>
          </div>
          <div class="housing-metric">
            <div class="housing-metric-value">${{formatAnnualGrowthSummary(cityData.medianPriceGrowth, "money")}}</div>
            <div class="housing-metric-label">Estimated median price YoY</div>
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
      const series = [
        {{ key: "medianPrice", label: "Median", color: colors[0] }},
        {{ key: "meanPrice", label: "Mean", color: colors[1] }},
        {{ key: "stddevPrice", label: "Std dev", color: colors[2] }}
      ].map(item => ({{
        ...item,
        points: rows.filter(row => row[item.key] != null).map(row => ({{ year: row.year, value: row[item.key] }}))
      }}));
      const values = series.flatMap(item => item.points.map(point => point.value));
      if (!values.length) {{
        drawEmptySvg(svg, "No housing price data for this period");
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
      svg.appendChild(text(margin.left, margin.top - 6, "EUR/m2", "axis-label"));
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
            `${{housingCityLabel()}} ${{item.label}}\\n${{d.year}}: ${{money(d.value)}} EUR/m2`;
          svg.appendChild(circle);
        }});
      }});

      renderHousingStatsLegend(series);
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
          <td>${{row.medianPrice == null ? "--" : money(row.medianPrice)}}</td>
          <td>${{row.meanPrice == null ? "--" : money(row.meanPrice)}}</td>
          <td>${{row.stddevPrice == null ? "--" : money(row.stddevPrice)}}</td>
          <td>${{row.medianPriceYoyChange == null ? "--" : signedMoney(row.medianPriceYoyChange)}}</td>
          <td>${{row.medianPriceYoy == null ? "--" : signedPercent(row.medianPriceYoy)}}</td>
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
