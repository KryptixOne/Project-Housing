import argparse
import os
from pathlib import Path
from typing import List, Optional

from .analysis import analyze_observations
from .io import read_observations, write_summaries_csv
from .models import CityTrendSummary, TrendConfig
from .sources.inkar import DEFAULT_INDICATORS, extract_inkar_city_observations
from .sources.regionalstatistik import fetch_table_csv


DEFAULT_INPUT = "data/sample_city_market.csv"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="housing-growth",
        description="Rank German city markets and classify growth trends from annual city-level observations.",
    )
    subparsers = parser.add_subparsers(dest="command")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a normalized city metric CSV.")
    _add_analyze_arguments(analyze_parser)

    fetch_parser = subparsers.add_parser(
        "fetch-regionalstatistik",
        help="Fetch a raw Regionalstatistik/GENESIS table with registered API credentials.",
    )
    fetch_parser.add_argument("--table", required=True, help="GENESIS table name, for example 31231-Z-02.")
    fetch_parser.add_argument("--output", required=True, help="Where to store the raw CSV response.")
    fetch_parser.add_argument("--start-year", type=int, default=None)
    fetch_parser.add_argument("--end-year", type=int, default=None)
    fetch_parser.add_argument("--username-env", default="REGIONALSTATISTIK_USERNAME")
    fetch_parser.add_argument("--password-env", default="REGIONALSTATISTIK_PASSWORD")
    fetch_parser.add_argument("--timeout", type=int, default=60)

    inkar_parser = subparsers.add_parser(
        "extract-inkar",
        help="Normalize selected real BBSR INKAR city observations from the public 2025 zip.",
    )
    inkar_parser.add_argument("--archive", default="raw/inkar_2025.zip")
    inkar_parser.add_argument("--reference", default="raw/BBSR_Raumgliederungen_Referenz_2023.xlsx")
    inkar_parser.add_argument("--output", default="data/real/inkar_2025_city_market_observations.csv")
    inkar_parser.add_argument("--start-year", type=int, default=None)
    inkar_parser.add_argument("--end-year", type=int, default=None)
    inkar_parser.add_argument(
        "--indicators",
        default=",".join(DEFAULT_INDICATORS),
        help="Comma-separated INKAR indicator codes to extract.",
    )

    args = parser.parse_args(argv)
    if args.command == "fetch-regionalstatistik":
        return _fetch_regionalstatistik(args)
    if args.command == "extract-inkar":
        return _extract_inkar(args)

    if args.command is None:
        args = parser.parse_args(["analyze"])

    return _analyze(args)


def _add_analyze_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Normalized CSV to analyze.")
    parser.add_argument("--metric", default=None, help="Metric to include, e.g. asking_rent_index.")
    parser.add_argument("--output", default=None, help="Optional CSV output path for full results.")
    parser.add_argument("--top", type=int, default=15, help="Number of rows to print.")
    parser.add_argument(
        "--sort",
        choices=["cagr", "latest-yoy", "city"],
        default="cagr",
        help="Printed table sort order.",
    )
    parser.add_argument("--stagnant-threshold", type=float, default=1.0, help="CAGR band for stagnant markets.")
    parser.add_argument("--strong-growth-threshold", type=float, default=2.0, help="CAGR level used for accelerating growth labels.")


def _analyze(args: argparse.Namespace) -> int:
    config = TrendConfig(
        stagnant_cagr_pct=args.stagnant_threshold,
        strong_growth_cagr_pct=args.strong_growth_threshold,
    )
    observations = read_observations(args.input)
    summaries = analyze_observations(observations, metric=args.metric, config=config)
    summaries = _sort_summaries(summaries, args.sort)

    if args.output:
        write_summaries_csv(args.output, summaries)

    _print_table(summaries[: args.top], args.metric)
    if args.output:
        print(f"\nWrote full results to {args.output}")
    return 0


def _fetch_regionalstatistik(args: argparse.Namespace) -> int:
    username = os.environ.get(args.username_env)
    password = os.environ.get(args.password_env)
    if not username or not password:
        raise SystemExit(
            "Missing Regionalstatistik credentials. Set "
            f"{args.username_env} and {args.password_env} before fetching."
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = fetch_table_csv(
        table=args.table,
        username=username,
        password=password,
        start_year=args.start_year,
        end_year=args.end_year,
        timeout=args.timeout,
    )
    output_path.write_text(content, encoding="utf-8")
    print(f"Wrote raw Regionalstatistik table {args.table} to {output_path}")
    return 0


def _extract_inkar(args: argparse.Namespace) -> int:
    indicators = [code.strip() for code in args.indicators.split(",") if code.strip()]
    result = extract_inkar_city_observations(
        archive_path=args.archive,
        reference_xlsx_path=args.reference,
        output_path=args.output,
        indicators=indicators,
        start_year=args.start_year,
        end_year=args.end_year,
    )
    print(
        f"Wrote {result.rows_written} real INKAR observations "
        f"for {result.cities_included} independent cities "
        f"and {result.indicators_included} indicators to {args.output}"
    )
    return 0


def _sort_summaries(summaries: List[CityTrendSummary], sort_key: str) -> List[CityTrendSummary]:
    if sort_key == "latest-yoy":
        return sorted(
            summaries,
            key=lambda item: item.latest_yoy_pct if item.latest_yoy_pct is not None else float("-inf"),
            reverse=True,
        )
    if sort_key == "city":
        return sorted(summaries, key=lambda item: item.city)
    return sorted(
        summaries,
        key=lambda item: item.cagr_pct if item.cagr_pct is not None else float("-inf"),
        reverse=True,
    )


def _print_table(summaries: List[CityTrendSummary], metric: Optional[str]) -> None:
    title = "City market trend ranking"
    if metric:
        title += f" for {metric}"
    print(title)

    rows = []
    for rank, summary in enumerate(summaries, start=1):
        row = [
            str(rank),
            summary.city,
            summary.trend_class,
            _pct(summary.cagr_pct),
            _pct(summary.latest_yoy_pct),
            f"{summary.linear_r2:.2f}",
            _maybe_float(summary.exponential_r2),
            f"{summary.start_year}-{summary.end_year}",
            f"{summary.confidence:.2f}",
        ]
        if metric is None:
            row.insert(2, summary.metric)
        rows.append(row)

    headers = ["#", "city", "class", "cagr", "latest yoy", "lin r2", "exp r2", "years", "conf"]
    if metric is None:
        headers.insert(2, "metric")
    _print_rows(headers, rows)


def _print_rows(headers: List[str], rows: List[List[str]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def render(row: List[str]) -> str:
        return "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row))

    print(render(headers))
    print(render(["-" * width for width in widths]))
    for row in rows:
        print(render(row))


def _pct(value: Optional[float]) -> str:
    if value is None:
        return ""
    return f"{value:.2f}%"


def _maybe_float(value: Optional[float]) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"
