"""Prepare complete district-month dengue/weather rows and next-month labels.

Monthly case totals are emitted only when every calendar day has a valid
reported dengue value and aligned weather values. Missing reporting days are
never interpreted as zero. The target describes reported-case change, not an
outbreak or clinical risk.
"""

from pathlib import Path

import pandas as pd

try:
    from .district_aliases import CANONICAL_DISTRICT_NAMES, canonical_district_id
except ImportError:  # Support ``python scripts/prepare_district_month_data.py``.
    from district_aliases import CANONICAL_DISTRICT_NAMES, canonical_district_id


ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "data" / "processed" / "dengue_weather_merged.csv"
UNMATCHED_FILE = ROOT / "data" / "processed" / "dengue_weather_unmatched_dengue.csv"
MONTHLY_OUTPUT = ROOT / "data" / "processed" / "dengue_district_month.csv"
TARGET_OUTPUT = ROOT / "data" / "processed" / "dengue_district_month_targets.csv"
EXCLUSIONS_OUTPUT = ROOT / "data" / "processed" / "dengue_district_month_exclusions.csv"
RECORD_EXCLUSIONS_OUTPUT = ROOT / "data" / "processed" / "dengue_district_month_record_exclusions.csv"

DATE_COLUMN = "metadata.recordDate"
DISTRICT_COLUMN = "district_census2011"
CASE_COLUMN = "daily_positive_total"
WEATHER_COLUMNS = ["temperature_c", "relative_humidity_pct", "rainfall_mm"]

MONTH_FEATURE_COLUMNS = [
    "reported_dengue_total",
    "mean_temperature_c",
    "mean_relative_humidity_pct",
    "total_rainfall_mm",
]
TARGET_COLUMN = "target_reported_case_increase_next_month"


def _require_columns(frame, required, label):
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} input missing columns: {missing}")


def _finite_numeric(series):
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.where(numeric.map(lambda value: pd.notna(value) and abs(value) != float("inf")))


def _append_unmatched_rows(daily, unmatched_dengue):
    """Add review-file case rows not already retained in the merged daily file."""
    if unmatched_dengue is None or unmatched_dengue.empty:
        return daily

    _require_columns(unmatched_dengue, [DATE_COLUMN, DISTRICT_COLUMN, CASE_COLUMN], "unmatched dengue")
    columns = [DATE_COLUMN, DISTRICT_COLUMN, CASE_COLUMN, *WEATHER_COLUMNS]
    daily = daily[columns].copy()
    extra = unmatched_dengue[[DATE_COLUMN, DISTRICT_COLUMN, CASE_COLUMN]].copy()
    for column in WEATHER_COLUMNS:
        extra[column] = float("nan")

    existing_districts = daily[DISTRICT_COLUMN].map(canonical_district_id)
    existing_dates = pd.to_datetime(daily[DATE_COLUMN], errors="coerce").dt.normalize()
    existing_valid = existing_districts.notna() & existing_dates.notna()
    existing_keys = set(zip(existing_districts[existing_valid], existing_dates[existing_valid]))
    extra_dates = pd.to_datetime(extra[DATE_COLUMN], errors="coerce").dt.normalize()
    extra_districts = extra[DISTRICT_COLUMN].map(canonical_district_id)
    duplicate_in_daily = pd.Series(
        [
            (district, date) in existing_keys if district is not None and pd.notna(date) else False
            for district, date in zip(extra_districts, extra_dates)
        ],
        index=extra.index,
    )
    extra = extra.loc[~duplicate_in_daily, columns].copy()
    return pd.concat([daily, extra], ignore_index=True)


def prepare_district_month_data(daily_frame, unmatched_dengue=None):
    """Return complete months, eligible next-month targets, and exclusions.

    The prediction cutoff for a row is the end of its ``month``. Features use
    only that month's reported total and weather. The next complete month is
    used only to construct the target label.
    """
    _require_columns(
        daily_frame,
        [DATE_COLUMN, DISTRICT_COLUMN, CASE_COLUMN, *WEATHER_COLUMNS],
        "merged daily",
    )

    daily = daily_frame[[DATE_COLUMN, DISTRICT_COLUMN, CASE_COLUMN, *WEATHER_COLUMNS]].copy()
    daily["_district_id"] = daily[DISTRICT_COLUMN].map(canonical_district_id)
    daily["_date"] = pd.to_datetime(daily[DATE_COLUMN], errors="coerce").dt.normalize()
    daily = _append_unmatched_rows(daily, unmatched_dengue)

    # Recompute normalized keys after review rows have been appended.
    daily["_district_id"] = daily[DISTRICT_COLUMN].map(canonical_district_id)
    daily["_date"] = pd.to_datetime(daily[DATE_COLUMN], errors="coerce").dt.normalize()

    valid_keys = daily["_district_id"].notna() & daily["_date"].notna()
    duplicate_keys = daily.loc[valid_keys].duplicated(["_district_id", "_date"], keep=False)
    if duplicate_keys.any():
        sample = daily.loc[valid_keys].loc[duplicate_keys, [DISTRICT_COLUMN, DATE_COLUMN]].head(5)
        raise ValueError(
            "Daily input contains duplicate canonical district-date keys; "
            "resolve source rows before monthly aggregation:\n"
            f"{sample.to_string(index=False)}"
        )

    daily[CASE_COLUMN] = _finite_numeric(daily[CASE_COLUMN])
    for column in WEATHER_COLUMNS:
        daily[column] = _finite_numeric(daily[column])

    daily["_case_valid"] = daily[CASE_COLUMN].notna() & daily[CASE_COLUMN].ge(0)
    daily["_weather_valid"] = (
        daily[WEATHER_COLUMNS].notna().all(axis=1)
        & daily["relative_humidity_pct"].between(0, 100)
        & daily["rainfall_mm"].ge(0)
    )

    record_exclusions = []
    excluded_record_mask = (
        daily["_date"].isna()
        | daily["_district_id"].isna()
        | ~daily["_case_valid"]
        | ~daily["_weather_valid"]
    )
    for index, row in daily.loc[excluded_record_mask].iterrows():
        reasons = []
        if pd.isna(row["_date"]):
            reasons.append("invalid_or_missing_date")
        if pd.isna(row["_district_id"]):
            reasons.append("unknown_district_name")
        if pd.notna(row["_date"]) and pd.notna(row["_district_id"]):
            if not row["_case_valid"]:
                reasons.append("missing_or_invalid_disease_value")
            if not row["_weather_valid"]:
                reasons.append("no_matched_weather_series" if row["_district_id"] == "vijayanagara" else "missing_or_invalid_weather")
        if reasons:
            record_exclusions.append({
                "source_row": index,
                "district_id": row["_district_id"],
                "date": row["_date"],
                "reason": ";".join(reasons),
            })
    record_exclusions = pd.DataFrame(
        record_exclusions,
        columns=["source_row", "district_id", "date", "reason"],
    )

    usable_calendar_rows = daily.loc[valid_keys].copy()
    if usable_calendar_rows.empty:
        empty_monthly = pd.DataFrame(columns=["district_id", "district_name", "month", *MONTH_FEATURE_COLUMNS])
        empty_targets = pd.DataFrame(columns=["district_id", "district_name", "month", "target_month", TARGET_COLUMN])
        empty_month_exclusions = pd.DataFrame(columns=["district_id", "district_name", "month", "reason"])
        summary = {
            "source_rows": len(daily),
            "source_district_count": 0,
            "complete_month_count": 0,
            "complete_month_district_count": 0,
            "target_count": 0,
            "target_district_count": 0,
            "target_class_counts": {0: 0, 1: 0},
            "date_min": None,
            "date_max": None,
            "missing_counts": {
                column: int(daily[column].isna().sum())
                for column in [DATE_COLUMN, DISTRICT_COLUMN, CASE_COLUMN, *WEATHER_COLUMNS]
            },
            "parsed_date_failures": int(daily["_date"].isna().sum()),
            "unrecognized_district_names": int(daily["_district_id"].isna().sum()),
            "record_exclusions": record_exclusions,
        }
        return empty_monthly, empty_targets, empty_month_exclusions, record_exclusions, summary

    data_as_of = usable_calendar_rows["_date"].max()
    month_records = []
    month_exclusions = []

    for district_id, district_rows in usable_calendar_rows.groupby("_district_id", sort=True):
        district_rows = district_rows.copy()
        district_rows["_month"] = district_rows["_date"].dt.to_period("M")
        first_month = district_rows["_month"].min()
        last_month = district_rows["_month"].max()
        rows_by_month = {period: frame for period, frame in district_rows.groupby("_month")}

        for period in pd.period_range(first_month, last_month, freq="M"):
            month_rows = rows_by_month.get(period, district_rows.iloc[0:0])
            expected_days = period.days_in_month
            observed_days = int(month_rows["_date"].nunique())
            valid_case_days = int(month_rows.loc[month_rows["_case_valid"], "_date"].nunique())
            valid_weather_days = int(month_rows.loc[month_rows["_weather_valid"], "_date"].nunique())

            reasons = []
            if period.end_time.normalize() > data_as_of:
                reasons.append("month_not_complete_at_dataset_cutoff")
            if observed_days < expected_days:
                reasons.append("missing_calendar_reporting_days")
            if valid_case_days < expected_days:
                reasons.append("missing_or_invalid_disease_values")
            if valid_weather_days < expected_days:
                if district_id == "vijayanagara" and valid_weather_days == 0:
                    reasons.append("no_matched_weather_series")
                else:
                    reasons.append("missing_or_invalid_weather_days")

            complete = not reasons
            item = {
                "district_id": district_id,
                "district_name": CANONICAL_DISTRICT_NAMES[district_id],
                "month": str(period),
                "prediction_cutoff": period.end_time.normalize().date().isoformat(),
                "calendar_days": expected_days,
                "reporting_days": observed_days,
                "valid_disease_days": valid_case_days,
                "valid_weather_days": valid_weather_days,
                "month_complete": complete,
                "exclusion_reason": ";".join(dict.fromkeys(reasons)),
            }

            # Do not expose partial sums/means as monthly metrics.
            if complete:
                item.update({
                    "reported_dengue_total": float(month_rows[CASE_COLUMN].sum()),
                    "mean_temperature_c": float(month_rows["temperature_c"].mean()),
                    "mean_relative_humidity_pct": float(month_rows["relative_humidity_pct"].mean()),
                    "total_rainfall_mm": float(month_rows["rainfall_mm"].sum()),
                })
                month_records.append(item)
            else:
                month_exclusions.append(item)

    complete_monthly = pd.DataFrame(month_records)
    if not complete_monthly.empty:
        complete_monthly["_period"] = pd.PeriodIndex(complete_monthly["month"], freq="M")
        complete_monthly = complete_monthly.sort_values(["district_id", "_period"]).reset_index(drop=True)
    else:
        complete_monthly = pd.DataFrame(columns=[
            "district_id",
            "district_name",
            "month",
            "prediction_cutoff",
            "calendar_days",
            "reporting_days",
            "valid_disease_days",
            "valid_weather_days",
            "month_complete",
            "exclusion_reason",
            *MONTH_FEATURE_COLUMNS,
        ])

    # Build labels only from adjacent, complete months. Future values are read
    # here for the target comparison and are not copied into feature columns.
    targets = []
    for district_id, group in complete_monthly.groupby("district_id", sort=True):
        by_period = {row["_period"]: row for _, row in group.iterrows()}
        for period, current in by_period.items():
            next_period = period + 1
            future = by_period.get(next_period)
            if future is None:
                continue
            target = int(future["reported_dengue_total"] > current["reported_dengue_total"])
            target_row = {
                "district_id": district_id,
                "district_name": current["district_name"],
                "month": str(period),
                "target_month": str(next_period),
                "prediction_cutoff": current["prediction_cutoff"],
            }
            target_row.update({column: current[column] for column in MONTH_FEATURE_COLUMNS})
            target_row[TARGET_COLUMN] = target
            targets.append(target_row)

    target_frame = pd.DataFrame(targets)
    month_exclusions_frame = pd.DataFrame(month_exclusions)
    if not complete_monthly.empty:
        complete_monthly = complete_monthly.drop(columns="_period")

    target_counts = (
        target_frame[TARGET_COLUMN].value_counts().to_dict()
        if not target_frame.empty
        else {}
    )
    summary = {
        "source_rows": len(daily),
        "source_district_count": int(usable_calendar_rows["_district_id"].nunique()),
        "complete_month_count": len(complete_monthly),
        "complete_month_district_count": int(complete_monthly["district_id"].nunique()) if not complete_monthly.empty else 0,
        "target_count": len(target_frame),
        "target_district_count": int(target_frame["district_id"].nunique()) if not target_frame.empty else 0,
        "target_class_counts": {0: int(target_counts.get(0, 0)), 1: int(target_counts.get(1, 0))},
        "date_min": usable_calendar_rows["_date"].min().date().isoformat(),
        "date_max": data_as_of.date().isoformat(),
        "missing_counts": {
            column: int(daily[column].isna().sum())
            for column in [DATE_COLUMN, DISTRICT_COLUMN, CASE_COLUMN, *WEATHER_COLUMNS]
        },
        "parsed_date_failures": int(daily["_date"].isna().sum()),
        "unrecognized_district_names": int(daily["_district_id"].isna().sum()),
        "record_exclusions": record_exclusions,
        "month_exclusions": month_exclusions_frame,
    }
    return complete_monthly, target_frame, month_exclusions_frame, record_exclusions, summary


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Merged dengue/weather dataset not found: {INPUT_FILE}")

    daily = pd.read_csv(INPUT_FILE, low_memory=False)
    unmatched = pd.read_csv(UNMATCHED_FILE, low_memory=False) if UNMATCHED_FILE.exists() else None
    monthly, targets, month_exclusions, record_exclusions, summary = prepare_district_month_data(daily, unmatched)

    MONTHLY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(MONTHLY_OUTPUT, index=False)
    targets.to_csv(TARGET_OUTPUT, index=False)
    month_exclusions.to_csv(EXCLUSIONS_OUTPUT, index=False)
    record_exclusions.to_csv(RECORD_EXCLUSIONS_OUTPUT, index=False)

    print("=== District-month dengue/weather preparation ===")
    print("Input rows:", summary["source_rows"])
    print("Recognized districts in source:", summary.get("source_district_count", 0))
    print("Date range:", summary.get("date_min", "unavailable"), "to", summary.get("date_max", "unavailable"))
    print("Missing values by input field:")
    print(pd.Series(summary.get("missing_counts", {})).to_string())
    print("Unparseable dates:", summary["parsed_date_failures"])
    print("Unrecognized district names:", summary["unrecognized_district_names"])
    print("Complete district-month rows:", summary["complete_month_count"])
    print("Districts with complete months:", summary["complete_month_district_count"])
    if not monthly.empty:
        print("Complete months by district:")
        print(monthly.groupby("district_name").size().sort_index().to_string())
    print("District-month target rows:", summary["target_count"])
    print("Districts with target rows:", summary["target_district_count"])
    if not targets.empty:
        print("Target rows by district:")
        print(targets.groupby("district_name").size().sort_index().to_string())
    print("Target class counts (0=no increase, 1=reported-case increase):", summary["target_class_counts"])
    print("Excluded source-record reasons:")
    if record_exclusions.empty:
        print("None")
    else:
        print(record_exclusions["reason"].str.split(";").explode().value_counts().to_string())
    print("Excluded district-month reasons:")
    if month_exclusions.empty:
        print("None")
    else:
        print(month_exclusions["exclusion_reason"].str.split(";").explode().value_counts().to_string())
    print("Excluded district-month rows:", len(month_exclusions))
    print("Monthly dataset:", MONTHLY_OUTPUT)
    print("Target dataset:", TARGET_OUTPUT)
    print("Excluded month report:", EXCLUSIONS_OUTPUT)
    print("Excluded source-record report:", RECORD_EXCLUSIONS_OUTPUT)
    print("Target semantics: reported total in the next complete month exceeds the current complete month; not a confirmed outbreak.")


if __name__ == "__main__":
    main()
