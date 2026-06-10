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


BORIS_INPUT_PATH = Path("data/real/neighborhood_housing_prices.csv")
REFERENCE_PATH = Path("raw/BBSR_Raumgliederungen_Referenz_2023.xlsx")
INKAR_ARCHIVE_PATH = Path("raw/inkar_2025.zip")
OUTPUT_PATH = Path("data/real/neighborhood_housing_prices.csv")

FIELDNAMES = [
    "city",
    "city_id",
    "area",
    "year",
    "median_housing_price",
    "mean_housing_price",
    "stddev_housing_price",
    "unit",
    "source",
    "price_basis",
    "coverage_level",
    "source_area",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Combine richer NRW BORIS Immobilienrichtwerte with real INKAR "
            "district-level asking-rent fallback for other German municipalities."
        )
    )
    parser.add_argument("--boris-input", type=Path, default=BORIS_INPUT_PATH)
    parser.add_argument("--reference", type=Path, default=REFERENCE_PATH)
    parser.add_argument("--inkar-archive", type=Path, default=INKAR_ARCHIVE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--start-year", type=int, default=2014)
    parser.add_argument("--end-year", type=int, default=2024)
    args = parser.parse_args()

    municipality_map = read_municipality_reference(args.reference)
    boris_rows = read_existing_boris_rows(args.boris_input, municipality_map)
    boris_city_keys = {city_key(row["city"]) for row in boris_rows}
    district_rents = read_inkar_district_rents(
        args.inkar_archive,
        args.start_year,
        args.end_year,
    )

    fallback_rows = []
    for municipality in municipality_map.values():
        if city_key(municipality["city"]) in boris_city_keys:
            continue
        district_series = district_rents.get(municipality["district_id"])
        if not district_series:
            continue
        for year, value in district_series.items():
            fallback_rows.append(
                {
                    "city": municipality["city"],
                    "city_id": municipality["city_id"],
                    "area": f"{municipality['district_name']} asking rent",
                    "year": str(year),
                    "median_housing_price": format_number(value),
                    "mean_housing_price": format_number(value),
                    "stddev_housing_price": "0",
                    "unit": "EUR_per_m2",
                    "source": "BBSR INKAR 2025 m_mietpr district-level asking rent",
                    "price_basis": "Asking rent",
                    "coverage_level": (
                        "city" if municipality["city_id"] == municipality["district_id"] else "district"
                    ),
                    "source_area": municipality["district_name"],
                }
            )

    rows = sorted(
        boris_rows + fallback_rows,
        key=lambda row: (city_key(row["city"]), row["area"], int(row["year"])),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Wrote {args.output} with {len(rows):,} rows: "
        f"{len(boris_rows):,} NRW BORIS rows plus "
        f"{len(fallback_rows):,} INKAR district-rent fallback rows."
    )
    return 0


def read_existing_boris_rows(path: Path, municipality_map: dict[str, dict]) -> list[dict]:
    if not path.exists():
        return []

    municipality_by_name = build_unique_name_lookup(municipality_map)
    rows = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            source = raw.get("source", "")
            is_inkar_fallback = "m_mietpr" in source or raw.get("price_basis") == "Asking rent"
            if is_inkar_fallback:
                continue
            city_id = raw.get("city_id") or municipality_by_name.get(city_key(raw["city"]), {}).get("city_id", "")
            rows.append(
                {
                    "city": raw["city"],
                    "city_id": city_id,
                    "area": raw["area"],
                    "year": raw["year"],
                    "median_housing_price": raw["median_housing_price"],
                    "mean_housing_price": raw["mean_housing_price"],
                    "stddev_housing_price": raw["stddev_housing_price"],
                    "unit": raw.get("unit") or "EUR_per_m2",
                    "source": raw.get("source")
                    or "NRW BORIS Immobilienrichtwerte official market-derived real estate guideline values",
                    "price_basis": raw.get("price_basis") or "Official real estate guideline value",
                    "coverage_level": raw.get("coverage_level") or "area",
                    "source_area": raw.get("source_area") or raw["area"],
                }
            )
    return rows


def build_unique_name_lookup(municipality_map: dict[str, dict]) -> dict[str, dict]:
    counts: dict[str, int] = {}
    for municipality in municipality_map.values():
        key = city_key(municipality["city"])
        counts[key] = counts.get(key, 0) + 1

    result = {}
    for municipality in municipality_map.values():
        key = city_key(municipality["city"])
        if counts[key] == 1:
            result[key] = municipality
    return result


def read_municipality_reference(path: Path) -> dict[str, dict]:
    rows = read_xlsx_sheet_rows(str(path), "Gemeindereferenz (inkl. Kreise)")
    headers = rows[0]
    indices = {header: headers.index(header) for header in ["GEM2023", "GEM_NAME", "KRS2023", "KRS_NAME"]}
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


def read_inkar_district_rents(archive_path: Path, start_year: int, end_year: int) -> dict[str, dict[int, float]]:
    if not archive_path.exists():
        raise FileNotFoundError(f"INKAR archive not found: {archive_path}")

    process = subprocess.Popen(
        ["unzip", "-p", str(archive_path), "inkar_2025.csv"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None:
        raise RuntimeError("Could not open unzip output stream.")

    result: dict[str, dict[int, float]] = {}
    try:
        stream = io.TextIOWrapper(process.stdout, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(stream, delimiter=";")
        for raw in reader:
            if raw.get("Bereich") != "LRB":
                continue
            if raw.get("Raumbezug") != "Kreise":
                continue
            if raw.get("Kuerzel") != "m_mietpr":
                continue

            year = int(raw["Zeitbezug"])
            if year < start_year or year > end_year:
                continue

            value = parse_inkar_number(raw.get("Wert", ""))
            if value is None:
                continue

            district_id = normalize_kennziffer(raw.get("Kennziffer", ""))
            result.setdefault(district_id, {})[year] = value
    finally:
        process.stdout.close()

    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"unzip failed with exit code {return_code}: {stderr.strip()}")

    return result


def city_key(value: str) -> str:
    return value.split(",")[0].strip().casefold()


def format_number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


if __name__ == "__main__":
    raise SystemExit(main())
