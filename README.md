# German City Housing Growth Lab

This project is a small foundation for acquiring and analyzing city-level German housing-market indicators. The first working version focuses on the analysis contract: given annual observations by city, metric, and value, it ranks cities by growth and labels the trend shape.

## What Works Now

- Reads normalized CSV data with `city`, `year`, `metric`, and `value`.
- Calculates latest year-over-year growth, average YoY growth, CAGR, total growth, linear fit, exponential fit, and acceleration.
- Classifies cities as:
  - `stagnant`
  - `decreasing`
  - `linear_growth`
  - `greater_than_linear_growth`
  - `exponential_growth`
  - `growth`
  - `mixed_or_volatile`
  - `insufficient_data`
- Includes synthetic sample German city data so the analysis can run before live data credentials are available.

## Quick Start

Run the sample ranking:

```bash
python3 main.py
```

Analyze a specific metric:

```bash
python3 main.py analyze --input data/sample_city_market.csv --metric asking_rent_index
```

Sort by the most recent YoY move and write the full result set:

```bash
python3 main.py analyze \
  --input data/sample_city_market.csv \
  --metric asking_rent_index \
  --sort latest-yoy \
  --output output/trends.csv
```

Run tests:

```bash
python3 -m unittest discover -s tests
```

## Data Contract

Normalized analysis input is a UTF-8 CSV:

```csv
city,city_id,year,metric,value,unit,source
Berlin,11000000,2024,asking_rent_index,125,index_2019_100,synthetic_sample
```

Required columns:

- `city`
- `year`
- `metric`
- `value`

Optional columns:

- `city_id`: municipality or city identifier, such as AGS.
- `unit`: original unit or index definition.
- `source`: source system or dataset name.

## Data Acquisition Strategy

For Germany, start with official city-level baseline indicators, then add market-specific price/rent sources where licensing allows it.

Real public source already wired into the project:

- INKAR, the BBSR online atlas: https://www.inkar.de/
- The 2025 INKAR page provides a full database zip. The site describes the release as roughly 600 indicators covering demographics, housing, labor market, economy, transport, environment, and more, with data on a common 31.12.2023 regional boundary.

Good first official source:

- Regionaldatenbank Deutschland / GENESIS: https://www.regionalstatistik.de/genesis/online
- GENESIS web service page: https://www.regionalstatistik.de/genesis/online?Menu=Webservice

The Regionalstatistik site lists housing and environment as a top-level topic and exposes a RESTful/JSON API. As of May 19, 2025, API access requires one-time free registration. The site also announced that SOAP/XML and REST GET methods are being switched off, so the acquisition adapter uses POST.

Current dashboard data uses official INKAR municipality population plus a combined real housing/rent feed:

- Population: INKAR `xbev` at `Gemeinden` level, 2014-2023.
- NRW housing values: BORIS `Immobilienrichtwerte`, area-level official market-derived real estate guideline values.
- Non-NRW fallback: INKAR `m_mietpr` asking rents at `Kreise` level, mapped to municipalities through the BBSR 2023 reference workbook and explicitly labeled as district-level where applicable.

Download the current INKAR zip:

```bash
mkdir -p raw
curl -L https://www.bbr-server.de/imagemap/inkar/download/inkar_2025.zip -o raw/inkar_2025.zip
unzip -j raw/inkar_2025.zip BBSR_Raumgliederungen_Referenz_2023.xlsx -d raw
```

Normalize selected real city observations:

```bash
python3 main.py extract-inkar \
  --archive raw/inkar_2025.zip \
  --reference raw/BBSR_Raumgliederungen_Referenz_2023.xlsx \
  --output data/real/inkar_2025_city_market_observations.csv
```

Build the current dashboard data:

```bash
python3 scripts/build_inkar_municipality_population.py
python3 scripts/build_nrw_housing_price_data.py
python3 scripts/build_combined_housing_price_data.py
python3 scripts/generate_population_dashboard.py
```

Analyze real asking-rent trends:

```bash
python3 main.py analyze \
  --input data/real/inkar_2025_city_market_observations.csv \
  --metric asking_rent_eur_per_m2 \
  --output output/inkar_2025_city_asking_rent_trends.csv
```

Regenerate only the interactive dashboard after data is already built:

```bash
python3 scripts/generate_population_dashboard.py
```

Open `output/population_growth_dashboard.html` in a browser.

The CLI includes a raw fetch command for registered Regionalstatistik users:

```bash
export REGIONALSTATISTIK_USERNAME="your-user"
export REGIONALSTATISTIK_PASSWORD="your-password"

python3 main.py fetch-regionalstatistik \
  --table 31231-Z-02 \
  --start-year 2019 \
  --end-year 2024 \
  --output raw/regionalstatistik_31231-Z-02.csv
```

The raw GENESIS output still needs a normalization step into the project CSV contract. That is the next practical adapter to build once we choose the exact tables and inspect the returned format.

## Trend Logic

The classifier uses CAGR for the long-run direction, YoY values for consistency, linear regression for straight-line growth, a log-linear fit for exponential growth, and acceleration of absolute annual gains for greater-than-linear growth.

Defaults:

- Stagnant band: within +/- 1.0% CAGR.
- Strong growth threshold: 2.0% CAGR.
- Good model fit: R2 >= 0.85.
- Exponential must beat linear fit by at least 0.03 R2.

These thresholds are intentionally configurable because rent indices, transaction prices, population, and building permits have different normal volatility.
