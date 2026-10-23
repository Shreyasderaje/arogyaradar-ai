
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

columns = [
    DATE,
    DISTRICT,
    DAILY,
    "previous_cumulative",
    CUMULATIVE,
    "cumulative_change",
]

print("=== CUMULATIVE DECREASE EXAMPLES ===")
print(
    df.loc[df["cumulative_decreased"], columns]
    .head(15)
    .to_string(index=False)
)

print("\n=== DAILY / CUMULATIVE MISMATCH EXAMPLES ===")
print(
    df.loc[df["daily_mismatch"], columns]
    .head(15)
    .to_string(index=False)
)

print("\n=== DIAGNOSTIC SUMMARY ===")
print("Districts:", df[DISTRICT].nunique())
print("Rows:", len(df))
print("Cumulative decreases:", int(df["cumulative_decreased"].sum()))
print("Daily mismatches:", int(df["daily_mismatch"].sum()))
print("\nNo source records were modified.")
