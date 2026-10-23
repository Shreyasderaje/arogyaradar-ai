
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

DENGUE_FILE = ROOT / "data" / "processed" / "dengue_karnataka_clean.csv"
WEATHER_FILE = ROOT / "data" / "processed" / "karnataka_district_weather.csv"

OUTPUT_FILE = ROOT / "data" / "processed" / "dengue_weather_merged.csv"
REVIEW_FILE = ROOT / "data" / "processed" / "dengue_weather_unmatched_dengue.csv"

def main():
    dengue = pd.read_csv(DENGUE_FILE)
    weather = pd.read_csv(WEATHER_FILE)

    # Standardize dates
    dengue["merge_date"] = pd.to_datetime(
        dengue["metadata.recordDate"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    weather["date"] = pd.to_datetime(
        weather["date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    # Map known district spelling differences
    aliases = {
        "BAGALKOTE": "BAGALKOT",
        "BALLARI": "BELLARY",
    }

    dengue["merge_district"] = (
        dengue["district_census2011"]
        .astype(str)
        .str.strip()
        .str.upper()
        .replace(aliases)
    )

    weather["merge_district"] = (
        weather["district_name"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Keep unmatched dengue records for review
    matched_weather_districts = set(weather["merge_district"].unique())
    unmatched_mask = ~dengue["merge_district"].isin(matched_weather_districts)

    unmatched = dengue.loc[unmatched_mask].copy()
    unmatched.drop(columns=["merge_date", "merge_district"], inplace=True)
    unmatched.to_csv(REVIEW_FILE, index=False)

    # Exclude unmatched district records from the merge
    dengue_matched = dengue.loc[~unmatched_mask].copy()

    # Select weather columns to attach
    weather_columns = [
        "merge_district",
        "date",
        "temperature_c",
        "relative_humidity_pct",
        "rainfall_mm",
    ]
    weather_for_merge = weather[weather_columns].copy()

    # Check weather join keys are unique
    if weather_for_merge.duplicated(["merge_district", "date"]).any():
        raise ValueError("Weather contains duplicate district-date keys")

    merged = dengue_matched.merge(
        weather_for_merge,
        left_on=["merge_district", "merge_date"],
        right_on=["merge_district", "date"],
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    unmatched_dates = merged["_merge"] != "both"
    if unmatched_dates.any():
        print("WARNING: Some dengue records did not find matching weather.")
        print(
            merged.loc[unmatched_dates, [
                "district_census2011", "merge_date"
            ]].head(10).to_string(index=False)
        )

    merged.drop(columns=["date", "_merge", "merge_date", "merge_district"], inplace=True)
    merged.to_csv(OUTPUT_FILE, index=False)

    print("\nMerge summary")
    print("Original dengue rows:", len(dengue))
    print("Rows merged:", len(merged))
    print("Dengue rows saved for district review:", len(unmatched))
    print("Rows without weather match:", int(unmatched_dates.sum()))
    print("Merged rows with missing weather values:",
          int(merged[["temperature_c", "relative_humidity_pct", "rainfall_mm"]].isna().any(axis=1).sum()))
    print("Output:", OUTPUT_FILE)
    print("Review file:", REVIEW_FILE)

if __name__ == "__main__":
    main()
