from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "processed" / "dengue_weather_merged.csv"


def get_district_history(district_id: str):
    if not DATA_FILE.exists():
        return {
            "district_id": district_id,
            "records": [],
            "data_status": "unavailable",
            "message": "Processed dengue dataset not found",
            "data_as_of": None,
        }

    df = pd.read_csv(DATA_FILE)

    required = {
        "district_census2011",
        "metadata.recordDate",
        "daily_positive_total",
    }

    if not required.issubset(df.columns):
        return {
            "district_id": district_id,
            "records": [],
            "data_status": "unavailable",
            "message": "Dataset is missing required history columns",
            "data_as_of": None,
        }

    df["date"] = pd.to_datetime(
        df["metadata.recordDate"], errors="coerce"
    )
    df["district_key"] = (
        df["district_census2011"].astype(str).str.strip().str.lower()
    )

    aliases = {
        "belagavi": "belgaum",
        "bengaluru-rural": "bangalore rural",
        "bengaluru-urban": "bangalore",
        "mysuru": "mysore",
        "shivamogga": "shimoga",
        "tumakuru": "tumkur",
    }

    requested = district_id.strip().lower()
    district_key = aliases.get(requested, requested)

    district_df = df[df["district_key"] == district_key].copy()
    district_df = district_df.dropna(subset=["date"])

    if district_df.empty:
        return {
            "district_id": district_id,
            "records": [],
            "data_status": "unavailable",
            "message": "No matching district history found in the dataset",
            "data_as_of": None,
        }

    district_df["daily_positive_total"] = pd.to_numeric(
        district_df["daily_positive_total"], errors="coerce"
    )

    monthly = (
        district_df.dropna(subset=["daily_positive_total"])
        .assign(month=lambda x: x["date"].dt.to_period("M").astype(str))
        .groupby("month", as_index=False)["daily_positive_total"]
        .sum()
        .sort_values("month")
    )

    records = [
        {
            "month": row["month"],
            "cases": int(row["daily_positive_total"]),
            "source": "processed_dengue_dataset",
        }
        for _, row in monthly.iterrows()
    ]

    return {
        "district_id": district_id,
        "records": records,
        "data_status": "historical_data",
        "data_as_of": datetime.now(timezone.utc).isoformat(),
    }
