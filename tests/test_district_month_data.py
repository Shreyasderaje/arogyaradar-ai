import unittest

import pandas as pd

from scripts.district_aliases import CANONICAL_DISTRICT_NAMES, canonical_district_id
from scripts.merge_dengue_weather import merge_dengue_with_weather
from scripts.prepare_district_month_data import (
    TARGET_COLUMN,
    prepare_district_month_data,
)


def daily_rows(district, start, end, case_value, temperature, rainfall=1.0):
    dates = pd.date_range(start, end, freq="D")
    return pd.DataFrame({
        "metadata.recordDate": dates,
        "district_census2011": district,
        "daily_positive_total": case_value,
        "temperature_c": temperature,
        "relative_humidity_pct": 70.0,
        "rainfall_mm": rainfall,
    })


class DistrictMonthPreparationTests(unittest.TestCase):
    def test_legacy_aliases_are_canonical_and_vijayanagara_is_distinct(self):
        self.assertEqual(canonical_district_id("Ramanagara"), "bengaluru-south")
        self.assertEqual(canonical_district_id("Bangalore"), "bengaluru-urban")
        self.assertEqual(canonical_district_id("Vijayanagar"), "vijayanagara")
        self.assertNotEqual(canonical_district_id("Vijayanagara"), canonical_district_id("Ballari"))
        self.assertIsNone(canonical_district_id("Unknown District"))

    def test_canonical_map_covers_the_31_current_district_names(self):
        self.assertEqual(len(CANONICAL_DISTRICT_NAMES), 31)
        for district_id, name in CANONICAL_DISTRICT_NAMES.items():
            with self.subTest(district=name):
                self.assertEqual(canonical_district_id(name), district_id)

    def test_merge_uses_exact_dates_and_retains_unmatched_vijayanagara(self):
        dengue = pd.DataFrame({
            "metadata.recordDate": ["2024-01-01", "2024-01-01", "2024-01-01"],
            "district_census2011": ["Ramanagara", "VIJAYANAGAR", "Ballari"],
            "daily_positive_total": [1, 2, 3],
        })
        weather = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02"],
            "district_name": ["Bengaluru South", "Ballari"],
            "temperature_c": [20.0, 21.0],
            "relative_humidity_pct": [70.0, 71.0],
            "rainfall_mm": [0.0, 1.0],
        })

        merged = merge_dengue_with_weather(dengue, weather)
        south = merged.loc[merged["district_id"] == "bengaluru-south"].iloc[0]
        vijayanagara = merged.loc[merged["district_id"] == "vijayanagara"].iloc[0]
        ballari = merged.loc[merged["district_id"] == "ballari"].iloc[0]

        self.assertEqual(south["weather_match_status"], "matched")
        self.assertEqual(south["temperature_c"], 20.0)
        self.assertEqual(vijayanagara["weather_match_status"], "no_exact_weather_match")
        self.assertTrue(pd.isna(vijayanagara["temperature_c"]))
        self.assertEqual(ballari["weather_match_status"], "no_exact_weather_match")

    def test_labels_only_adjacent_complete_months_and_features_stop_at_cutoff(self):
        daily = pd.concat([
            daily_rows("Mysore", "2024-01-01", "2024-01-31", 1, 10.0),
            daily_rows("Mysuru", "2024-02-01", "2024-02-29", 2, 30.0),
        ], ignore_index=True)

        monthly, targets, exclusions, record_exclusions, summary = prepare_district_month_data(daily)

        self.assertEqual(len(monthly), 2)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets.iloc[0]["month"], "2024-01")
        self.assertEqual(targets.iloc[0]["target_month"], "2024-02")
        self.assertEqual(targets.iloc[0]["reported_dengue_total"], 31.0)
        self.assertEqual(targets.iloc[0]["mean_temperature_c"], 10.0)
        self.assertEqual(targets.iloc[0][TARGET_COLUMN], 1)
        self.assertNotIn("next_month_reported_total", targets.columns)
        self.assertTrue(exclusions.empty)
        self.assertTrue(record_exclusions.empty)
        self.assertEqual(summary["target_class_counts"], {0: 0, 1: 1})

    def test_missing_reporting_day_does_not_become_zero_or_month_total(self):
        january = daily_rows("Mysore", "2024-01-01", "2024-01-31", 1, 10.0)
        january = january.loc[january["metadata.recordDate"] != pd.Timestamp("2024-01-15")]
        february = daily_rows("Mysore", "2024-02-01", "2024-02-29", 2, 20.0)
        daily = pd.concat([january, february], ignore_index=True)

        monthly, targets, exclusions, _, _ = prepare_district_month_data(daily)

        self.assertEqual(monthly["month"].tolist(), ["2024-02"])
        self.assertTrue(targets.empty)
        self.assertIn("missing_calendar_reporting_days", exclusions.iloc[0]["exclusion_reason"])
        self.assertNotIn("reported_dengue_total", exclusions.columns)

    def test_unmatched_vijayanagara_weather_is_not_imputed(self):
        vijayanagara = daily_rows("VIJAYANAGAR", "2024-01-01", "2024-01-31", 1, 25.0)
        vijayanagara["temperature_c"] = pd.NA

        monthly, targets, exclusions, record_exclusions, summary = prepare_district_month_data(vijayanagara)

        self.assertTrue(monthly.empty)
        self.assertTrue(targets.empty)
        self.assertEqual(exclusions.iloc[0]["district_id"], "vijayanagara")
        self.assertIn("no_matched_weather_series", exclusions.iloc[0]["exclusion_reason"])
        self.assertEqual(len(record_exclusions), 31)
        self.assertEqual(summary["target_class_counts"], {0: 0, 1: 0})

    def test_duplicate_canonical_district_date_is_rejected(self):
        daily = pd.concat([
            daily_rows("Mysore", "2024-01-01", "2024-01-01", 1, 10.0),
            daily_rows("Mysuru", "2024-01-01", "2024-01-01", 2, 11.0),
        ], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "duplicate canonical district-date"):
            prepare_district_month_data(daily)


if __name__ == "__main__":
    unittest.main()
