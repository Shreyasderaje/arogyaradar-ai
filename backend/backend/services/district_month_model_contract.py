"""Request/response contract for the evaluated district-month model.

This module validates proposed inputs and data availability. It does not load a
model or calculate predictions; FastAPI uses it to return honest support states.
"""

from dataclasses import asdict, dataclass
import calendar
from datetime import date, datetime, timedelta
import math
import re
from typing import Literal


MODEL_VERSION = "district-month-logistic-regression-eval-v1"
FEATURE_SCHEMA_VERSION = "district-month-features-v1"
TARGET_DEFINITION = (
    "1 when the complete next calendar month's reported dengue total is greater "
    "than the current complete month's total; this is not a confirmed outbreak prediction."
)
TRAINING_METADATA = {
    "training_rows": 391,
    "training_label_counts": {"0": 208, "1": 183},
    "last_feature_month": "2022-10",
    "last_prediction_cutoff": "2022-10-31",
    "last_target_month": "2022-11",
    "last_target_observation_end": "2022-11-30",
    "full_feature_coverage": {"first_month": "2021-01", "last_month": "2024-01"},
    "full_label_coverage": {
        "current_month_first": "2021-01",
        "current_month_last": "2023-04",
        "target_month_first": "2021-02",
        "target_month_last": "2023-05",
    },
    "evaluation_holdout_target_months": ["2022-12", "2023-03", "2023-04", "2023-05"],
    "artifact_available": False,
}

FEATURE_SCHEMA = (
    {
        "name": "reported_dengue_total",
        "type": "number",
        "unit": "reported cases",
        "availability": "sum from a complete current calendar month, at month-end cutoff",
    },
    {
        "name": "mean_temperature_c",
        "type": "number",
        "unit": "degrees Celsius",
        "availability": "mean aligned daily weather over the complete current month",
    },
    {
        "name": "mean_relative_humidity_pct",
        "type": "number",
        "unit": "percent",
        "availability": "mean aligned daily weather over the complete current month",
    },
    {
        "name": "total_rainfall_mm",
        "type": "number",
        "unit": "millimeters",
        "availability": "sum aligned daily weather over the complete current month",
    },
)
FEATURE_NAMES = tuple(item["name"] for item in FEATURE_SCHEMA)
MODEL_TRANSFORMATIONS = (
    "SimpleImputer(strategy='median'), fit on training partition only",
    "StandardScaler(), fit on training partition only",
    "LogisticRegression(C=1.0, class_weight='balanced', max_iter=2000, random_state=42)",
)
_DISTRICT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_RESPONSE_STATUSES = {"supported", "unavailable", "not_current", "unknown_district", "model_unavailable"}


@dataclass(frozen=True)
class DistrictMonthPredictionRequest:
    """One current, complete district-month request; no feature values supplied by caller."""

    district_id: str
    current_month: str

    @classmethod
    def from_mapping(cls, payload):
        if not isinstance(payload, dict):
            raise ValueError("Request must be a JSON object")
        missing = {"district_id", "current_month"} - payload.keys()
        if missing:
            raise ValueError(f"Missing request fields: {sorted(missing)}")
        district_id = payload["district_id"]
        current_month = payload["current_month"]
        if not isinstance(district_id, str) or not _DISTRICT_ID_RE.fullmatch(district_id):
            raise ValueError("district_id must be a canonical lowercase district slug")
        if not isinstance(current_month, str) or not _MONTH_RE.fullmatch(current_month):
            raise ValueError("current_month must use YYYY-MM and be a valid calendar month")
        # The regex checks month bounds; strptime also rejects impossible years.
        try:
            datetime.strptime(current_month, "%Y-%m")
        except ValueError as exc:
            raise ValueError("current_month must be a valid calendar month") from exc
        return cls(district_id=district_id, current_month=current_month)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class DistrictMonthPredictionResponse:
    district_id: str
    current_month: str
    target_month: str
    prediction_cutoff: str
    status: Literal["supported", "unavailable", "not_current", "unknown_district", "model_unavailable"]
    prediction_supported: bool
    prediction: int | None
    probability_of_reported_case_increase: float | None
    model_version: str
    feature_schema_version: str
    target_definition: str
    health_data_as_of: str | None
    message: str

    def __post_init__(self):
        if self.status not in _RESPONSE_STATUSES:
            raise ValueError(f"Unsupported response status: {self.status}")
        if self.prediction_supported != (self.status == "supported"):
            raise ValueError("prediction_supported must agree with status")
        if self.status == "supported":
            if self.prediction not in (0, 1) or self.probability_of_reported_case_increase is None:
                raise ValueError("A supported response requires a binary prediction and probability")
            if not 0 <= self.probability_of_reported_case_increase <= 1:
                raise ValueError("Probability must be between 0 and 1")
        elif self.prediction is not None or self.probability_of_reported_case_increase is not None:
            raise ValueError("Unsupported responses must not include prediction values")

    def to_dict(self):
        return asdict(self)


def _month_end(month):
    year, month_number = (int(part) for part in month.split("-"))
    if month_number == 12:
        return date(year, 12, 31)
    return date(year, month_number + 1, 1) - timedelta(days=1)


def _month_number(month):
    year, month_number = (int(part) for part in month.split("-"))
    return year * 12 + month_number


def build_feature_values(record):
    """Return the exact training feature order; reject missing or invalid values."""
    if not isinstance(record, dict):
        raise ValueError("Feature record must be an object")
    missing = set(FEATURE_NAMES) - record.keys()
    if missing:
        raise ValueError(f"Missing model features: {sorted(missing)}")
    values = {}
    for name in FEATURE_NAMES:
        value = record[name]
        if isinstance(value, bool):
            raise ValueError(f"Feature {name} must be numeric")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Feature {name} must be numeric") from exc
        if not math.isfinite(number):
            raise ValueError(f"Feature {name} must be finite")
        values[name] = number
    if values["reported_dengue_total"] < 0 or values["total_rainfall_mm"] < 0:
        raise ValueError("Reported total and rainfall cannot be negative")
    if not 0 <= values["mean_relative_humidity_pct"] <= 100:
        raise ValueError("Mean relative humidity must be between 0 and 100")
    return values


def is_complete_district_month_record(record):
    """Validate the prepared monthly row and its date/count completeness fields."""
    if not isinstance(record, dict):
        return False
    month = record.get("month")
    if not isinstance(month, str) or not _MONTH_RE.fullmatch(month):
        return False
    try:
        datetime.strptime(month, "%Y-%m")
        year, month_number = (int(part) for part in month.split("-"))
        calendar_days = int(record["calendar_days"])
        complete_flag = record["month_complete"] in (True, 1, "True", "true")
        if not (
            complete_flag
            and calendar_days == calendar.monthrange(year, month_number)[1]
            and int(record["reporting_days"]) == calendar_days
            and int(record["valid_disease_days"]) == calendar_days
            and int(record["valid_weather_days"]) == calendar_days
            and record.get("prediction_cutoff") == _month_end(month).isoformat()
        ):
            return False
        build_feature_values(record)
    except (KeyError, TypeError, ValueError):
        return False
    return True


def assess_prediction_request(
    request,
    *,
    known_district_ids,
    today,
    latest_complete_month,
    health_data_as_of,
    district_month_record,
    model_available=False,
    prediction=None,
    probability=None,
):
    """Build an honest response from validated current-month inputs.

    No model is loaded here. ``model_available`` and outputs are reserved for a
    future inference adapter; by default the candidate remains unavailable.
    """
    if not isinstance(request, DistrictMonthPredictionRequest):
        raise TypeError("request must be a validated DistrictMonthPredictionRequest")
    current_year, current_month_number = (int(part) for part in request.current_month.split("-"))
    if current_month_number == 12:
        target_year, target_month_number = current_year + 1, 1
    else:
        target_year, target_month_number = current_year, current_month_number + 1
    target_month = f"{target_year:04d}-{target_month_number:02d}"
    cutoff = _month_end(request.current_month).isoformat()

    def response(status, message, data_as_of=None, output=None):
        output = output or {}
        return DistrictMonthPredictionResponse(
            district_id=request.district_id,
            current_month=request.current_month,
            target_month=target_month,
            prediction_cutoff=cutoff,
            status=status,
            prediction_supported=status == "supported",
            prediction=output.get("prediction"),
            probability_of_reported_case_increase=output.get("probability"),
            model_version=MODEL_VERSION,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            target_definition=TARGET_DEFINITION,
            health_data_as_of=data_as_of,
            message=message,
        )

    if request.district_id not in set(known_district_ids):
        return response("unknown_district", "District is not in the configured district registry.")

    today_month = f"{today.year:04d}-{today.month:02d}"
    target_number = _month_number(target_month)
    today_number = _month_number(today_month)
    if target_number < today_number:
        return response("not_current", "Requested target month is historical; this interface does not present backtests as current forecasts.", health_data_as_of)
    if target_number > today_number + 1:
        return response("unavailable", "Requested target month is beyond the next calendar month.", health_data_as_of)
    if not latest_complete_month:
        return response("unavailable", "No validated complete health-data month is available.")
    try:
        if not _MONTH_RE.fullmatch(latest_complete_month):
            raise ValueError("invalid month")
        latest_month_number = _month_number(latest_complete_month)
    except (AttributeError, TypeError, ValueError):
        return response("unavailable", "The latest complete health-data month is invalid.")
    if latest_month_number < _month_number(request.current_month):
        return response("not_current", "Health data does not cover the requested complete month.", health_data_as_of)
    if latest_month_number > _month_number(request.current_month):
        return response("not_current", "A newer complete health-data month is available; the request is not based on the latest month.", health_data_as_of)
    if today < _month_end(request.current_month):
        return response("unavailable", "Current-month features require a complete calendar month.", health_data_as_of)
    if target_number == today_number + 1 and today != _month_end(request.current_month):
        return response("unavailable", "A next-month forecast is only eligible at the current-month cutoff.", health_data_as_of)
    try:
        data_as_of_date = date.fromisoformat(health_data_as_of)
    except (TypeError, ValueError):
        return response("unavailable", "A verifiable health-data as-of date is unavailable.")
    if data_as_of_date < _month_end(request.current_month):
        return response("not_current", "Health data does not cover the requested complete month.", health_data_as_of)

    record = district_month_record
    if not isinstance(record, dict):
        return response("unavailable", "No complete health and weather feature row exists for this district and month.", health_data_as_of)
    if record.get("district_id") != request.district_id or record.get("month") != request.current_month:
        return response("unavailable", "The available feature row does not match the requested district and month.", health_data_as_of)
    if not is_complete_district_month_record(record):
        return response("unavailable", "District-month health and aligned weather data is missing or incomplete.", health_data_as_of)

    if not model_available:
        return response("model_unavailable", "Current features are complete, but no candidate model artifact is available.", health_data_as_of)
    if prediction not in (0, 1) or probability is None:
        raise ValueError("Supported status requires model output")
    output = {"prediction": int(prediction), "probability": float(probability)}
    return response("supported", "A model output is available for complete current-month features.", health_data_as_of, output)
