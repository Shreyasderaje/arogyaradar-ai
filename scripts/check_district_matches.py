
from pathlib import Path
import pandas as pd
import re
import unicodedata

ROOT = Path(__file__).resolve().parent.parent

DENGUE_FILE = ROOT / "data" / "raw" / "Updated_Daily_File.csv"
DISTRICT_FILE = ROOT / "data" / "processed" / "karnataka_districts_census2011.csv"


def normalize(name):
    if pd.isna(name):
        return ""

    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.upper().split())


dengue = pd.read_csv(DENGUE_FILE, usecols=["location.admin2.name"])
census = pd.read_csv(DISTRICT_FILE)

dengue_names = sorted(
    dengue["location.admin2.name"].dropna().astype(str).unique()
)

census_names = sorted(
    census["district_name"].dropna().astype(str).unique()
)

census_lookup = {normalize(name): name for name in census_names}

print("=== DISTRICT NAME MATCHING ===")

matched = []
unmatched = []

for name in dengue_names:
    key = normalize(name)

    if key in census_lookup:
        matched.append((name, census_lookup[key]))
    else:
        unmatched.append(name)

print("\nExact normalized matches:", len(matched))
for current, old in matched:
    print(f"{current} -> {old}")

print("\nNames needing review:", len(unmatched))
for name in unmatched:
    print("-", name)
