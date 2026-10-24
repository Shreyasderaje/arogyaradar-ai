import unittest
from datetime import date

from scripts.evaluate_district_month_model import FEATURE_COLUMNS
from backend.backend.services.district_month_model_contract import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    MODEL_TRANSFORMATIONS,
    MODEL_VERSION,
    DistrictMonthPredictionRequest,
    DistrictMonthPredictionResponse,
    assess_prediction_request,
    build_feature_values,
)


def complete_record(district_id="mysuru", month="2026-10"):
    return {
        "district_id": district_id,
        "district_name": "Mysuru",
        "month": month,
        "prediction_cutoff": "2026-10-31",
        "calendar_days": 31,
        "reporting_days": 31,
        "valid_disease_days": 31,
        "valid_weather_days": 31,
        "month_complete": True,
        "reported_dengue_total": 17,
        "mean_temperature_c": 25.5,
        "mean_relative_humidity_pct": 70.0,
        "total_rainfall_mm": 48.2,
    }


class DistrictMonthInferenceContractTests(unittest.TestCase):
    def setUp(self):
        self.request = DistrictMonthPredictionRequest.from_mapping({
            "district_id": "mysuru",
            "current_month": "2026-10",
        })

    def assess(self, **overrides):
        args = {
            "known_district_ids": {"mysuru"},
            "today": date(2026, 10, 31),
            "latest_complete_month": "2026-10",
            "health_data_as_of": "2026-10-31",
            "district_month_record": complete_record(),
        }
        args.update(overrides)
        return assess_prediction_request(self.request, **args)

    def test_request_rejects_missing_fields_and_invalid_months(self):
        with self.assertRaisesRegex(ValueError, "Missing request fields"):
            DistrictMonthPredictionRequest.from_mapping({"district_id": "mysuru"})
        for invalid_month in ("2026-13", "2026-00", "2026/10", "2026-1"):
            with self.subTest(month=invalid_month), self.assertRaises(ValueError):
                DistrictMonthPredictionRequest.from_mapping({
                    "district_id": "mysuru",
                    "current_month": invalid_month,
                })

    def test_missing_features_are_rejected_and_never_imputed_at_inference(self):
        record = complete_record()
        del record["mean_temperature_c"]
        with self.assertRaisesRegex(ValueError, "Missing model features"):
            build_feature_values(record)

    def test_unknown_district_returns_explicit_status(self):
        unknown_request = DistrictMonthPredictionRequest.from_mapping({
            "district_id": "unknown-district",
            "current_month": "2026-10",
        })
        response = assess_prediction_request(
            unknown_request,
            known_district_ids={"mysuru", "udupi"},
            today=date(2026, 10, 31),
            latest_complete_month="2026-10",
            health_data_as_of="2026-10-31",
            district_month_record=complete_record("unknown-district"),
        )
        self.assertEqual(response.status, "unknown_district")
        self.assertFalse(response.prediction_supported)
        self.assertIsNone(response.prediction)

    def test_missing_or_historical_health_data_is_not_current_prediction(self):
        no_history = self.assess(latest_complete_month=None, health_data_as_of=None, district_month_record=None)
        self.assertEqual(no_history.status, "unavailable")
        stale = self.assess(latest_complete_month="2024-01", health_data_as_of="2024-01-31")
        self.assertEqual(stale.status, "not_current")
        self.assertEqual(stale.health_data_as_of, "2024-01-31")
        self.assertIsNone(stale.probability_of_reported_case_increase)

    def test_partial_or_wrong_month_record_is_unavailable(self):
        record = complete_record()
        record["valid_disease_days"] = 30
        partial = self.assess(district_month_record=record)
        self.assertEqual(partial.status, "unavailable")
        wrong_month = self.assess(district_month_record=complete_record(month="2026-09"))
        self.assertEqual(wrong_month.status, "unavailable")

    def test_current_month_must_be_complete_at_request_date(self):
        response = self.assess(today=date(2026, 10, 24))
        self.assertEqual(response.status, "unavailable")
        self.assertIn("complete calendar month", response.message)

    def test_previous_complete_month_can_only_support_the_current_target_month(self):
        request = DistrictMonthPredictionRequest.from_mapping({
            "district_id": "mysuru",
            "current_month": "2026-09",
        })
        record = complete_record(month="2026-09")
        record.update({
            "prediction_cutoff": "2026-09-30",
            "calendar_days": 30,
            "reporting_days": 30,
            "valid_disease_days": 30,
            "valid_weather_days": 30,
        })
        response = assess_prediction_request(
            request,
            known_district_ids={"mysuru"},
            today=date(2026, 10, 24),
            latest_complete_month="2026-09",
            health_data_as_of="2026-09-30",
            district_month_record=record,
        )
        self.assertEqual(response.status, "model_unavailable")
        self.assertEqual(response.target_month, "2026-10")

    def test_inference_schema_matches_evaluated_feature_columns(self):
        self.assertEqual(FEATURE_NAMES, FEATURE_COLUMNS)
        values = build_feature_values({**complete_record(), "target_reported_case_increase_next_month": 1})
        self.assertEqual(tuple(values), FEATURE_COLUMNS)
        self.assertNotIn("target_reported_case_increase_next_month", values)
        self.assertEqual(FEATURE_SCHEMA_VERSION, "district-month-features-v1")
        self.assertEqual(MODEL_VERSION, "district-month-logistic-regression-eval-v1")
        self.assertEqual(len(MODEL_TRANSFORMATIONS), 3)

    def test_candidate_defaults_to_model_unavailable_and_response_schema_is_consistent(self):
        response = self.assess()
        self.assertEqual(response.status, "model_unavailable")
        self.assertFalse(response.prediction_supported)
        self.assertIsNone(response.prediction)
        self.assertEqual(response.target_month, "2026-11")
        self.assertEqual(response.prediction_cutoff, "2026-10-31")
        with self.assertRaisesRegex(ValueError, "supported response requires"):
            DistrictMonthPredictionResponse(
                district_id="mysuru",
                current_month="2026-10",
                target_month="2026-11",
                prediction_cutoff="2026-10-31",
                status="supported",
                prediction_supported=True,
                prediction=None,
                probability_of_reported_case_increase=None,
                model_version=MODEL_VERSION,
                feature_schema_version=FEATURE_SCHEMA_VERSION,
                target_definition="reported increase",
                health_data_as_of="2026-10-31",
                message="",
            )


if __name__ == "__main__":
    unittest.main()
