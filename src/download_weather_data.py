"""
download_nyc_weather_2025.py

Download hourly NYC historical weather for all of 2025 from Open-Meteo.
Designed for joining with an hourly NYC Uber/Lyft demand dataset.

Output:
    data/raw/weather/nyc_weather_hourly_2025.csv
    data/raw/weather/nyc_weather_hourly_2025.parquet

Run:
    python src/data/download_nyc_weather_2025.py

Requirements:
    pip install pandas requests pyarrow
"""

from pathlib import Path
import requests
import pandas as pd


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

YEAR = 2025

# NYC / Midtown Manhattan approximate coordinates.
# For a citywide demand model, one representative NYC weather point
# is usually sufficient as a first version of the project.
LATITUDE = 40.7128
LONGITUDE = -74.0060

TIMEZONE = "America/New_York"

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

# If this file is stored at:
# project_root/src/data/download_nyc_weather_2025.py
# then parents[2] points to project_root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "weather"

CSV_PATH = OUTPUT_DIR / f"nyc_weather_hourly_{YEAR}.csv"
PARQUET_PATH = OUTPUT_DIR / f"nyc_weather_hourly_{YEAR}.parquet"


# Weather features which are useful for trip-demand modeling.
HOURLY_VARIABLES = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "rain",
    "snowfall",
    "weather_code",
    "cloud_cover",
    "pressure_msl",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]


def download_weather(year: int) -> pd.DataFrame:
    """Download one full year of hourly NYC weather."""

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": TIMEZONE,

        # Explicit units make downstream analysis clearer.
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
    }

    print(f"Downloading NYC hourly weather for {year}...")

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()

    if "hourly" not in data:
        raise ValueError(
            "Open-Meteo response does not contain hourly weather data."
        )

    df = pd.DataFrame(data["hourly"])

    return df


def clean_weather(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare weather data for SQL / ML use."""

    df = df.copy()

    # Convert Open-Meteo timestamp string into pandas datetime.
    # Because timezone=America/New_York was requested, these timestamps
    # correspond to NYC local clock time.
    df["weather_hour"] = pd.to_datetime(df["time"])

    df = df.drop(columns=["time"])

    # Put join key first.
    cols = ["weather_hour"] + [
        col for col in df.columns if col != "weather_hour"
    ]
    df = df[cols]

    # Add calendar features which are useful for inspection/modeling.
    df["weather_date"] = df["weather_hour"].dt.date
    df["hour_of_day"] = df["weather_hour"].dt.hour
    df["day_of_week"] = df["weather_hour"].dt.day_name()
    df["month"] = df["weather_hour"].dt.month

    # Simple precipitation indicator.
    df["is_precipitating"] = (
        df["precipitation"].fillna(0) > 0
    ).astype(int)

    # Simple snow indicator.
    df["is_snowing"] = (
        df["snowfall"].fillna(0) > 0
    ).astype(int)

    # Reorder useful ID/time fields to the front.
    front = [
        "weather_hour",
        "weather_date",
        "day_of_week",
        "month",
        "hour_of_day",
    ]

    remaining = [c for c in df.columns if c not in front]

    return df[front + remaining]


def validate_weather(df: pd.DataFrame, year: int) -> None:
    """Basic checks before saving."""

    if df.empty:
        raise ValueError("Weather dataframe is empty.")

    if df["weather_hour"].duplicated().any():
        duplicated = df.loc[
            df["weather_hour"].duplicated(keep=False),
            "weather_hour",
        ]
        print(
            "\nWARNING: duplicate local clock hours detected "
            "(this can occur around daylight-saving time)."
        )
        print(duplicated.to_string(index=False))

    missing = df.isna().sum()
    missing = missing[missing > 0]

    print("\nValidation")
    print("-" * 50)
    print(f"Rows: {len(df):,}")
    print(f"Start: {df['weather_hour'].min()}")
    print(f"End:   {df['weather_hour'].max()}")

    if len(missing) == 0:
        print("Missing values: none")
    else:
        print("\nMissing values:")
        print(missing)


def save_weather(df: pd.DataFrame) -> None:
    """Save CSV and Parquet copies."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(CSV_PATH, index=False)
    df.to_parquet(PARQUET_PATH, index=False)

    print("\nSaved successfully:")
    print(f"CSV:     {CSV_PATH}")
    print(f"Parquet: {PARQUET_PATH}")


def main() -> None:
    weather = download_weather(YEAR)
    weather = clean_weather(weather)

    validate_weather(weather, YEAR)
    save_weather(weather)

    print("\nPreview:")
    print(weather.head())

    print("\nSeptember 2025 preview:")
    september = weather[
        weather["weather_hour"].dt.month == 9
    ]
    print(september.head())


if __name__ == "__main__":
    main()