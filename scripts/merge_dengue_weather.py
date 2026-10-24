"""Join daily dengue reports to historical weather using district and date."""

from pathlib import Path

import pandas as pd

try:
    from .district_aliases import canonical_district_id
except ImportError:  # Support ``python scripts/merge_dengue_weather.py``.
    from district_aliases import canonical_district_id


ROOT = Path(__file__).resolve().parent.parent

DENGUE_FILE = ROOT / "data" / "processed" / "dengue_karnataka_clean.csv"
WEATHER_FILE = ROOT / "data" / "processed" / "karnataka_district_weather.csv"
OUTPUT_FILE = ROOT / "data" / "processed" / "dengue_weather_merged.csv"
REVIEW_FILE = ROOT / "data" / "processed" / "dengue_weather_unmatched_dengue.csv"

DENGUE_DATE = "metadata.recordDate"
DENGUE_DISTRICT = "district_census2011"
WEATHER_DATE = "date"
WEATHER_DISTRICT = "district_name"
WEATHER_COLUMNS = ["temperature_c", "relative_humidity_pct", "rainfall_mm"]


def merge_dengue_with_weather(dengue, weather):
    """Left-join all dengue rows to weather on canonical district and exact date.

    Unmatched dengue rows are retained with null weather fields. In particular,
    Vijayanagara is not merged into Ballari when its weather series is absent.
    """
    required_dengue = {DENGUE_DATE, DENGUE_DISTRICT}
    required_weather = {WEATHER_DATE, WEATHER_DISTRICT, *WEATHER_COLUMNS}
    if not required_dengue.issubset(dengue.columns):
        raise ValueError(f"Dengue input missing columns: {sorted(required_dengue - set(dengue.columns))}")
    if not required_weather.issubset(weather.columns):
        raise ValueError(f"Weather input missing columns: {sorted(required_weather - set(weather.columns))}")

    dengue_rows = dengue.drop(columns=WEATHER_COLUMNS, errors="ignore").copy()
    weather_rows = weather[[WEATHER_DATE, WEATHER_DISTRICT, *WEATHER_COLUMNS]].copy()

    dengue_rows["_district_id"] = dengue_rows[DENGUE_DISTRICT].map(canonical_district_id)
    weather_rows["_district_id"] = weather_rows[WEATHER_DISTRICT].map(canonical_district_id)
    dengue_rows["_exact_date"] = pd.to_datetime(dengue_rows[DENGUE_DATE], errors="coerce").dt.normalize()
    weather_rows["_exact_date"] = pd.to_datetime(weather_rows[WEATHER_DATE], errors="coerce").dt.normalize()

    weather_keys = weather_rows.dropna(subset=["_district_id", "_exact_date"])
    duplicate_weather = weather_keys.duplicated(["_district_id", "_exact_date"], keep=False)
    if duplicate_weather.any():
        examples = weather_keys.loc[duplicate_weather, [WEATHER_DISTRICT, WEATHER_DATE]].head(5)
        raise ValueError(
            "Weather contains duplicate canonical district-date keys:\n"
            f"{examples.to_string(index=False)}"
        )

    dengue_keys = dengue_rows.dropna(subset=["_district_id", "_exact_date"])
    duplicate_dengue = dengue_keys.duplicated(["_district_id", "_exact_date"], keep=False)
    if duplicate_dengue.any():
        examples = dengue_keys.loc[duplicate_dengue, [DENGUE_DISTRICT, DENGUE_DATE]].head(5)
        raise ValueError(
            "Dengue contains duplicate canonical district-date keys; resolve them "
            "from the source before aggregation:\n"
            f"{examples.to_string(index=False)}"
        )

    # Avoid pandas matching null join keys to one another. Unknown district or
    # invalid-date records remain in the left-side output and receive no weather.
    weather_keys = weather_keys.rename(columns={WEATHER_DISTRICT: "_weather_district", WEATHER_DATE: "_weather_date"})
    merged = dengue_rows.merge(
        weather_keys[["_district_id", "_exact_date", *WEATHER_COLUMNS]],
        on=["_district_id", "_exact_date"],
        how="left",
        validate="many_to_one",
        indicator="_weather_merge",
    )

    merged["district_id"] = merged["_district_id"]
    merged["weather_match_status"] = "matched"
    merged.loc[merged["_district_id"].isna(), "weather_match_status"] = "unknown_district_name"
    merged.loc[merged["_exact_date"].isna(), "weather_match_status"] = "invalid_or_missing_date"
    merged.loc[
        merged["_district_id"].notna()
        & merged["_exact_date"].notna()
        & merged["_weather_merge"].eq("left_only"),
        "weather_match_status",
    ] = "no_exact_weather_match"
    return merged.drop(columns=["_district_id", "_exact_date", "_weather_merge"])


def main():
    dengue = pd.read_csv(DENGUE_FILE, low_memory=False)
    weather = pd.read_csv(WEATHER_FILE, low_memory=False)
    merged = merge_dengue_with_weather(dengue, weather)

    unmatched = merged[merged["weather_match_status"] != "matched"].copy()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUTPUT_FILE, index=False)
    unmatched.to_csv(REVIEW_FILE, index=False)

    print("\nDaily merge summary")
    print("Dengue rows retained:", len(merged))
    print("Canonical dengue districts:", merged["district_id"].nunique(dropna=True))
    print("Matched rows:", int(merged["weather_match_status"].eq("matched").sum()))
    print("Unmatched rows by reason:")
    print(merged.loc[merged["weather_match_status"] != "matched", "weather_match_status"].value_counts().to_string())
    if not unmatched.empty:
        print("Unmatched districts:")
        print(unmatched[DENGUE_DISTRICT].value_counts(dropna=False).to_string())
    print("Weather values missing by column:")
    print(merged[WEATHER_COLUMNS].isna().sum().to_string())
    print("Output:", OUTPUT_FILE)
    print("Review file:", REVIEW_FILE)


if __name__ == "__main__":
    main()
