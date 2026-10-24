
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from zoneinfo import ZoneInfo

from services.history_service import get_district_history
from services.weather_service import get_district_weather
from services.scoring_service import calculate_preparedness_score
from services.early_warning_service import predict_early_warning
from services.district_month_assessment_service import assess_district_month_request
from services.district_month_model_contract import DistrictMonthPredictionResponse
from app.schemas import DistrictMonthAssessmentInput


app = FastAPI(
    title="ArogyaRadar AI",
    description="Rural health early-warning and resource-readiness API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5178",
        "http://localhost:5179",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5178",
        "http://127.0.0.1:5179",
        "https://arogyaradar-ai.vercel.app",
        "https://arogyaradar-ai-git-main-shreyasderaje.vercel.app",
        "https://arogyaradar-ai-khx9g5d4m-shreyasderaje.vercel.app",
        "https://arogyaradar-ai-bc28d63si-shreyasderaje.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


DISTRICTS = [
    {"id": "belagavi", "name": "Belagavi"},
    {"id": "bengaluru-rural", "name": "Bengaluru Rural"},
    {"id": "bengaluru-urban", "name": "Bengaluru Urban"},
    {"id": "chamarajanagara", "name": "Chamarajanagara"},
    {"id": "chikkamagaluru", "name": "Chikkamagaluru"},
    {"id": "davangere", "name": "Davangere"},
    {"id": "kalaburagi", "name": "Kalaburagi"},
    {"id": "mysuru", "name": "Mysuru"},
    {"id": "shivamogga", "name": "Shivamogga"},
    {"id": "tumakuru", "name": "Tumakuru"},
    {"id": "vijayanagara", "name": "Vijayanagara"},
    {"id": "vijayapura", "name": "Vijayapura"},
]


@app.get("/")
def root():
    return {"message": "ArogyaRadar AI API is running"}


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "message": "ArogyaRadar AI backend is running",
    }


@app.get("/api/v1/districts")
def get_districts():
    return {
        "count": len(DISTRICTS),
        "districts": DISTRICTS,
        "data_as_of": None,
    }


@app.get("/api/v1/districts/{district_id}")
def get_district(district_id: str):
    district_id = district_id.strip().lower()

    for district in DISTRICTS:
        if district["id"] == district_id:
            return district

    raise HTTPException(
        status_code=404,
        detail="District not found",
    )


@app.get("/api/v1/districts/{district_id}/history")
def district_history(district_id: str):
    return get_district_history(district_id)


@app.get("/api/v1/districts/{district_id}/weather")
def district_weather(district_id: str):
    return get_district_weather(district_id)


@app.get("/api/v1/scores")
def get_preparedness_score(
    weather: Optional[float] = Query(default=None, ge=0, le=100),
    health: Optional[float] = Query(default=None, ge=0, le=100),
    vulnerability: Optional[float] = Query(default=None, ge=0, le=100),
    readiness: Optional[float] = Query(default=None, ge=0, le=100),
):
    components = {
        "weather": weather,
        "health": health,
        "vulnerability": vulnerability,
        "readiness": readiness,
    }

    try:
        return calculate_preparedness_score(components)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/v1/districts/{district_id}/score")
def get_district_score(district_id: str):
    district_id = district_id.strip().lower()

    district = next(
        (item for item in DISTRICTS if item["id"] == district_id),
        None,
    )

    if district is None:
        raise HTTPException(
            status_code=404,
            detail="District not found",
        )

    return {
        "district_id": district["id"],
        "district_name": district["name"],
        "score": None,
        "data_status": "unavailable",
        "available_components": [],
        "missing_components": [
            "weather",
            "health",
            "vulnerability",
            "readiness",
        ],
        "coverage_percent": 0,
        "message": (
            "District-specific scoring inputs are not yet validated. "
            "No risk score has been calculated."
        ),
    }


class EarlyWarningInput(BaseModel):
    temperature_c: float = Field(ge=-10, le=60)
    relative_humidity_pct: float = Field(ge=0, le=100)
    rainfall_mm: float = Field(ge=0)
    cases_last_7d: float = Field(ge=0)
    cases_last_14d: float = Field(ge=0)


@app.post(
    "/api/v1/district-month/assess",
    response_model=DistrictMonthPredictionResponse,
    summary="Assess next-month reported dengue case increase support",
    description=(
        "Returns a support/data status for the candidate district-month model. "
        "This is not a confirmed outbreak prediction; no candidate artifact is currently approved."
    ),
)
def district_month_assessment(payload: DistrictMonthAssessmentInput):
    try:
        result = assess_district_month_request(
            payload.model_dump(),
            known_district_ids={district["id"] for district in DISTRICTS},
            today=datetime.now(ZoneInfo("Asia/Kolkata")).date(),
        )
        return result.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/v1/early-warning/predict")
def early_warning_prediction(payload: EarlyWarningInput):
    try:
        return predict_early_warning(**payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
