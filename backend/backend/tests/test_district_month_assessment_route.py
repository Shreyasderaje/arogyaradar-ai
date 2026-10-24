import calendar
import csv
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import DISTRICTS, app
from services import district_month_assessment_service as assessment_service


client = TestClient(app)


def month_before(month):
    year, month_number = (int(part) for part in month.split("-"))
    if month_number == 1:
        year -= 1
        month_number = 12
    else:
        month_number -= 1
    return f"{year:04d}-{month_number:02d}"


def complete_row(district_id, month):
    year, month_number = (int(part) for part in month.split("-"))
    days = calendar.monthrange(year, month_number)[1]
    cutoff = f"{month}-{days:02d}"
    return {
        "district_id": district_id,
        "district_name": "Mysuru",
        "month": month,
        "prediction_cutoff": cutoff,
        "calendar_days": days,
        "reporting_days": days,
        "valid_disease_days": days,
        "valid_weather_days": days,
        "month_complete": True,
        "reported_dengue_total": 12.0,
        "mean_temperature_c": 25.0,
        "mean_relative_humidity_pct": 70.0,
        "total_rainfall_mm": 42.0,
    }


def write_rows(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def current_month_feature_file(tmp_path, monkeypatch):
    current_target_month = f"{date.today().year:04d}-{date.today().month:02d}"
    feature_month = month_before(current_target_month)
    data_file = tmp_path / "district-month.csv"
    write_rows(data_file, [complete_row("mysuru", feature_month)])
    monkeypatch.setattr(assessment_service, "FEATURE_DATA_FILE", data_file)
    return feature_month, current_target_month


def test_new_versioned_route_returns_model_unavailable_without_candidate_artifact(current_month_feature_file):
    feature_month, target_month = current_month_feature_file
    payload = {"district_id": "mysuru", "current_month": feature_month}

    with patch("app.main.predict_early_warning", side_effect=AssertionError("legacy model must not run")):
        response = client.post("/api/v1/district-month/assess", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "model_unavailable"
    assert body["prediction_supported"] is False
    assert body["prediction"] is None
    assert body["probability_of_reported_case_increase"] is None
    assert body["current_month"] == feature_month
    assert body["target_month"] == target_month
    assert body["health_data_as_of"] == complete_row("mysuru", feature_month)["prediction_cutoff"]
    assert "/api/v1/district-month/assess" in app.openapi()["paths"]


@pytest.mark.parametrize("payload", [
    {"district_id": "mysuru"},
    {"district_id": "mysuru", "current_month": "2026-13"},
    {"district_id": "Mysuru", "current_month": "2026-10"},
])
def test_invalid_request_is_422(payload):
    response = client.post("/api/v1/district-month/assess", json=payload)
    assert response.status_code == 422


def test_unknown_registered_slug_returns_unknown_district_status():
    response = client.post("/api/v1/district-month/assess", json={
        "district_id": "yadgir",
        "current_month": f"{date.today().year:04d}-{date.today().month:02d}",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "unknown_district"
    assert response.json()["prediction"] is None


def test_stale_history_returns_not_current(tmp_path, monkeypatch):
    data_file = tmp_path / "stale.csv"
    write_rows(data_file, [complete_row("mysuru", "2024-01")])
    monkeypatch.setattr(assessment_service, "FEATURE_DATA_FILE", data_file)
    feature_month = month_before(f"{date.today().year:04d}-{date.today().month:02d}")

    response = client.post("/api/v1/district-month/assess", json={
        "district_id": "mysuru",
        "current_month": feature_month,
    })
    assert response.status_code == 200
    assert response.json()["status"] == "not_current"
    assert response.json()["prediction_supported"] is False
    assert response.json()["health_data_as_of"] == "2024-01-31"


def test_missing_health_dataset_returns_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(assessment_service, "FEATURE_DATA_FILE", tmp_path / "absent.csv")
    feature_month = month_before(f"{date.today().year:04d}-{date.today().month:02d}")

    response = client.post("/api/v1/district-month/assess", json={
        "district_id": "mysuru",
        "current_month": feature_month,
    })
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["health_data_as_of"] is None


def test_partial_month_row_is_not_used_as_feature_data(tmp_path, monkeypatch):
    feature_month = month_before(f"{date.today().year:04d}-{date.today().month:02d}")
    row = complete_row("mysuru", feature_month)
    row["valid_disease_days"] -= 1
    data_file = tmp_path / "partial.csv"
    write_rows(data_file, [row])
    monkeypatch.setattr(assessment_service, "FEATURE_DATA_FILE", data_file)

    response = client.post("/api/v1/district-month/assess", json={
        "district_id": "mysuru",
        "current_month": feature_month,
    })
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["prediction"] is None


def test_existing_endpoints_remain_available_and_old_prediction_route_is_not_replaced():
    assert client.get("/api/v1/health").status_code == 200
    districts = client.get("/api/v1/districts")
    assert districts.status_code == 200
    assert districts.json()["count"] == len(DISTRICTS) == 12
    score = client.get("/api/v1/districts/mysuru/score")
    assert score.status_code == 200
    assert score.json()["score"] is None
    assert score.json()["data_status"] == "unavailable"
    with patch("app.main.get_district_history", return_value={
        "district_id": "mysuru",
        "records": [],
        "data_status": "historical_data",
        "data_as_of": "source-derived-in-existing-endpoint",
    }):
        history = client.get("/api/v1/districts/mysuru/history")
    assert history.status_code == 200
    assert history.json()["data_status"] == "historical_data"

    # Invalid body is rejected by the pre-existing route schema without loading the legacy model.
    old_route = client.post("/api/v1/early-warning/predict", json={})
    assert old_route.status_code == 422
    assert "/api/v1/early-warning/predict" in app.openapi()["paths"]
