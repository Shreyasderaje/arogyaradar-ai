# District-month model inference contract (design only)

The FastAPI route `POST /api/v1/district-month/assess` uses this contract to
validate the request and report data/model support. It does not load or save a
model. The evaluated Logistic Regression is a candidate only; no current
request receives a model prediction while the approved artifact is absent.

## Task and candidate metadata

- Model version: `district-month-logistic-regression-eval-v1` (evaluation-only).
- Feature schema: `district-month-features-v1`.
- Target: `1` when a district's reported dengue total in the next **complete
  calendar month** is greater than its total in the current complete month;
  otherwise `0`. This is a reported-case increase classification task, not a
  confirmed outbreak prediction.
- Evaluation training rows: 391; labels: 208 non-increases and 183 increases.
- Latest feature month in that training partition: October 2022; feature cutoff:
  2022-10-31. Its latest target month is November 2022 (target observation
  through 2022-11-30).
- Full prepared feature coverage: January 2021 through January 2024. Labeled
  current months: January 2021 through April 2023; target months: February
  2021 through May 2023.
- The four held-out target months and small dependent sample do not support a
  reliability claim. The reported probability is not clinically validated or
  known to be calibrated.

## Features and cutoff

For a request with `current_month=YYYY-MM`, all features must be computed from
that district's complete current month and be available by its final calendar
day. The target month is the immediately following month and contributes only
to offline label creation. It must never be supplied to the inference feature
matrix. District names, IDs, dates, target labels, target-month totals, and
target-month weather are not model features.

| Feature | Type/unit | Meaning and required availability |
|---|---|---|
| `reported_dengue_total` | number, reported cases | Sum for all valid daily reports in the complete current month |
| `mean_temperature_c` | number, °C | Mean of aligned daily weather in the complete current month |
| `mean_relative_humidity_pct` | number, % | Mean of aligned daily weather in the complete current month |
| `total_rainfall_mm` | number, mm | Sum of aligned daily rainfall in the complete current month |

Training transformed these columns in this order with `SimpleImputer(strategy="median")`,
`StandardScaler()`, and `LogisticRegression(C=1.0, class_weight="balanced",
max_iter=2000, random_state=42)`. The imputer and scaler were fit only on the
training partition. Although the pipeline includes an imputer, no feature was
missing in the 511 labeled rows; inference should therefore reject missing or
non-finite required fields rather than silently inventing values.

## Request schema

```json
{
  "district_id": "mysuru",
  "current_month": "2026-10"
}
```

`district_id` is a canonical district slug checked against the configured
district registry. `current_month` must be exactly `YYYY-MM`. The caller does
not submit feature values; a future service must resolve them from a validated,
complete district-month source.

## Response schema

```json
{
  "district_id": "mysuru",
  "current_month": "2026-10",
  "target_month": "2026-11",
  "prediction_cutoff": "2026-10-31",
  "status": "model_unavailable",
  "prediction_supported": false,
  "prediction": null,
  "probability_of_reported_case_increase": null,
  "model_version": "district-month-logistic-regression-eval-v1",
  "feature_schema_version": "district-month-features-v1",
  "target_definition": "...",
  "health_data_as_of": "2026-10-31",
  "message": "Current features are complete, but no candidate model artifact is available."
}
```

Statuses: `supported`, `model_unavailable`, `unavailable`, `not_current`, and
`unknown_district`. Prediction and probability must be null for every status
except `supported`. That status requires both outputs and a validated current
feature row. In this step, the model artifact does not exist, so the contract
resolver returns `model_unavailable` even when a test fixture supplies complete
features.

`not_current` is used when the target month has passed or the request is not
based on the latest validated complete feature month. A feature month can
support the target month that is currently underway (for example, a complete
September row can support an October target during October); a next-month target
is eligible only at the feature month's final-day cutoff. `unavailable` means
the month is not complete, feature/source dates cannot be verified, or the
district-month health/weather row is absent or incomplete. Missing disease
reports must never be filled with zero.

## Current integration blockers

- The prepared district-month CSV's latest complete feature month is January
  2024. The source's raw reporting rows extend later, but they do not form
  complete monthly feature rows under the preparation rule. This is stale for
  current forecasting.
- The existing history service returns sums over whatever daily values are
  present and sets `data_as_of` to request time. It does not verify all calendar
  reporting days, so it cannot provide these model features or establish
  freshness as-is.
- The current weather endpoint returns point-in-time/forecast Open-Meteo fields,
  not the aligned daily historical weather aggregates used by this model.
- The current district API registry has 12 districts, while the preparation
  alias map covers 31 and prepared complete months cover 30. The registry must
  be reconciled before asserting all-district inference coverage.
- No candidate model artifact is saved. The legacy daily model artifact is a
  different feature schema and must not be loaded for this contract.

The endpoint is intentionally an assessment/status endpoint until there is a
refreshed, completeness-checked data feed and separately reviewed candidate
model artifact. The existing daily `/api/v1/early-warning/predict` contract is
unchanged and is not used as a fallback.
