
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = ROOT / "data" / "processed" / "dengue_karnataka_clean.csv"
OUTPUT_FILE = ROOT / "data" / "processed" / "dengue_anomalies_review.csv"

DATE = "metadata.recordDate"
DISTRICT = "location.admin2.name"
DAILY = "daily_positive_total"
CUMULATIVE = "cumulative.positive.total"

df = pd.read_csv(INPUT_FILE, low_memory=False)

df[DATE] = pd.to_datetime(df[DATE], errors="coerce")

for col in [DAILY, CUMULATIVE]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.sort_values([DISTRICT, DATE]).copy()

group = df.groupby(DISTRICT, dropna=False)
df["previous_cumulative"] = group[CUMULATIVE].shift(1)
df["cumulative_change"] = group[CUMULATIVE].diff()

df["cumulative_decreased"] = (
    df[CUMULATIVE].notna()
    & df["previous_cumulative"].notna()
    & (df[CUMULATIVE] < df["previous_cumulative"])
)

df["daily_mismatch"] = (
    df[DAILY].notna()
    & df["cumulative_change"].notna()
    & (df[DAILY] != df["cumulative_change"])
)

review = df[df["cumulative_decreased"] | df["daily_mismatch"]].copy()

review.to_csv(OUTPUT_FILE, index=False)

print("Anomaly records exported:", len(review))
print("Cumulative decreases:", int(df["cumulative_decreased"].sum()))
print("Daily mismatches:", int(df["daily_mismatch"].sum()))
print("Saved to:", OUTPUT_FILE)
print("\nOriginal dataset unchanged.")
