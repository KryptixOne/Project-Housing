from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Mapping, Optional


INVESTMENT_WEIGHTS = {
    "demand": 0.30,
    "supply": 0.25,
    "yield": 0.20,
    "affordability": 0.15,
    "data_quality": 0.10,
}


@dataclass(frozen=True)
class YieldMetrics:
    annual_rent_per_m2: float
    gross_rental_yield_pct: float
    price_to_rent_ratio: float


@dataclass(frozen=True)
class SupplyDemandMetrics:
    total_completions: float
    total_permits: float
    absorption_ratio: Optional[float]
    absorption_ratio_display: str
    absorption_ratio_score_value: Optional[float]
    pipeline_rate: Optional[float]
    pipeline_rate_display: str


def classify_housing_basis(price_basis: str) -> str:
    return "rent" if "rent" in (price_basis or "").casefold() else "purchase"


def compute_yield_metrics(
    purchase_price_per_m2: Optional[float],
    monthly_rent_per_m2: Optional[float],
) -> Optional[YieldMetrics]:
    if not purchase_price_per_m2 or not monthly_rent_per_m2:
        return None
    if purchase_price_per_m2 <= 0 or monthly_rent_per_m2 <= 0:
        return None
    annual_rent = monthly_rent_per_m2 * 12
    return YieldMetrics(
        annual_rent_per_m2=annual_rent,
        gross_rental_yield_pct=annual_rent / purchase_price_per_m2 * 100,
        price_to_rent_ratio=purchase_price_per_m2 / annual_rent,
    )


def compute_supply_demand_metrics(
    population_by_year: Mapping[int, float],
    completions_per_1000_by_year: Mapping[int, float],
    permits_per_1000_by_year: Mapping[int, float],
    start_year: int,
    end_year: int,
) -> SupplyDemandMetrics:
    total_completions = 0.0
    total_permits = 0.0
    for year in range(start_year, end_year + 1):
        population = population_by_year.get(year)
        if population is None:
            continue
        if year in completions_per_1000_by_year:
            total_completions += population * completions_per_1000_by_year[year] / 1000
        if year in permits_per_1000_by_year:
            total_permits += population * permits_per_1000_by_year[year] / 1000

    if total_completions > 0:
        pipeline_rate = total_permits / total_completions
        pipeline_display = f"{pipeline_rate:.2f}"
    elif total_permits > 0:
        pipeline_rate = None
        pipeline_display = "Unbounded"
    else:
        pipeline_rate = None
        pipeline_display = "Unavailable"

    start_population = population_by_year.get(start_year)
    end_population = population_by_year.get(end_year)
    if start_population is None or end_population is None:
        absorption_ratio = None
        absorption_display = "Unavailable"
        absorption_score_value = None
    else:
        population_change = end_population - start_population
        if total_completions > 0:
            absorption_ratio = population_change / total_completions
            absorption_display = f"{absorption_ratio:.2f}"
            absorption_score_value = absorption_ratio
        elif population_change > 0:
            absorption_ratio = None
            absorption_display = "No completions"
            absorption_score_value = 10.0
        else:
            absorption_ratio = None
            absorption_display = "Unavailable"
            absorption_score_value = None

    return SupplyDemandMetrics(
        total_completions=total_completions,
        total_permits=total_permits,
        absorption_ratio=absorption_ratio,
        absorption_ratio_display=absorption_display,
        absorption_ratio_score_value=absorption_score_value,
        pipeline_rate=pipeline_rate,
        pipeline_rate_display=pipeline_display,
    )


def compute_weighted_score(subscores: Mapping[str, Optional[float]]) -> tuple[float, float]:
    weighted_total = 0.0
    available_weight = 0.0
    for key, weight in INVESTMENT_WEIGHTS.items():
        value = subscores.get(key)
        if value is None:
            continue
        weighted_total += value * weight
        available_weight += weight
    if available_weight == 0:
        return 0.0, 0.0
    return weighted_total / available_weight, available_weight


def score_supply_constraint(absorption_ratio_score_value: Optional[float], pipeline_rate: Optional[float]) -> Optional[float]:
    if absorption_ratio_score_value is None:
        return None
    score = _piecewise(
        absorption_ratio_score_value,
        ((0, 0), (0.7, 25), (1.2, 45), (2.0, 75), (3.0, 100)),
    )
    if pipeline_rate is not None:
        if pipeline_rate > 1.25:
            score -= min(10, (pipeline_rate - 1.25) / 1.25 * 10)
        elif pipeline_rate < 0.75:
            score += min(10, (0.75 - pipeline_rate) / 0.75 * 10)
    return max(0, min(100, score))


def _piecewise(value: float, points: tuple[tuple[float, float], ...]) -> float:
    if value <= points[0][0]:
        return points[0][1]
    for index in range(1, len(points)):
        x1, y1 = points[index - 1]
        x2, y2 = points[index]
        if value <= x2:
            ratio = (value - x1) / (x2 - x1)
            return y1 + ratio * (y2 - y1)
    return points[-1][1]
