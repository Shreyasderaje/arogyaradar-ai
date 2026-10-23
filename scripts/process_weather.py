
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "weather_bengaluru.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "weather_bengaluru_clean.csv"


def main():
    # Skip NASA POWER's 11 metadata lines.
    df = pd.read_csv(INPUT_FILE, skiprows=11, na_values=[-999])

    # Convert year and day-of-year into a proper date.
    df["date"] = pd.to_datetime(
        df["YEAR"].astype(str)
        + df["DOY"].astype(str).str.zfill(3),
        format="%Y%j",
        errors="raise",
    )

    # Keep the useful weather columns.
    df = df[
        ["date", "T2M", "RH2M", "PRECTOTCORR"]
    ].rename(
        columns={
            "T2M": "temperature_c",
            "RH2M": "relative_humidity_pct",
            "PRECTOTCORR": "rainfall_mm",
        }
    )

    # Validate dates and measurements.
    assert df["date"].is_unique, "Duplicate dates found."
    assert df["date"].notna().all(), "Missing dates found."
    assert not df.duplicated().any(), "Duplicate rows found."

    assert df["temperature_c"].dropna().between(-10, 60).all()
    assert df["relative_humidity_pct"].dropna().between(0, 100).all()
    assert (df["rainfall_mm"].dropna() >= 0).all()

    # Save the processed dataset.
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print("Weather processing successful!")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Rows: {len(df)}")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print("\nMissing values:")
    print(df.isna().sum())


if __name__ == "__main__":
    main()
