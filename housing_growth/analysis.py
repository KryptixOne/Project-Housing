import math
import statistics
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .models import CityTrendSummary, MarketObservation, TrendConfig


def analyze_observations(
    observations: Iterable[MarketObservation],
    metric: Optional[str] = None,
    config: Optional[TrendConfig] = None,
) -> List[CityTrendSummary]:
    """Analyze observations grouped by city and metric."""
    config = config or TrendConfig()
    grouped: Dict[Tuple[str, str], List[MarketObservation]] = defaultdict(list)

    for observation in observations:
        if metric and observation.metric != metric:
            continue
        grouped[(observation.city, observation.metric)].append(observation)

    summaries = [
        analyze_city_metric(group, config)
        for group in grouped.values()
        if group
    ]
    return sorted(
        summaries,
        key=lambda item: (
            item.cagr_pct if item.cagr_pct is not None else float("-inf"),
            item.latest_yoy_pct if item.latest_yoy_pct is not None else float("-inf"),
            item.city,
        ),
        reverse=True,
    )


def analyze_city_metric(
    observations: Sequence[MarketObservation],
    config: Optional[TrendConfig] = None,
) -> CityTrendSummary:
    config = config or TrendConfig()
    series = sorted(observations, key=lambda item: item.year)
    if not series:
        raise ValueError("Cannot analyze an empty observation series.")

    city = series[-1].city
    metric = series[-1].metric
    years = [item.year for item in series]
    values = [item.value for item in series]
    start_year = years[0]
    end_year = years[-1]
    start_value = values[0]
    end_value = values[-1]

    if len(series) < 3:
        return CityTrendSummary(
            city=city,
            metric=metric,
            start_year=start_year,
            end_year=end_year,
            start_value=start_value,
            end_value=end_value,
            observations=len(series),
            latest_yoy_pct=None,
            average_yoy_pct=None,
            cagr_pct=None,
            total_growth_pct=_percent_change(start_value, end_value),
            trend_class="insufficient_data",
            confidence=0.1,
            linear_r2=0.0,
            exponential_r2=None,
            slope_per_year=0.0,
            acceleration_per_year2=0.0,
            reason="Need at least 3 annual observations to classify a trend.",
        )

    xs = [float(year - start_year) for year in years]
    linear_slope, _, linear_r2 = _linear_regression(xs, values)
    exp_r2 = _exponential_r2(xs, values)
    yoy_values = _annualized_yoy_values(series)
    latest_yoy_pct = yoy_values[-1] if yoy_values else None
    average_yoy_pct = statistics.mean(yoy_values) if yoy_values else None
    total_growth_pct = _percent_change(start_value, end_value)
    cagr_pct = _cagr(start_value, end_value, end_year - start_year)
    acceleration = _acceleration_per_year2(series)

    trend_class, reason = _classify_trend(
        cagr_pct=cagr_pct,
        average_yoy_pct=average_yoy_pct,
        total_growth_pct=total_growth_pct,
        yoy_values=yoy_values,
        linear_r2=linear_r2,
        exponential_r2=exp_r2,
        acceleration=acceleration,
        values=values,
        config=config,
    )

    return CityTrendSummary(
        city=city,
        metric=metric,
        start_year=start_year,
        end_year=end_year,
        start_value=start_value,
        end_value=end_value,
        observations=len(series),
        latest_yoy_pct=latest_yoy_pct,
        average_yoy_pct=average_yoy_pct,
        cagr_pct=cagr_pct,
        total_growth_pct=total_growth_pct,
        trend_class=trend_class,
        confidence=_confidence(len(series), max(linear_r2, exp_r2 or 0.0), yoy_values),
        linear_r2=linear_r2,
        exponential_r2=exp_r2,
        slope_per_year=linear_slope,
        acceleration_per_year2=acceleration,
        reason=reason,
    )


def _classify_trend(
    cagr_pct: Optional[float],
    average_yoy_pct: Optional[float],
    total_growth_pct: Optional[float],
    yoy_values: Sequence[float],
    linear_r2: float,
    exponential_r2: Optional[float],
    acceleration: float,
    values: Sequence[float],
    config: TrendConfig,
) -> Tuple[str, str]:
    growth_rate = cagr_pct if cagr_pct is not None else average_yoy_pct
    if growth_rate is None:
        return "unclassifiable", "Values could not be converted into year-over-year growth rates."

    positive_share = _share(yoy_values, lambda value: value > config.stagnant_cagr_pct)
    negative_share = _share(yoy_values, lambda value: value < -config.stagnant_cagr_pct)
    avg_abs_delta = _average_absolute_delta(values)
    acceleration_share = abs(acceleration) / avg_abs_delta if avg_abs_delta else 0.0

    if (
        growth_rate <= -config.stagnant_cagr_pct
        and negative_share >= 0.5
    ):
        return (
            "decreasing",
            "CAGR is negative and at least half of observed yearly moves are materially down.",
        )

    if (
        abs(growth_rate) <= config.stagnant_cagr_pct
        and (total_growth_pct is None or abs(total_growth_pct) <= config.stagnant_cagr_pct * max(1, len(values) - 1) * 1.5)
    ):
        return (
            "stagnant",
            "CAGR and total change are inside the configured stagnant band.",
        )

    if growth_rate > config.stagnant_cagr_pct:
        if (
            exponential_r2 is not None
            and exponential_r2 >= config.good_fit_r2
            and exponential_r2 >= linear_r2 + config.exponential_r2_margin
            and positive_share >= 0.7
        ):
            return (
                "exponential_growth",
                "Positive yearly moves fit an exponential curve better than a straight line.",
            )

        if (
            acceleration > 0
            and acceleration_share >= config.acceleration_share_threshold
            and growth_rate >= config.strong_growth_cagr_pct
            and positive_share >= 0.6
        ):
            return (
                "greater_than_linear_growth",
                "Growth is positive and the annual absolute gains are accelerating.",
            )

        if linear_r2 >= config.good_fit_r2 and positive_share >= 0.6:
            return (
                "linear_growth",
                "Positive growth is explained well by a straight-line trend.",
            )

        return (
            "growth",
            "Growth is positive, but the path is not cleanly linear or exponential.",
        )

    if growth_rate < -config.stagnant_cagr_pct:
        return (
            "decreasing",
            "CAGR is materially negative, although yearly moves are mixed.",
        )

    return (
        "mixed_or_volatile",
        "The long-run growth rate is near flat, but yearly moves are too uneven for a stagnant label.",
    )


def _annualized_yoy_values(series: Sequence[MarketObservation]) -> List[float]:
    values: List[float] = []
    for previous, current in zip(series, series[1:]):
        years = current.year - previous.year
        if years <= 0 or previous.value <= 0 or current.value <= 0:
            continue
        values.append(((current.value / previous.value) ** (1.0 / years) - 1.0) * 100.0)
    return values


def _percent_change(start: float, end: float) -> Optional[float]:
    if start == 0:
        return None
    return ((end - start) / abs(start)) * 100.0


def _cagr(start: float, end: float, years: int) -> Optional[float]:
    if years <= 0 or start <= 0 or end <= 0:
        return None
    return ((end / start) ** (1.0 / years) - 1.0) * 100.0


def _linear_regression(xs: Sequence[float], ys: Sequence[float]) -> Tuple[float, float, float]:
    if len(xs) != len(ys):
        raise ValueError("x and y series must have the same length.")

    x_mean = statistics.mean(xs)
    y_mean = statistics.mean(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return 0.0, y_mean, 0.0

    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominator
    intercept = y_mean - slope * x_mean
    predicted = [intercept + slope * x for x in xs]
    r2 = _r2(ys, predicted)
    return slope, intercept, r2


def _exponential_r2(xs: Sequence[float], values: Sequence[float]) -> Optional[float]:
    if any(value <= 0 for value in values):
        return None
    log_values = [math.log(value) for value in values]
    _, _, r2 = _linear_regression(xs, log_values)
    return r2


def _r2(actual: Sequence[float], predicted: Sequence[float]) -> float:
    actual_mean = statistics.mean(actual)
    total = sum((value - actual_mean) ** 2 for value in actual)
    if total == 0:
        return 1.0
    residual = sum((value - estimate) ** 2 for value, estimate in zip(actual, predicted))
    return max(0.0, min(1.0, 1.0 - residual / total))


def _acceleration_per_year2(series: Sequence[MarketObservation]) -> float:
    annual_deltas: List[float] = []
    midpoints: List[float] = []
    start_year = series[0].year

    for previous, current in zip(series, series[1:]):
        year_gap = current.year - previous.year
        if year_gap <= 0:
            continue
        annual_deltas.append((current.value - previous.value) / year_gap)
        midpoints.append(((previous.year + current.year) / 2.0) - start_year)

    if len(annual_deltas) < 2:
        return 0.0

    slope, _, _ = _linear_regression(midpoints, annual_deltas)
    return slope


def _average_absolute_delta(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.mean(abs(current - previous) for previous, current in zip(values, values[1:]))


def _share(values: Sequence[float], predicate) -> float:
    if not values:
        return 0.0
    return sum(1 for value in values if predicate(value)) / float(len(values))


def _confidence(observation_count: int, fit_r2: float, yoy_values: Sequence[float]) -> float:
    length_score = min(1.0, max(0.0, (observation_count - 2) / 4.0))
    if len(yoy_values) > 1:
        volatility = statistics.pstdev(yoy_values)
        avg_abs = statistics.mean(abs(value) for value in yoy_values) or 1.0
        stability = 1.0 - min(1.0, volatility / max(2.0, avg_abs * 2.0))
    else:
        stability = 0.4

    score = 0.2 + 0.35 * length_score + 0.3 * fit_r2 + 0.15 * stability
    return round(max(0.1, min(0.99, score)), 2)
