
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

for col in [DAILY, CUMULATIVE]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.sort_values([DISTRICT, DATE]).copy()

group = df.groupby(DISTRICT, dropna=False)
df["previous_cumulative"] = group[CUMULATIVE].shift(1)

df["cumulative_decreased"] = (
    df[CUMULATIVE].notna()
    & df["previous_cumulative"].notna()
    & (df[CUMULATIVE] < df["previous_cumulative"])
)

df["daily_mismatch"] = (
    df[DAILY].notna()
    & group[CUMULATIVE].diff().notna()
    & (df[DAILY] != group[CUMULATIVE].diff())
)

print("=== MOST COMMON REPORTING DATES ===")

date_summary = (
    df.groupby(DATE)
    .agg(
        districts_reporting=(DISTRICT, "nunique"),
        zero_cumulative=(CUMULATIVE, lambda s: (s == 0).sum()),
        positive_daily=(DAILY, lambda s: (s > 0).sum()),
        decreases=("cumulative_decreased", "sum"),
        mismatches=("daily_mismatch", "sum"),
    )
    .sort_values(
        ["decreases", "mismatches", "zero_cumulative"],
        ascending=False,
    )
)

print(date_summary.head(15).to_string())

print("\n=== DISTRICT RECORD COUNTS ===")
print(df.groupby(DISTRICT).size().sort_values().to_string())

print("\nSource data has not been modified.")
