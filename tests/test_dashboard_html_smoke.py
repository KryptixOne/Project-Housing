import unittest
from pathlib import Path


HTML_PATH = Path("output/population_growth_dashboard.html")


class GeneratedDashboardSmokeTests(unittest.TestCase):
    @unittest.skipUnless(HTML_PATH.exists(), "generated dashboard HTML not present")
    def test_generated_html_contains_investment_and_housing_markers(self):
        markers = [
            "Investment Potential",
            "market_indicators",
            "investmentWeights",
            "computeInvestmentScore",
            "scoreDemand",
            "scoreSupplyConstraint",
            "scoreYield",
            "scoreAffordability",
            "scoreDataQuality",
            "grossRentalYieldPct",
            "priceToRentRatio",
            "absorptionRatio",
            "pipelineRate",
            "Growth + Price/Rent Signals",
            "opportunityChartTitle: document.getElementById(\"opportunityChartTitle\")",
            "opportunitySignalMetric",
            "Best available price/rent signal",
            "Conservative comparable mode",
            "Yield and Price-to-Rent Over Years",
            "housingYieldChart",
            "housingPriceRentChart",
            "Gross rental yield",
            "Price-to-rent ratio",
            "Absorption ratio",
            "Pipeline rate",
            "Investment score",
            "data-investment-sort=\"investmentScore\"",
            "data-investment-sort=\"grossRentalYieldPct\"",
            "investmentChartRowLimit",
            "investmentYieldDemandChart: document.getElementById(\"investmentYieldDemandChart\")",
            "investmentSupplyChart: document.getElementById(\"investmentSupplyChart\")",
        ]

        missing = _missing_tokens(HTML_PATH, markers)

        self.assertEqual(missing, [])

    @unittest.skipUnless(HTML_PATH.exists(), "generated dashboard HTML not present")
    def test_generated_html_has_no_external_script_or_stylesheet_refs(self):
        forbidden = [
            "<script src",
            "<link ",
            "fetch(",
            "import(",
        ]

        present = [token for token in forbidden if not _missing_tokens(HTML_PATH, [token])]

        self.assertEqual(present, [])


def _missing_tokens(path: Path, tokens: list[str]) -> list[str]:
    remaining = {token: token.encode("utf-8") for token in tokens}
    if not remaining:
        return []

    max_token_length = max(len(token) for token in remaining.values())
    overlap = b""
    with path.open("rb") as handle:
        while remaining:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            window = overlap + chunk
            for token, needle in list(remaining.items()):
                if needle in window:
                    remaining.pop(token)
            overlap = window[-max_token_length + 1 :]

    return list(remaining)


if __name__ == "__main__":
    unittest.main()
