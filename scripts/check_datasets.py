
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

district_file = ROOT / "data" / "processed" / "karnataka_districts_census2011.csv"
hmis_file = ROOT / "data" / "raw" / "HMIS report of all States and Districts Across the Months for 2019-20.csv"

print("=== ArogyaRadar AI: Dataset Check ===")

if district_file.exists():
    districts = pd.read_csv(district_file)
    print("\nKarnataka District Dataset")
    print("District count:", len(districts))
    print("Duplicate names:", districts["district_name"].duplicated().sum())
    print("Missing values:", districts.isna().sum().sum())
else:
    print("District CSV not found!")

if hmis_file.exists():
    hmis = pd.read_csv(
        hmis_file,
        encoding="cp1252",
        header=None,
        low_memory=False,
    )
    print("\nHMIS Dataset")
    print("Rows:", len(hmis))
    print("Columns:", len(hmis.columns))
    print("Note: HMIS data is not confirmed dengue case data.")
else:
    print("HMIS CSV not found!")

print("\nDataset check finished.")