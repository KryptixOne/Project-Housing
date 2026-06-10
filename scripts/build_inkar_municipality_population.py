import argparse
import csv
import io
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from housing_growth.sources.inkar import normalize_kennziffer, parse_inkar_number


DEFAULT_ARCHIVE = Path("raw/inkar_2025.zip")
OUTPUT_PATH = Path("data/real/inkar_2025_municipality_population_observations.csv")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract official INKAR municipality-level population observations."
    )
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--start-year", type=int, default=2014)
    parser.add_argument("--end-year", type=int, default=2023)
    args = parser.parse_args()

    rows = extract_population_rows(args.archive, args.start_year, args.end_year)
    if not rows:
        raise SystemExit("No INKAR municipality population rows were parsed.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["city", "city_id", "year", "metric", "value", "unit", "source"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Wrote {args.output} with {len(rows):,} population observations "
        f"for {len({row['city_id'] for row in rows}):,} municipalities."
    )
    return 0


def extract_population_rows(archive_path: Path, start_year: int, end_year: int) -> list[dict]:
    if not archive_path.exists():
        raise FileNotFoundError(f"INKAR archive not found: {archive_path}")

    process = subprocess.Popen(
        ["unzip", "-p", str(archive_path), "inkar_2025.csv"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None:
        raise RuntimeError("Could not open unzip output stream.")

    rows = []
    try:
        stream = io.TextIOWrapper(process.stdout, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(stream, delimiter=";")
        for raw in reader:
            if raw.get("Bereich") != "LRB":
                continue
            if raw.get("Raumbezug") != "Gemeinden":
                continue
            if raw.get("Kuerzel") != "xbev":
                continue

            year = int(raw["Zeitbezug"])
            if year < start_year or year > end_year:
                continue

            value = parse_inkar_number(raw.get("Wert", ""))
            if value is None:
                continue

            rows.append(
                {
                    "city": raw["Name"].strip(),
                    "city_id": normalize_kennziffer(raw.get("Kennziffer", "")),
                    "year": str(year),
                    "metric": "population",
                    "value": f"{value:.6f}".rstrip("0").rstrip("."),
                    "unit": "people",
                    "source": "BBSR INKAR 2025 xbev Gemeinden",
                }
            )
    finally:
        process.stdout.close()

    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"unzip failed with exit code {return_code}: {stderr.strip()}")

    rows.sort(key=lambda row: (row["city"], int(row["year"])))
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
