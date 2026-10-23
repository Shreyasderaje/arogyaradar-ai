
from pathlib import Path

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = PROJECT_ROOT / "models" / "early_warning_model.joblib"

FEATURES = [
    "temperature_c",
    "relative_humidity_pct",
    "rainfall_mm",
    "cases_last_7d",
    "cases_last_14d",
]

_model_bundle = None


def _load_model():
    global _model_bundle

    if _model_bundle is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Trained model not found: {MODEL_PATH}"
            )

        _model_bundle = joblib.load(MODEL_PATH)

    return _model_bundle


def predict_early_warning(
    temperature_c: float,
    relative_humidity_pct: float,
    rainfall_mm: float,
    cases_last_7d: float,
    cases_last_14d: float,
) -> dict:
    bundle = _load_model()
    model = bundle["model"]

    values = {
        "temperature_c": temperature_c,
        "relative_humidity_pct": relative_humidity_pct,
        "rainfall_mm": rainfall_mm,
        "cases_last_7d": cases_last_7d,
        "cases_last_14d": cases_last_14d,
    }

    if not all(pd.notna(value) for value in values.values()):
        raise ValueError("All five model inputs must be valid numbers.")

    if not 0 <= relative_humidity_pct <= 100:
        raise ValueError("Relative humidity must be between 0 and 100.")

    if rainfall_mm < 0 or cases_last_7d < 0 or cases_last_14d < 0:
        raise ValueError("Rainfall and case counts cannot be negative.")

    features = pd.DataFrame(
        [[values[name] for name in FEATURES]],
        columns=FEATURES,
    )

    probability = float(model.predict_proba(features)[0][1])
    prediction = int(model.predict(features)[0])

    return {
        "prediction": prediction,
        "prediction_label": (
            "reported_case_increase" if prediction == 1
            else "no_reported_case_increase"
        ),
        "probability_of_increase": round(probability, 4),
        "data_status": "experimental_model",
        "message": (
            "Experimental estimate of reported-case increases, "
            "not a confirmed outbreak prediction."
        ),
    }
