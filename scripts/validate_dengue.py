
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "processed" / "dengue_karnataka_clean.csv"

DATE = "metadata.recordDate"
DISTRICT = "location.admin2.name"
DAILY = "daily_positive_total"
CUMULATIVE = "cumulative.positive.total"

df = pd.read_csv(FILE, low_memory=False)
df[DATE] = pd.to_datetime(df[DATE], errors="coerce")

print("=== DENGUE DATA VALIDATION ===")
print("Total rows:", len(df))
print("Unique districts:", df[DISTRICT].nunique())
print("Date range:", df[DATE].min(), "to", df[DATE].max())

# Check duplicate district-date records.
duplicates = df.duplicated([DISTRICT, DATE], keep=False)
print("\nRows belonging to duplicate district-date pairs:", int(duplicates.sum()))

# Check daily and cumulative case counts.
df = df.sort_values([DISTRICT, DATE])
daily = pd.to_numeric(df[DAILY], errors="coerce")
cumulative = pd.to_numeric(df[CUMULATIVE], errors="coerce")

print("\nDaily cases summary:")
print(daily.describe().to_string())

print("\nCumulative cases summary:")
print(cumulative.describe().to_string())


# Sort by district and date before comparing consecutive records.
df["_validation_date"] = pd.to_datetime(
    df["metadata.recordDate"], errors="coerce"
)

df = df.sort_values(
    ["district_census2011", "_validation_date"]
).reset_index(drop=True)

cumulative = pd.to_numeric(
    df["cumulative.positive.total"], errors="coerce"
)
daily = pd.to_numeric(
    df["daily_positive_total"], errors="coerce"
)

# Cumulative counts should generally not decrease.
previous = cumulative.groupby(df["district_census2011"]).shift(1)
decreases = cumulative.lt(previous) & cumulative.notna() & previous.notna()

print("\nCumulative decreases:", int(decreases.sum()))

# Compare daily cases with changes in cumulative cases.
change = cumulative.groupby(df["district_census2011"]).diff()
comparable = daily.notna() & change.notna()

mismatches = comparable & daily.ne(change)
print("Daily vs cumulative-change mismatches:", int(mismatches.sum()))

# Save flagged records for manual review.
flagged = df.loc[decreases | mismatches].copy()
flagged["cumulative_decrease_flag"] = decreases.loc[flagged.index].to_numpy()
flagged["daily_change_mismatch_flag"] = mismatches.loc[flagged.index].to_numpy()

review_path = (
    __import__("pathlib").Path(__file__).resolve().parent.parent
    / "data" / "processed" / "dengue_validation_review.csv"
)
review_path.parent.mkdir(parents=True, exist_ok=True)
flagged.to_csv(review_path, index=False)

print("Flagged records saved to:", review_path)
print("\nValidation finished. Investigate flagged records before modeling.")
