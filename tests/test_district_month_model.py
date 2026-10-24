import unittest

import pandas as pd

from scripts.evaluate_district_month_model import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_feature_matrix,
    chronological_holdout,
    make_models,
    previous_month_trend_baseline,
    validate_target_frame,
)


def sample_targets():
    rows = []
    for district in ("alpha", "beta"):
        for current_month, target_month, label in (
            ("2021-01", "2021-02", 0),
            ("2021-02", "2021-03", 1),
            ("2021-03", "2021-04", 0),
            ("2021-04", "2021-05", 1),
            ("2021-05", "2021-06", 0),
        ):
            rows.append({
                "district_id": district,
                "district_name": district.title(),
                "month": current_month,
                "target_month": target_month,
                "prediction_cutoff": str((pd.Period(current_month, freq="M").end_time).date()),
                "reported_dengue_total": float(len(rows) + 1),
                "mean_temperature_c": 25.0,
                "mean_relative_humidity_pct": 70.0,
                "total_rainfall_mm": 12.0,
                TARGET_COLUMN: label,
            })
    return pd.DataFrame(rows)


class DistrictMonthModelTests(unittest.TestCase):
    def test_model_features_exclude_identifiers_and_target_month_fields(self):
        frame = sample_targets()
        x = build_feature_matrix(frame)
        self.assertEqual(tuple(x.columns), FEATURE_COLUMNS)
        self.assertNotIn(TARGET_COLUMN, x)
        self.assertNotIn("target_month", x)
        self.assertNotIn("district_id", x)
        self.assertNotIn("prediction_cutoff", x)

    def test_chronological_split_groups_target_months_and_has_no_label_overlap(self):
        frame = sample_targets()
        train, test, months = chronological_holdout(frame, target_month_count=2)
        first_test = pd.Period(min(test["target_month"]), freq="M")
        self.assertEqual(len(months), 2)
        self.assertTrue((pd.PeriodIndex(train["target_month"], freq="M") < first_test).all())
        self.assertTrue(set(train["target_month"]).isdisjoint(test["target_month"]))
        self.assertEqual(set(test["target_month"]), {str(month) for month in months})

    def test_cutoff_and_adjacent_target_are_validated(self):
        frame = sample_targets()
        validate_target_frame(frame)
        invalid = frame.copy()
        invalid.loc[0, "prediction_cutoff"] = "2021-02-01"
        with self.assertRaisesRegex(ValueError, "prediction_cutoff"):
            validate_target_frame(invalid)
        invalid = frame.copy()
        invalid.loc[0, "target_month"] = "2021-03"
        with self.assertRaisesRegex(ValueError, "immediately follow"):
            validate_target_frame(invalid)

    def test_pipeline_inference_schema_matches_training_features(self):
        frame = sample_targets()
        x = build_feature_matrix(frame)
        y = frame[TARGET_COLUMN]
        model = make_models()["regularized_logistic_regression"]
        model.fit(x, y)
        self.assertEqual(tuple(model.feature_names_in_), FEATURE_COLUMNS)
        self.assertEqual(model.predict_proba(build_feature_matrix(frame.iloc[:1])).shape, (1, 2))

    def test_previous_month_baseline_omits_rows_without_complete_previous_month(self):
        targets = sample_targets().iloc[[3, 8]].copy()
        targets["month"] = ["2021-04", "2021-04"]
        targets["target_month"] = ["2021-05", "2021-05"]
        monthly = pd.DataFrame({
            "district_id": ["alpha"],
            "month": ["2021-03"],
            "reported_dengue_total": [10.0],
        })
        eligible, predictions = previous_month_trend_baseline(targets, monthly)
        self.assertEqual(len(eligible), 1)
        self.assertEqual(predictions.tolist(), [0])


if __name__ == "__main__":
    unittest.main()
