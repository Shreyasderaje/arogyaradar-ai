
from typing import Optional

WEIGHTS = {
    "weather": 0.35,
    "health": 0.25,
    "vulnerability": 0.20,
    "readiness": 0.20,
}


def calculate_preparedness_score(
    components: dict[str, Optional[float]],
) -> dict:
    """Calculate a weighted score from available 0-100 inputs."""

    available = {}
    missing = []

    for name, weight in WEIGHTS.items():
        value = components.get(name)

        if value is None:
            missing.append(name)
            continue

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0 <= value <= 100
        ):
            raise ValueError(
                f"{name} must be a number between 0 and 100"
            )

        available[name] = (float(value), weight)

    if not available:
        return {
            "score": None,
            "data_status": "unavailable",
            "available_components": [],
            "missing_components": missing,
            "coverage_percent": 0,
        }

    total_weight = sum(weight for _, weight in available.values())

    score = sum(
        value * weight for value, weight in available.values()
    ) / total_weight

    coverage = round(total_weight * 100, 1)

    return {
        "score": round(score, 2),
        "data_status": (
            "complete" if not missing
            else "partial" if coverage >= 50
            else "limited"
        ),
        "available_components": list(available.keys()),
        "missing_components": missing,
        "coverage_percent": coverage,
        "message": (
            "Prioritization aid only; not a confirmed outbreak prediction."
        ),
    }
