import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile


RAW_DIR = Path("raw")
OUTPUT_PATH = Path("data/real/neighborhood_housing_prices.csv")
DEFAULT_YEARS = range(2014, 2025)
SOURCE_NAME = "NRW BORIS Immobilienrichtwerte"
SOURCE_URL_TEMPLATE = (
    "https://www.opengeodata.nrw.de/produkte/infrastruktur_bauen_wohnen/"
    "boris/IRW/IRW_{year}_EPSG25832_Shape.zip"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build area-level housing price observations from NRW BORIS "
            "Immobilienrichtwerte shapefile DBF tables."
        )
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help="Directory containing IRW_<year>_EPSG25832_Shape.zip files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Output CSV path for the HTML dashboard.",
    )
    parser.add_argument(
        "--years",
        nargs="*",
        type=int,
        default=list(DEFAULT_YEARS),
        help="Years to include. Defaults to 2014-2024.",
    )
    args = parser.parse_args()

    grouped = defaultdict(list)
    loaded_years = []
    for year in args.years:
        zip_path = args.raw_dir / f"IRW_{year}_EPSG25832_Shape.zip"
        if not zip_path.exists():
            print(f"Skipping missing {zip_path}")
            continue
        loaded_years.append(year)
        for row in read_irw_rows(zip_path):
            city = normalize_text(row.get("GENA"))
            value = parse_number(row.get("IMRW"))
            if not city or value is None or value <= 0:
                continue
            area = area_name(row, city)
            grouped[(city, area, year)].append(value)

    if not grouped:
        raise SystemExit("No NRW BORIS Immobilienrichtwerte rows were parsed.")

    rows = []
    for (city, area, year), values in grouped.items():
        values.sort()
        rows.append(
            {
                "city": city,
                "area": area,
                "year": year,
                "median_housing_price": round(statistics.median(values), 2),
                "mean_housing_price": round(statistics.mean(values), 2),
                "stddev_housing_price": round(statistics.pstdev(values), 2)
                if len(values) > 1
                else 0,
                "unit": "EUR_per_m2",
                "source": (
                    f"{SOURCE_NAME} official market-derived real estate "
                    "guideline values"
                ),
            }
        )

    rows.sort(key=lambda row: (row["city"], row["area"], row["year"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "city",
                "area",
                "year",
                "median_housing_price",
                "mean_housing_price",
                "stddev_housing_price",
                "unit",
                "source",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Wrote {args.output} with {len(rows):,} area-year rows from "
        f"{len(loaded_years)} NRW BORIS annual files."
    )
    return 0


def read_irw_rows(zip_path: Path):
    with ZipFile(zip_path) as archive:
        dbf_names = [
            name for name in archive.namelist() if name.lower().endswith(".dbf")
        ]
        if len(dbf_names) != 1:
            raise ValueError(f"Expected one DBF in {zip_path}, found {dbf_names}")
        data = archive.read(dbf_names[0])

    record_count = int.from_bytes(data[4:8], "little")
    header_length = int.from_bytes(data[8:10], "little")
    record_length = int.from_bytes(data[10:12], "little")
    fields = read_dbf_fields(data)

    for index in range(record_count):
        start = header_length + index * record_length
        record = data[start : start + record_length]
        if not record or record[0:1] == b"*":
            continue
        yield parse_dbf_record(record, fields)


def read_dbf_fields(data: bytes):
    fields = []
    offset = 32
    while data[offset] != 0x0D:
        descriptor = data[offset : offset + 32]
        name = descriptor[:11].split(b"\0", 1)[0].decode("ascii")
        length = descriptor[16]
        fields.append((name, length))
        offset += 32
    return fields


def parse_dbf_record(record: bytes, fields):
    row = {}
    offset = 1
    for name, length in fields:
        raw = record[offset : offset + length]
        offset += length
        row[name] = raw.decode("utf-8", errors="replace").strip()
    return row


def area_name(row: dict, city: str) -> str:
    candidates = [
        normalize_text(row.get("ORTST")),
        normalize_text(row.get("GEBIET")),
        normalize_text(row.get("GEMA")),
        normalize_text(row.get("NAME_IRW")),
    ]
    city_folded = city.casefold()
    ignored = {city_folded, f"stadt {city_folded}", "stadtgebiet"}
    for candidate in candidates:
        if candidate and candidate.casefold() not in ignored:
            return candidate
    return next((candidate for candidate in candidates if candidate), city)


def normalize_text(value: str) -> str:
    return " ".join((value or "").split())


def parse_number(value: str):
    cleaned = normalize_text(value).replace(" ", "")
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        number = float(cleaned)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


if __name__ == "__main__":
    raise SystemExit(main())
