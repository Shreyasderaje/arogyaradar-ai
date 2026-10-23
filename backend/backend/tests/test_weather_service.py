import json
from unittest.mock import Mock

import httpx

from services import weather_service


def test_live_weather_is_saved_to_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(weather_service, "CACHE_DIR", tmp_path)

    payload = {
        "timezone": "Asia/Kolkata",
        "current": {
            "time": "2026-10-24T10:00",
            "temperature_2m": 27.0,
            "relative_humidity_2m": 70,
            "precipitation": 0.0,
        },
        "hourly": {"time": ["2026-10-24T10:00"]},
    }

    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None

    monkeypatch.setattr(weather_service.httpx, "get", lambda *a, **k: response)

    result = weather_service.get_district_weather("mysuru")

    assert result["data_status"] == "live"
    assert result["current"]["temperature_2m"] == 27.0
    assert (tmp_path / "weather_mysuru.json").exists()


def test_cache_is_used_when_live_request_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(weather_service, "CACHE_DIR", tmp_path)

    cached = {
        "district_id": "mysuru",
        "source": "Open-Meteo",
        "data_status": "live",
        "current": {"temperature_2m": 26.0},
        "forecast": {},
        "data_as_of": "2026-10-24T09:00",
    }

    (tmp_path / "weather_mysuru.json").write_text(
        json.dumps(cached), encoding="utf-8"
    )

    def fail_request(*args, **kwargs):
        raise httpx.ConnectError("Simulated connection failure")

    monkeypatch.setattr(weather_service.httpx, "get", fail_request)

    result = weather_service.get_district_weather("mysuru")

    assert result["data_status"] == "cached"
    assert result["current"]["temperature_2m"] == 26.0
    assert "cache_notice" in result


def test_unavailable_when_request_fails_and_no_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(weather_service, "CACHE_DIR", tmp_path)

    def fail_request(*args, **kwargs):
        raise httpx.ConnectError("Simulated connection failure")

    monkeypatch.setattr(weather_service.httpx, "get", fail_request)

    result = weather_service.get_district_weather("mysuru")

    assert result["data_status"] == "unavailable"
    assert result["current"] is None


def test_unknown_district_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(weather_service, "CACHE_DIR", tmp_path)

    result = weather_service.get_district_weather("unknown-district")

    assert result["data_status"] == "unavailable"
    assert "coordinates" in result["message"].lower()
