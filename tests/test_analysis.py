import tempfile
import unittest
from pathlib import Path

from housing_growth.analysis import analyze_observations
from housing_growth.io import read_observations
from housing_growth.models import MarketObservation
from housing_growth.sources.inkar import normalize_kennziffer, parse_inkar_number


class TrendAnalysisTests(unittest.TestCase):
    def test_classifies_core_growth_shapes(self):
        observations = []
        observations.extend(_series("Linearstadt", [100, 110, 120, 130, 140]))
        observations.extend(_series("Fallstadt", [100, 96, 92, 88, 84]))
        observations.extend(_series("Flatstadt", [100, 100.2, 99.8, 100.1, 100.0]))
        observations.extend(_series("Faststadt", [100, 120, 150, 200, 280]))

        by_city = {item.city: item for item in analyze_observations(observations)}

        self.assertEqual(by_city["Linearstadt"].trend_class, "linear_growth")
        self.assertEqual(by_city["Fallstadt"].trend_class, "decreasing")
        self.assertEqual(by_city["Flatstadt"].trend_class, "stagnant")
        self.assertEqual(by_city["Faststadt"].trend_class, "exponential_growth")

    def test_reads_normalized_csv_with_german_decimal_comma(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "observations.csv"
            path.write_text(
                "city,year,metric,value\n"
                "Berlin,2022,asking_rent_index,\"101,5\"\n"
                "Berlin,2023,asking_rent_index,\"103,0\"\n"
                "Berlin,2024,asking_rent_index,\"104,7\"\n",
                encoding="utf-8",
            )

            observations = read_observations(str(path))

        self.assertEqual(len(observations), 3)
        self.assertAlmostEqual(observations[0].value, 101.5)

    def test_parses_inkar_number_and_normalizes_city_id(self):
        self.assertAlmostEqual(parse_inkar_number("1.234,56"), 1234.56)
        self.assertEqual(normalize_kennziffer("1001000"), "01001000")


def _series(city, values):
    return [
        MarketObservation(city=city, year=2019 + index, metric="asking_rent_index", value=value)
        for index, value in enumerate(values)
    ]


if __name__ == "__main__":
    unittest.main()
