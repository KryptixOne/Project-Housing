import unittest

from housing_growth.investment import (
    classify_housing_basis,
    compute_supply_demand_metrics,
    compute_weighted_score,
    compute_yield_metrics,
    score_supply_constraint,
)


class InvestmentMetricTests(unittest.TestCase):
    def test_computes_gross_yield_and_price_to_rent(self):
        metrics = compute_yield_metrics(3000, 10)

        self.assertIsNotNone(metrics)
        self.assertAlmostEqual(metrics.gross_rental_yield_pct, 4.0)
        self.assertAlmostEqual(metrics.price_to_rent_ratio, 25.0)

    def test_yield_requires_purchase_and_rent_pair(self):
        self.assertIsNone(compute_yield_metrics(None, 10))
        self.assertIsNone(compute_yield_metrics(3000, None))
        self.assertIsNone(compute_yield_metrics(0, 10))
        self.assertIsNone(compute_yield_metrics(3000, 0))

    def test_classifies_asking_rent_as_rent_not_purchase(self):
        self.assertEqual(classify_housing_basis("Asking rent"), "rent")
        self.assertEqual(
            classify_housing_basis("Official real estate guideline value"),
            "purchase",
        )

    def test_supply_demand_completions_permits_absorption_and_pipeline(self):
        metrics = compute_supply_demand_metrics(
            population_by_year={2020: 1000, 2021: 1100},
            completions_per_1000_by_year={2020: 10, 2021: 10},
            permits_per_1000_by_year={2020: 12, 2021: 12},
            start_year=2020,
            end_year=2021,
        )

        self.assertAlmostEqual(metrics.total_completions, 21)
        self.assertAlmostEqual(metrics.total_permits, 25.2)
        self.assertAlmostEqual(metrics.absorption_ratio, 100 / 21)
        self.assertAlmostEqual(metrics.pipeline_rate, 25.2 / 21)

    def test_zero_completions_positive_population_is_unbounded_for_scoring(self):
        metrics = compute_supply_demand_metrics(
            population_by_year={2020: 1000, 2021: 1100},
            completions_per_1000_by_year={2020: 0, 2021: 0},
            permits_per_1000_by_year={2020: 2, 2021: 2},
            start_year=2020,
            end_year=2021,
        )

        self.assertIsNone(metrics.absorption_ratio)
        self.assertEqual(metrics.absorption_ratio_display, "No completions")
        self.assertEqual(metrics.absorption_ratio_score_value, 10.0)
        self.assertEqual(metrics.pipeline_rate_display, "Unbounded")

    def test_missing_start_or_end_population_makes_absorption_unavailable(self):
        metrics = compute_supply_demand_metrics(
            population_by_year={2020: 1000},
            completions_per_1000_by_year={2020: 10},
            permits_per_1000_by_year={2020: 12},
            start_year=2020,
            end_year=2021,
        )

        self.assertIsNone(metrics.absorption_ratio)
        self.assertEqual(metrics.absorption_ratio_display, "Unavailable")
        self.assertIsNone(metrics.absorption_ratio_score_value)
        self.assertEqual(metrics.pipeline_rate_display, "1.20")

    def test_supply_score_uses_absorption_and_pipeline_modifier(self):
        constrained = score_supply_constraint(2.0, 0.5)
        expanding_pipeline = score_supply_constraint(2.0, 2.0)

        self.assertGreater(constrained, expanding_pipeline)
        self.assertGreaterEqual(constrained, 75)

    def test_weighted_score_tracks_completeness(self):
        score, completeness = compute_weighted_score(
            {
                "demand": 80,
                "supply": 60,
                "yield": None,
                "affordability": 50,
                "data_quality": 90,
            }
        )

        self.assertGreater(score, 0)
        self.assertAlmostEqual(completeness, 0.80)


if __name__ == "__main__":
    unittest.main()
