
from pathlib import Path
import pandas as pd

from district_aliases import DISTRICT_ALIASES

ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = ROOT / "data" / "raw" / "Updated_Daily_File.csv"
OUTPUT_FILE = ROOT / "data" / "processed" / "dengue_karnataka_clean.csv"
REVIEW_FILE = ROOT / "data" / "processed" / "dengue_districts_needing_review.csv"

DATE = "metadata.recordDate"
DISTRICT = "location.admin2.name"

REQUIRED = [
    DATE,
    DISTRICT,
    "cumulative.positive.total",
    "cumulative.deaths",
    "daily_positive_total",
    "daily_deaths",
]

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Dengue CSV not found: {INPUT_FILE}")

df = pd.read_csv(INPUT_FILE, low_memory=False)

missing_columns = [c for c in REQUIRED if c not in df.columns]
if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")

# Preserve the original district name for auditing.
df["district_original"] = df[DISTRICT].astype("string").str.strip()

# Parse dates and numeric values.
df[DATE] = pd.to_datetime(df[DATE], errors="coerce")

count_columns = [
    "cumulative.positive.total",
    "cumulative.deaths",
    "daily_positive_total",
    "daily_deaths",
]

for col in count_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Standardize district names and apply reviewed aliases.
df["district_normalized"] = (
    df[DISTRICT]
    .astype("string")
    .str.strip()
    .str.upper()
    .str.replace(r"\s+", " ", regex=True)
)

df["district_census2011"] = df["district_normalized"].map(
    DISTRICT_ALIASES
).fillna(df[DISTRICT].astype("string").str.strip())

# Flag names that require manual review.
unmatched_aliases = {"VIJAYANAGAR"}

df["district_mapping_status"] = "name matched or unchanged"
df.loc[
    df["district_normalized"].isin(unmatched_aliases),
    "district_mapping_status",
] = "review required"

# Do not replace missing counts with zero.
df["invalid_date"] = df[DATE].isna()
df["negative_count"] = df[count_columns].lt(0).any(axis=1)

# Save records needing review separately.
review = df[
    df["invalid_date"]
    | df["negative_count"]
    | df["district_mapping_status"].eq("review required")
].copy()

# Keep records with valid dates and non-negative counts.
# Rows with missing count values remain available for review.
clean = df[
    ~df["invalid_date"] & ~df["negative_count"]
].copy()

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
clean.to_csv(OUTPUT_FILE, index=False)
review.to_csv(REVIEW_FILE, index=False)

print("=== DENGUE CLEANING REPORT ===")
print("Input rows:", len(df))
print("Output rows:", len(clean))
print("Rows needing review:", len(review))
print("Invalid dates:", int(df["invalid_date"].sum()))
print("Rows with negative counts:", int(df["negative_count"].sum()))
print("Rows with missing values:", int(df[REQUIRED].isna().any(axis=1).sum()))
print("Output:", OUTPUT_FILE)
print("Review file:", REVIEW_FILE)
print("\nOriginal input file was not modified.")
