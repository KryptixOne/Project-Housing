import argparse
import csv
import io
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from housing_growth.sources.inkar import (
    normalize_kennziffer,
    parse_inkar_number,
    read_xlsx_sheet_rows,
)


DEFAULT_ARCHIVE = Path("raw/inkar_2025.zip")
REFERENCE_PATH = Path("raw/BBSR_Raumgliederungen_Referenz_2023.xlsx")
OUTPUT_PATH = Path("data/real/inkar_2025_municipality_market_indicators.csv")

INDICATORS = {
    "xbev": ("population", "people"),
    "m_mietpr": ("asking_rent_eur_per_m2", "EUR_per_m2_month"),
    "q_gen_wo_ew": ("building_permits_per_1000_residents", "per_1000_residents"),
    "q_fert_wo_bev": ("completed_new_apartments_per_1000_residents", "per_1000_residents"),
    "q_wofl_bev": ("living_space_m2_per_resident", "m2_per_resident"),
    "d_KW_BL": ("building_land_price_eur_per_m2", "EUR_per_m2"),
}

MUNICIPALITY_CODES = {"xbev", "q_gen_wo_ew", "q_fert_wo_bev"}
DISTRICT_FALLBACK_CODES = {"m_mietpr", "q_wofl_bev", "d_KW_BL"}

FIELDNAMES = [
    "city",
    "city_id",
    "year",
    "metric",
    "value",
    "unit",
    "source",
    "coverage_level",
    "source_area",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract municipality/year INKAR market indicators with explicit coverage labels."
    )
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--reference", type=Path, default=REFERENCE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--start-year", type=int, default=2014)
    parser.add_argument("--end-year", type=int, default=2023)
    args = parser.parse_args()

    municipality_map = read_municipality_reference(args.reference)
    rows = extract_indicator_rows(
        archive_path=args.archive,
        municipality_map=municipality_map,
        start_year=args.start_year,
        end_year=args.end_year,
    )
    if not rows:
        raise SystemExit("No INKAR market-indicator rows were parsed.")

    rows.sort(key=lambda row: (row["city"], row["metric"], int(row["year"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Wrote {args.output} with {len(rows):,} observations "
        f"for {len({row['city_id'] for row in rows}):,} municipalities."
    )
    return 0


def extract_indicator_rows(
    archive_path: Path,
    municipality_map: dict[str, dict],
    start_year: int,
    end_year: int,
) -> list[dict]:
    if not archive_path.exists():
        raise FileNotFoundError(f"INKAR archive not found: {archive_path}")

    district_series: dict[tuple[str, str], dict[int, float]] = {}
    rows: list[dict] = []

    process = subprocess.Popen(
        ["unzip", "-p", str(archive_path), "inkar_2025.csv"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None:
        raise RuntimeError("Could not open unzip output stream.")

    try:
        stream = io.TextIOWrapper(process.stdout, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(stream, delimiter=";")
        for raw in reader:
            if raw.get("Bereich") != "LRB":
                continue

            code = raw.get("Kuerzel", "")
            if code not in INDICATORS:
                continue

            year = int(raw["Zeitbezug"])
            if year < start_year or year > end_year:
                continue

            value = parse_inkar_number(raw.get("Wert", ""))
            if value is None:
                continue

            metric, unit = INDICATORS[code]
            geography = raw.get("Raumbezug")
            source_id = normalize_kennziffer(raw.get("Kennziffer", ""))

            if geography == "Gemeinden" and code in MUNICIPALITY_CODES:
                municipality = municipality_map.get(source_id)
                if municipality is None:
                    continue
                rows.append(
                    build_row(
                        municipality=municipality,
                        year=year,
                        metric=metric,
                        value=value,
                        unit=unit,
                        source=f"BBSR INKAR 2025 {code} Gemeinden",
                        coverage_level="municipality",
                        source_area=municipality["city"],
                    )
                )
            elif geography == "Kreise" and code in DISTRICT_FALLBACK_CODES:
                district_series.setdefault((source_id, code), {})[year] = value
    finally:
        process.stdout.close()

    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"unzip failed with exit code {return_code}: {stderr.strip()}")

    for municipality in municipality_map.values():
        for code in sorted(DISTRICT_FALLBACK_CODES):
            metric, unit = INDICATORS[code]
            series = district_series.get((municipality["district_id"], code), {})
            for year, value in series.items():
                rows.append(
                    build_row(
                        municipality=municipality,
                        year=year,
                        metric=metric,
                        value=value,
                        unit=unit,
                        source=f"BBSR INKAR 2025 {code} Kreise mapped to municipality",
                        coverage_level=(
                            "municipality"
                            if municipality["city_id"] == municipality["district_id"]
                            else "district"
                        ),
                        source_area=municipality["district_name"],
                    )
                )

    return rows


def build_row(
    municipality: dict,
    year: int,
    metric: str,
    value: float,
    unit: str,
    source: str,
    coverage_level: str,
    source_area: str,
) -> dict:
    return {
        "city": municipality["city"],
        "city_id": municipality["city_id"],
        "year": str(year),
        "metric": metric,
        "value": format_number(value),
        "unit": unit,
        "source": source,
        "coverage_level": coverage_level,
        "source_area": source_area,
    }


def read_municipality_reference(path: Path) -> dict[str, dict]:
    rows = read_xlsx_sheet_rows(str(path), "Gemeindereferenz (inkl. Kreise)")
    headers = rows[0]
    required = ["GEM2023", "GEM_NAME", "KRS2023", "KRS_NAME"]
    indices = {header: headers.index(header) for header in required}

    result = {}
    for row in rows[2:]:
        if len(row) <= max(indices.values()):
            continue
        city_id = normalize_kennziffer(row[indices["GEM2023"]])
        district_id = normalize_kennziffer(row[indices["KRS2023"]])
        result[city_id] = {
            "city_id": city_id,
            "city": row[indices["GEM_NAME"]].strip(),
            "district_id": district_id,
            "district_name": row[indices["KRS_NAME"]].strip(),
        }
    return result


def format_number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


if __name__ == "__main__":
    raise SystemExit(main())
