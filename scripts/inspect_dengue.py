
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "raw" / "Updated_Daily_File.csv"

print("=== ArogyaRadar AI: Dengue Data Inspection ===")

if not FILE.exists():
    print("ERROR: Dengue CSV not found:", FILE)
    raise SystemExit(1)

df = pd.read_csv(FILE, low_memory=False)

print("\nRows:", len(df))
print("Columns:", len(df.columns))

print("\nColumn names:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head().to_string(index=False))

print("\nMissing values:")
print(df.isna().sum().to_string())

date_col = "metadata.recordDate"
district_col = "location.admin2.name"

if date_col in df.columns:
    dates = pd.to_datetime(df[date_col], errors="coerce")
    print("\nEarliest date:", dates.min())
    print("Latest date:", dates.max())
    print("Invalid dates:", dates.isna().sum())

if district_col in df.columns:
    print("\nUnique district count:", df[district_col].nunique())
    print("District names:")
    print(sorted(df[district_col].dropna().astype(str).unique()))

print("\nInspection complete.")
