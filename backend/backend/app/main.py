
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.history_service import get_district_history
from services.weather_service import get_district_weather

app = FastAPI(
    title="ArogyaRadar AI",
    description="Rural health early-warning and resource-readiness API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
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
    for district in DISTRICTS:
        if district["id"] == district_id:
            return district

    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="District not found")
@app.get("/api/v1/districts/{district_id}/history")
def district_history(district_id: str):
    return get_district_history(district_id)
@app.get("/api/v1/districts/{district_id}/weather")
def district_weather(district_id: str):
    return get_district_weather(district_id)

