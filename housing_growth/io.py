import csv
from pathlib import Path
from typing import Iterable, List, Optional

from .models import CityTrendSummary, MarketObservation

REQUIRED_COLUMNS = {"city", "year", "metric", "value"}


def read_observations(path: str) -> List[MarketObservation]:
    csv_path = Path(path)
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} does not contain a CSV header row.")

        missing = REQUIRED_COLUMNS.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"{path} is missing required columns: {', '.join(sorted(missing))}")

        observations: List[MarketObservation] = []
        for row_number, row in enumerate(reader, start=2):
            try:
                observations.append(
                    MarketObservation(
                        city=_required(row, "city", row_number),
                        city_id=(row.get("city_id") or "").strip(),
                        year=int(_required(row, "year", row_number)),
                        metric=_required(row, "metric", row_number),
                        value=_parse_number(_required(row, "value", row_number)),
                        unit=(row.get("unit") or "").strip(),
                        source=(row.get("source") or "").strip(),
                    )
                )
            except ValueError as exc:
                raise ValueError(f"{path}:{row_number}: {exc}") from exc

    return observations


def write_summaries_csv(path: str, summaries: Iterable[CityTrendSummary]) -> None:
    fieldnames = [
        "city",
        "metric",
        "start_year",
        "end_year",
        "start_value",
        "end_value",
        "observations",
        "latest_yoy_pct",
        "average_yoy_pct",
        "cagr_pct",
        "total_growth_pct",
        "trend_class",
        "confidence",
        "linear_r2",
        "exponential_r2",
        "slope_per_year",
        "acceleration_per_year2",
        "reason",
    ]
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for summary in summaries:
            writer.writerow({name: _format_value(getattr(summary, name)) for name in fieldnames})


def _required(row: dict, key: str, row_number: int) -> str:
    value = (row.get(key) or "").strip()
    if value == "":
        raise ValueError(f"column '{key}' is blank")
    return value


def _parse_number(raw: str) -> float:
    value = raw.strip().replace(" ", "").replace("%", "")
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")
    return float(value)


def _format_value(value: Optional[object]) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
