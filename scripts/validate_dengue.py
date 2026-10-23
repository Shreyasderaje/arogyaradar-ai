
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

# Cumulative counts should generally not decrease.
previous = cumulative.groupby(df[DISTRICT]).shift(1)
decreases = cumulative.lt(previous) & cumulative.notna() & previous.notna()

print("\nCumulative decreases:", int(decreases.sum()))

# Compare daily cases with changes in cumulative cases.
change = cumulative.groupby(df[DISTRICT]).diff()
comparable = daily.notna() & change.notna()

mismatches = comparable & daily.ne(change)
print("Daily vs cumulative-change mismatches:", int(mismatches.sum()))

print("\nValidation finished. Investigate flagged records before modeling.")
