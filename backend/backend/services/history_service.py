
from datetime import datetime, timezone

# Demo records only. Replace with verified historical health data
# before using the results for real-world decisions.
HISTORY = {
    "mysuru": [
        {
            "month": "2026-01",
            "cases": 42,
            "source": "synthetic_demo",
        },
        {
            "month": "2026-02",
            "cases": 51,
            "source": "synthetic_demo",
        },
        {
            "month": "2026-03",
            "cases": 47,
            "source": "synthetic_demo",
        },
    ]
}


def get_district_history(district_id: str):
    records = HISTORY.get(district_id.lower())

    if records is None:
        return {
            "district_id": district_id,
            "records": [],
            "data_status": "unavailable",
            "message": "No historical data loaded for this district",
            "data_as_of": None,
        }

    return {
        "district_id": district_id,
        "records": records,
        "data_status": "demo_only",
        "data_as_of": datetime.now(timezone.utc).isoformat(),
    }
