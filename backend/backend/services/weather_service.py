
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Approximate district-centre coordinates for demo purposes.
DISTRICT_COORDS = {
    "mysuru": (12.2958, 76.6394),
    "belagavi": (15.8497, 74.4977),
    "bengaluru-urban": (12.9716, 77.5946),
    "bengaluru-rural": (13.2847, 77.6070),
    "chamarajanagara": (11.9261, 76.9437),
    "chikkamagaluru": (13.3161, 75.7720),
    "davangere": (14.4644, 75.9218),
    "kalaburagi": (17.3297, 76.8343),
    "shivamogga": (13.9299, 75.5681),
    "tumakuru": (13.3379, 77.1173),
    "vijayanagara": (15.1414, 76.9214),
    "vijayapura": (16.8302, 75.7100),
}


def get_district_weather(district_id: str):
    district_id = district_id.lower()

    if district_id not in DISTRICT_COORDS:
        return {
            "district_id": district_id,
            "data_status": "unavailable",
            "message": "Weather coordinates are not configured",
            "data_as_of": None,
        }

    cache_file = CACHE_DIR / f"weather_{district_id}.json"
    latitude, longitude = DISTRICT_COORDS[district_id]

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation",
        "forecast_days": 3,
        "timezone": "Asia/Kolkata",
    }

    try:
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params,
            timeout=8.0,
        )
        response.raise_for_status()
        payload = response.json()

        result = {
            "district_id": district_id,
            "source": "Open-Meteo",
            "data_status": "live",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "current": payload.get("current"),
            "forecast": payload.get("hourly"),
            "forecast_timezone": payload.get("timezone"),
            "data_as_of": payload.get("current", {}).get("time"),
        }

        cache_file.write_text(
            json.dumps(result, ensure_ascii=False),
            encoding="utf-8",
        )
        return result

    except (httpx.HTTPError, ValueError, OSError):
        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                cached["data_status"] = "cached"
                cached["cache_notice"] = (
                    "Live weather unavailable; showing saved weather data."
                )
                return cached
            except (json.JSONDecodeError, OSError):
                pass

        return {
            "district_id": district_id,
            "source": "Open-Meteo",
            "data_status": "unavailable",
            "current": None,
            "forecast": None,
            "message": "No live or cached weather data is available",
            "data_as_of": None,
        }
