from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MarketObservation:
    city: str
    year: int
    metric: str
    value: float
    city_id: str = ""
    unit: str = ""
    source: str = ""


@dataclass(frozen=True)
class TrendConfig:
    stagnant_cagr_pct: float = 1.0
    strong_growth_cagr_pct: float = 2.0
    good_fit_r2: float = 0.85
    exponential_r2_margin: float = 0.03
    acceleration_share_threshold: float = 0.15


@dataclass(frozen=True)
class CityTrendSummary:
    city: str
    metric: str
    start_year: int
    end_year: int
    start_value: float
    end_value: float
    observations: int
    latest_yoy_pct: Optional[float]
    average_yoy_pct: Optional[float]
    cagr_pct: Optional[float]
    total_growth_pct: Optional[float]
    trend_class: str
    confidence: float
    linear_r2: float
    exponential_r2: Optional[float]
    slope_per_year: float
    acceleration_per_year2: float
    reason: str
