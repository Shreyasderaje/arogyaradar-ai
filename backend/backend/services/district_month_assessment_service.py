"""Data adapter for the district-month assessment route.

Only the prepared complete-month CSV is accepted. This service never derives
model inputs from partial history totals or current Open-Meteo readings.
"""

from pathlib import Path

import pandas as pd

from services.district_month_model_contract import (
    DistrictMonthPredictionRequest,
    assess_prediction_request,
    is_complete_district_month_record,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FEATURE_DATA_FILE = PROJECT_ROOT / "data" / "processed" / "dengue_district_month.csv"
CANDIDATE_MODEL_AVAILABLE = False


def _load_validated_month_rows():
    """Return validated complete rows and source date, or no evidence on failure."""
    if not FEATURE_DATA_FILE.is_file():
        return [], None
    try:
        frame = pd.read_csv(FEATURE_DATA_FILE, low_memory=False)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError):
        return [], None
    records = frame.to_dict(orient="records")
    valid = [row for row in records if is_complete_district_month_record(row)]
    if not valid:
        return [], None
    latest = max(valid, key=lambda row: row["month"])
    return valid, latest["prediction_cutoff"]


def assess_district_month_request(payload, *, known_district_ids, today):
    """Apply the contract against verified monthly rows; do not run any model."""
    request = DistrictMonthPredictionRequest.from_mapping(payload)

    # Unknown IDs can be answered without reading potentially unavailable data.
    known_district_ids = set(known_district_ids)
    if request.district_id not in known_district_ids:
        return assess_prediction_request(
            request,
            known_district_ids=known_district_ids,
            today=today,
            latest_complete_month=None,
            health_data_as_of=None,
            district_month_record=None,
            model_available=False,
        )

    records, _ = _load_validated_month_rows()
    district_records = [row for row in records if row.get("district_id") == request.district_id]
    latest_district_record = max(district_records, key=lambda row: row["month"], default=None)
    latest_complete_month = latest_district_record["month"] if latest_district_record else None
    health_data_as_of = latest_district_record["prediction_cutoff"] if latest_district_record else None
    district_month_rows = [row for row in district_records if row.get("month") == request.current_month]
    # Duplicate district-month entries are ambiguous and fail closed.
    month_record = district_month_rows[0] if len(district_month_rows) == 1 else None

    return assess_prediction_request(
        request,
        known_district_ids=known_district_ids,
        today=today,
        latest_complete_month=latest_complete_month,
        health_data_as_of=health_data_as_of,
        district_month_record=month_record,
        model_available=CANDIDATE_MODEL_AVAILABLE,
    )
