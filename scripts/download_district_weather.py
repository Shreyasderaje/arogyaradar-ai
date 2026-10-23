
from pathlib import Path
import time

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parent.parent
COORDINATES_FILE = ROOT / "scripts" / "district_coordinates.csv"
OUTPUT_FILE = ROOT / "data" / "processed" / "karnataka_district_weather.csv"

START_DATE = "20210101"
END_DATE = "20240828"

API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

PARAMETERS = "T2M,RH2M,PRECTOTCORR"


def download_weather(session, district, latitude, longitude):
    params = {
        "parameters": PARAMETERS,
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": START_DATE,
        "end": END_DATE,
        "format": "JSON",
        "time-standard": "LST",
    }

    response = session.get(API_URL, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()

    if "properties" not in payload or "parameter" not in payload["properties"]:
        raise ValueError(f"Unexpected API response for {district}")

    values = payload["properties"]["parameter"]
    required = ["T2M", "RH2M", "PRECTOTCORR"]

    for parameter in required:
        if parameter not in values:
            raise ValueError(f"{parameter} missing for {district}")

    frames = []

    for parameter in required:
        series = pd.Series(values[parameter], name=parameter)
        frames.append(series)

    weather = pd.concat(frames, axis=1)
    weather.index.name = "date"
    weather = weather.reset_index()

    weather["date"] = pd.to_datetime(
        weather["date"], format="%Y%m%d", errors="raise"
    )

    weather["district_name"] = district
    weather["latitude"] = latitude
    weather["longitude"] = longitude

    weather = weather.rename(
        columns={
            "T2M": "temperature_c",
            "RH2M": "relative_humidity_pct",
            "PRECTOTCORR": "rainfall_mm",
        }
    )

    weather = weather[
        [
            "district_name",
            "date",
            "latitude",
            "longitude",
            "temperature_c",
            "relative_humidity_pct",
            "rainfall_mm",
        ]
    ]

    weather = weather.replace(-999, float("nan"))
    return weather


def main():
    districts = pd.read_csv(COORDINATES_FILE)

    required_columns = {"district_name", "latitude", "longitude"}
    if not required_columns.issubset(districts.columns):
        raise ValueError("Coordinate file is missing required columns")

    if districts["district_name"].duplicated().any():
        raise ValueError("Duplicate district names in coordinate file")

    all_weather = []
    failures = []

    with requests.Session() as session:
        for index, row in districts.iterrows():
            name = row["district_name"]
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])

            print(
                f"[{index + 1}/{len(districts)}] Downloading {name}...",
                flush=True,
            )

            try:
                weather = download_weather(
                    session, name, latitude, longitude
                )
                all_weather.append(weather)
                print(f"  Received {len(weather)} daily rows")

            except Exception as error:
                failures.append((name, str(error)))
                print(f"  FAILED: {error}")

            # Avoid sending requests too rapidly.
            time.sleep(1)

    if all_weather:
        result = pd.concat(all_weather, ignore_index=True)
        result = result.sort_values(
            ["district_name", "date"]
        ).reset_index(drop=True)

        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(OUTPUT_FILE, index=False)

        print("\nWeather download summary")
        print("Districts downloaded:", result["district_name"].nunique())
        print("Total rows:", len(result))
        print("Date range:", result["date"].min(), "to", result["date"].max())
        print("Missing values:\n", result.isna().sum())
        print("Output:", OUTPUT_FILE)

    if failures:
        print("\nFailed districts:")
        for name, message in failures:
            print(f"- {name}: {message}")

        raise SystemExit(
            f"{len(failures)} district download(s) failed. "
            "Review the errors and rerun after fixing the cause."
        )


if __name__ == "__main__":
    main()
