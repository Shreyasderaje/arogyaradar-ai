
from pathlib import Path

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer

ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = ROOT / "data" / "processed" / "dengue_weather_merged.csv"
MODEL_DIR = ROOT / "models"
MODEL_FILE = MODEL_DIR / "early_warning_model.joblib"
FEATURE_FILE = ROOT / "data" / "processed" / "early_warning_features.csv"

FEATURES = [
    "temperature_c",
    "relative_humidity_pct",
    "rainfall_mm",
    "cases_last_7d",
    "cases_last_14d",
]

def main():
    df = pd.read_csv(INPUT_FILE)
    df["metadata.recordDate"] = pd.to_datetime(
        df["metadata.recordDate"], errors="coerce"
    )
    df = df.dropna(
        subset=["metadata.recordDate", "district_census2011", "daily_positive_total"]
    ).copy()

    df = df.sort_values(
        ["district_census2011", "metadata.recordDate"]
    ).reset_index(drop=True)

    # Aggregate cases by district and date.
    # Use max because the source contains cumulative/daily reporting inconsistencies;
    # inspect the source carefully before interpreting this as true incidence.
    df["daily_positive_total"] = pd.to_numeric(
        df["daily_positive_total"], errors="coerce"
    )
    df = df.dropna(subset=["daily_positive_total"])
    df["daily_positive_total"] = df["daily_positive_total"].clip(lower=0)

    # Rolling features use only prior observations.
    grouped = df.groupby("district_census2011", group_keys=False)
    df["cases_last_7d"] = grouped["daily_positive_total"].transform(
        lambda s: s.shift(1).rolling(7, min_periods=7).sum()
    )
    df["cases_last_14d"] = grouped["daily_positive_total"].transform(
        lambda s: s.shift(1).rolling(14, min_periods=14).sum()
    )

    # Define target: next 7 calendar days have more reported cases
    # than the previous 7 calendar days.
    # First reindex each district to a daily calendar to avoid treating
    # missing reporting dates as zero.
    pieces = []
    for district, part in df.groupby("district_census2011"):
        part = part.sort_values("metadata.recordDate").set_index("metadata.recordDate")
        part = part[~part.index.duplicated(keep="last")]

        calendar = pd.date_range(part.index.min(), part.index.max(), freq="D")
        part = part.reindex(calendar)
        part.index.name = "date"
        part["district_census2011"] = district

        # Weather is retained only on dates with observed weather.
        # Missing dengue reporting dates remain missing, not zero.
        cases = part["daily_positive_total"]
        prior_7 = cases.shift(1).rolling(7, min_periods=7).sum()
        next_7 = cases.shift(-7).rolling(7, min_periods=7).sum()

        part["cases_last_7d"] = prior_7
        part["cases_last_14d"] = cases.shift(1).rolling(14, min_periods=14).sum()
        part["next_7d_cases"] = next_7
        part["target_increase"] = (
            (next_7 > prior_7) & prior_7.notna() & next_7.notna()
        ).astype("float")
        part.loc[prior_7.isna() | next_7.isna(), "target_increase"] = float("nan")

        pieces.append(part.reset_index())

    features = pd.concat(pieces, ignore_index=True)
    features = features.dropna(subset=FEATURES + ["target_increase"]).copy()
    features["target_increase"] = features["target_increase"].astype(int)

    # Save the model-ready data for review.
    FEATURE_FILE.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(FEATURE_FILE, index=False)

    # Time-based split: older dates for training, latest 20% for testing.
    dates = features["date"].sort_values().unique()
    split_date = dates[int(len(dates) * 0.8)]
    train = features[features["date"] < split_date].copy()
    test = features[features["date"] >= split_date].copy()

    if train.empty or test.empty or train["target_increase"].nunique() < 2:
        raise ValueError(
            "Insufficient training data or only one target class. "
            "Inspect reporting patterns before proceeding."
        )

    X_train, y_train = train[FEATURES], train["target_increase"]
    X_test, y_test = test[FEATURES], test["target_increase"]

    models = {
        "baseline": make_pipeline(
            SimpleImputer(strategy="median"),
            DummyClassifier(strategy="most_frequent"),
        ),
        "random_forest": make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestClassifier(
                n_estimators=200,
                max_depth=8,
                min_samples_leaf=10,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            ),
        ),
    }

    print("Feature dataset:", features.shape)
    print("Train rows:", len(train), "| Test rows:", len(test))
    print("Train period:", train["date"].min(), "to", train["date"].max())
    print("Test period:", test["date"].min(), "to", test["date"].max())
    print("\nTarget distribution:\n", features["target_increase"].value_counts().to_string())

    for name, model in models.items():
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)

        print(f"\n--- {name} ---")
        print("Accuracy:", round(accuracy_score(y_test, predictions), 4))
        print("Confusion matrix:\n", confusion_matrix(y_test, predictions))
        print(classification_report(y_test, predictions, zero_division=0))

        if hasattr(model[-1], "predict_proba") and y_test.nunique() == 2:
            probabilities = model.predict_proba(X_test)[:, 1]
            print("ROC-AUC:", round(roc_auc_score(y_test, probabilities), 4))

        if name == "random_forest":
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            joblib.dump(
                {"model": model, "features": FEATURES},
                MODEL_FILE,
            )

    print("\nFeature data saved to:", FEATURE_FILE)
    print("Model saved to:", MODEL_FILE)

if __name__ == "__main__":
    main()
