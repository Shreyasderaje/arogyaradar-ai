"""Chronologically evaluate district-month reported dengue increase models.

This evaluates a reported-case change classification task, not outbreak
prediction. It deliberately does not overwrite or promote the legacy model.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parent.parent
TARGET_FILE = ROOT / "data" / "processed" / "dengue_district_month_targets.csv"
MONTHLY_FILE = ROOT / "data" / "processed" / "dengue_district_month.csv"

TARGET_COLUMN = "target_reported_case_increase_next_month"
FEATURE_COLUMNS = (
    "reported_dengue_total",
    "mean_temperature_c",
    "mean_relative_humidity_pct",
    "total_rainfall_mm",
)
IDENTIFIER_COLUMNS = ("district_id", "district_name", "month", "target_month", "prediction_cutoff")
HOLDOUT_TARGET_MONTH_COUNT = 4


def validate_target_frame(frame):
    """Fail closed on schema/date/label inconsistencies that could leak target data."""
    required = set(IDENTIFIER_COLUMNS) | set(FEATURE_COLUMNS) | {TARGET_COLUMN}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Target input missing required columns: {missing}")
    if frame.empty:
        raise ValueError("Target input is empty")

    current_month = pd.PeriodIndex(frame["month"].astype(str), freq="M")
    target_month = pd.PeriodIndex(frame["target_month"].astype(str), freq="M")
    if not np.all((current_month + 1) == target_month):
        raise ValueError("Each target_month must immediately follow its current month")
    expected_cutoff = current_month.to_timestamp(how="end").normalize().date.astype(str)
    supplied_cutoff = pd.to_datetime(frame["prediction_cutoff"], errors="coerce").dt.date.astype(str)
    if not np.all(expected_cutoff == supplied_cutoff):
        raise ValueError("prediction_cutoff must be the last calendar day of the current month")

    labels = pd.to_numeric(frame[TARGET_COLUMN], errors="coerce")
    if labels.isna().any() or not set(labels.unique()).issubset({0, 1}):
        raise ValueError("Target labels must be present and binary (0 or 1)")
    if frame.duplicated(["district_id", "month"]).any():
        raise ValueError("Duplicate district-month target rows found")
    return frame.copy()


def chronological_holdout(frame, target_month_count=HOLDOUT_TARGET_MONTH_COUNT):
    """Reserve complete latest target months; train labels end strictly earlier."""
    months = sorted(pd.PeriodIndex(frame["target_month"].astype(str), freq="M").unique())
    if len(months) <= target_month_count:
        raise ValueError(
            f"Need more than {target_month_count} distinct target months; found {len(months)}"
        )
    test_months = months[-target_month_count:]
    first_test_month = test_months[0]
    row_target_month = pd.PeriodIndex(frame["target_month"].astype(str), freq="M")
    train = frame.loc[row_target_month < first_test_month].copy()
    test = frame.loc[row_target_month.isin(test_months)].copy()
    if train.empty or test.empty:
        raise ValueError("Chronological split produced an empty partition")
    if pd.PeriodIndex(train["target_month"].astype(str), freq="M").max() >= first_test_month:
        raise AssertionError("Training labels overlap the evaluation period")
    return train, test, test_months


def build_feature_matrix(frame):
    """Select only cutoff-available numeric features from the target CSV."""
    absent = [column for column in FEATURE_COLUMNS if column not in frame]
    if absent:
        raise ValueError(f"Missing model features: {absent}")
    features = frame.loc[:, FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    features = features.replace([np.inf, -np.inf], np.nan)
    return features


def previous_month_trend_baseline(test, monthly):
    """Predict increase if current complete-month total exceeds prior complete month.

    Rows without an immediately preceding complete month are omitted from this
    baseline only; no missing report is interpreted as zero.
    """
    required = {"district_id", "month", "reported_dengue_total"}
    if not required.issubset(monthly.columns):
        raise ValueError(f"Monthly input missing columns: {sorted(required - set(monthly.columns))}")
    prior = monthly[["district_id", "month", "reported_dengue_total"]].copy()
    prior["month"] = pd.PeriodIndex(prior["month"].astype(str), freq="M") + 1
    prior = prior.rename(columns={"month": "month", "reported_dengue_total": "previous_month_total"})

    comparison = test.copy()
    comparison["month"] = pd.PeriodIndex(comparison["month"].astype(str), freq="M")
    comparison = comparison.merge(prior, on=["district_id", "month"], how="left", validate="one_to_one")
    comparison["current_total"] = pd.to_numeric(comparison["reported_dengue_total"], errors="coerce")
    comparison = comparison.dropna(subset=["previous_month_total", "current_total"])
    if comparison.empty:
        return comparison, np.array([], dtype=int)
    predictions = (comparison["current_total"].to_numpy() > comparison["previous_month_total"].to_numpy()).astype(int)
    return comparison, predictions


def classification_metrics(y_true, predicted, probabilities=None):
    y_true = np.asarray(y_true, dtype=int)
    predicted = np.asarray(predicted, dtype=int)
    matrix = confusion_matrix(y_true, predicted, labels=[0, 1])
    result = {
        "samples": int(len(y_true)),
        "class_counts": {int(k): int(v) for k, v in pd.Series(y_true).value_counts().sort_index().items()},
        "confusion_matrix_labels_0_1": matrix.tolist(),
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predicted)),
        "accuracy": float(accuracy_score(y_true, predicted)),
        "roc_auc": None,
        "pr_auc_average_precision": None,
    }
    if probabilities is not None and len(np.unique(y_true)) == 2:
        result["roc_auc"] = float(roc_auc_score(y_true, probabilities))
        result["pr_auc_average_precision"] = float(average_precision_score(y_true, probabilities))
    return result


def make_models():
    return {
        "regularized_logistic_regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("classifier", LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=42)),
        ]),
        "random_forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("classifier", RandomForestClassifier(
                n_estimators=300,
                min_samples_leaf=5,
                max_features="sqrt",
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )),
        ]),
    }


def evaluate(targets, monthly):
    targets = validate_target_frame(targets)
    train, test, test_months = chronological_holdout(targets)
    x_train, x_test = build_feature_matrix(train), build_feature_matrix(test)
    y_train = train[TARGET_COLUMN].astype(int)
    y_test = test[TARGET_COLUMN].astype(int)
    if y_train.nunique() < 2:
        raise ValueError("Training period has only one target class")

    metrics = {}
    majority = DummyClassifier(strategy="most_frequent")
    majority.fit(np.zeros((len(y_train), 1)), y_train)
    majority_pred = majority.predict(np.zeros((len(y_test), 1)))
    metrics["majority_class_baseline"] = classification_metrics(
        y_test, majority_pred, np.zeros(len(y_test), dtype=float)
    )

    trend_rows, trend_pred = previous_month_trend_baseline(test, monthly)
    if len(trend_rows):
        metrics["previous_month_trend_baseline"] = classification_metrics(
            trend_rows[TARGET_COLUMN].astype(int), trend_pred, trend_pred.astype(float)
        )
    else:
        metrics["previous_month_trend_baseline"] = {"status": "unavailable", "reason": "No held-out rows have a complete immediately preceding month"}

    for name, model in make_models().items():
        # Pipeline imputation/scaling are fit exclusively on the training partition.
        model.fit(x_train, y_train)
        predicted = model.predict(x_test)
        probabilities = model.predict_proba(x_test)[:, 1]
        metrics[name] = classification_metrics(y_test, predicted, probabilities)

    report = {
        "total_rows": int(len(targets)),
        "total_class_counts": {int(k): int(v) for k, v in targets[TARGET_COLUMN].value_counts().sort_index().items()},
        "feature_columns": list(FEATURE_COLUMNS),
        "feature_missing_counts": {column: int(build_feature_matrix(targets)[column].isna().sum()) for column in FEATURE_COLUMNS},
        "train_rows": int(len(train)),
        "train_class_counts": {int(k): int(v) for k, v in y_train.value_counts().sort_index().items()},
        "train_target_months": sorted(train["target_month"].unique()),
        "test_rows": int(len(test)),
        "test_class_counts": {int(k): int(v) for k, v in y_test.value_counts().sort_index().items()},
        "test_target_months": [str(month) for month in test_months],
        "test_district_count": int(test["district_id"].nunique()),
        "metrics": metrics,
        "promotion": {
            "artifact_saved": False,
            "reason": "Single small chronological holdout with only four target months; evidence is insufficient to promote a model.",
        },
    }
    return report


def _format_metrics(name, values):
    print(f"\n{name}: n={values.get('samples', '—')}")
    if "status" in values:
        print("  Status:", values["status"], "—", values["reason"])
        return
    print("  Class counts:", values["class_counts"])
    print("  Confusion matrix [[TN, FP], [FN, TP]]:", values["confusion_matrix_labels_0_1"])
    for key in ("precision", "recall", "f1", "balanced_accuracy", "accuracy", "roc_auc", "pr_auc_average_precision"):
        value = values[key]
        print(f"  {key}:", "undefined" if value is None else f"{value:.4f}")


def main():
    if not TARGET_FILE.exists() or not MONTHLY_FILE.exists():
        raise FileNotFoundError("Run scripts/prepare_district_month_data.py first to generate both input CSVs")
    targets = pd.read_csv(TARGET_FILE)
    monthly = pd.read_csv(MONTHLY_FILE)
    report = evaluate(targets, monthly)

    print("=== District-month dengue reported-case increase evaluation ===")
    print("Task: next complete calendar month's reported total > current complete month's total; not outbreak prediction")
    print("Target dataset:", TARGET_FILE.relative_to(ROOT))
    print("Prediction cutoff: end of current month; target-month values are label-only and excluded from features")
    print("Total samples:", report["total_rows"], "| class counts:", report["total_class_counts"])
    print("Features:", report["feature_columns"])
    print("Feature missing counts:", report["feature_missing_counts"])
    print("Train rows:", report["train_rows"], "| classes:", report["train_class_counts"])
    print("Train target months:", report["train_target_months"])
    print("Holdout rows:", report["test_rows"], "| classes:", report["test_class_counts"])
    print("Held-out target months:", report["test_target_months"])
    print("Held-out districts:", report["test_district_count"])
    print("Split: all districts in a target month stay in one partition; training labels precede the first held-out target month.")
    for name, values in report["metrics"].items():
        _format_metrics(name, values)
    print("\nArtifact:", "not saved; evidence gate not met.")
    print("Limitations: district rows within a target month are dependent; only four held-out months provide weak temporal evidence.")


if __name__ == "__main__":
    main()
