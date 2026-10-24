"""Canonical Karnataka district-name handling shared by data scripts.

The source datasets mix present-day spellings with older census spellings.
Vijayanagara is kept as its own district; it is never mapped to Ballari.
"""

import re
import unicodedata


# Keep this mapping for clean_dengue.py, which stores the historical source
# name in ``district_census2011``. New joins should use canonical IDs below.
DISTRICT_ALIASES = {
    "BELAGAVI": "Belgaum",
    "BENGALURU RURAL": "Bangalore Rural",
    "BENGALURU URBAN": "Bangalore",
    "BENGALURU SOUTH": "Ramanagara",
    "CHAMARAJANAGARA": "Chamrajnagar",
    "CHIKKAMAGALURU": "Chikmagalur",
    "DAVANGERE": "Davanagere",
    "KALABURAGI": "Gulbarga",
    "MYSURU": "Mysore",
    "SHIVAMOGGA": "Shimoga",
    "TUMAKURU": "Tumkur",
    "VIJAYAPURA": "Bijapur",
}


CANONICAL_DISTRICT_NAMES = {
    "bagalkote": "Bagalkote",
    "ballari": "Ballari",
    "belagavi": "Belagavi",
    "bengaluru-rural": "Bengaluru Rural",
    "bengaluru-south": "Bengaluru South",
    "bengaluru-urban": "Bengaluru Urban",
    "bidar": "Bidar",
    "chamarajanagara": "Chamarajanagara",
    "chikkaballapur": "Chikkaballapur",
    "chikkamagaluru": "Chikkamagaluru",
    "chitradurga": "Chitradurga",
    "dakshina-kannada": "Dakshina Kannada",
    "davangere": "Davangere",
    "dharwad": "Dharwad",
    "gadag": "Gadag",
    "hassan": "Hassan",
    "haveri": "Haveri",
    "kalaburagi": "Kalaburagi",
    "kodagu": "Kodagu",
    "kolar": "Kolar",
    "koppal": "Koppal",
    "mandya": "Mandya",
    "mysuru": "Mysuru",
    "raichur": "Raichur",
    "shivamogga": "Shivamogga",
    "tumakuru": "Tumakuru",
    "udupi": "Udupi",
    "uttara-kannada": "Uttara Kannada",
    "vijayanagara": "Vijayanagara",
    "vijayapura": "Vijayapura",
    "yadgir": "Yadgir",
}


_NAME_ALIASES = {
    "bagalkote": "bagalkote",
    "bagalkot": "bagalkote",
    "ballari": "ballari",
    "bellary": "ballari",
    "belagavi": "belagavi",
    "belgaum": "belagavi",
    "bengaluru rural": "bengaluru-rural",
    "bangalore rural": "bengaluru-rural",
    "bengaluru south": "bengaluru-south",
    "ramanagara": "bengaluru-south",
    "bengaluru urban": "bengaluru-urban",
    "bangalore urban": "bengaluru-urban",
    "bangalore": "bengaluru-urban",
    "bidar": "bidar",
    "chamarajanagara": "chamarajanagara",
    "chamarajanagar": "chamarajanagara",
    "chamrajnagar": "chamarajanagara",
    "chamrajnagara": "chamarajanagara",
    "chikkaballapur": "chikkaballapur",
    "chikkaballapura": "chikkaballapur",
    "chikkamagaluru": "chikkamagaluru",
    "chikmagalur": "chikkamagaluru",
    "chitradurga": "chitradurga",
    "dakshina kannada": "dakshina-kannada",
    "davangere": "davangere",
    "davanagere": "davangere",
    "dharwad": "dharwad",
    "gadag": "gadag",
    "hassan": "hassan",
    "haveri": "haveri",
    "kalaburagi": "kalaburagi",
    "gulbarga": "kalaburagi",
    "kodagu": "kodagu",
    "kolar": "kolar",
    "koppal": "koppal",
    "mandya": "mandya",
    "mysuru": "mysuru",
    "mysore": "mysuru",
    "raichur": "raichur",
    "shivamogga": "shivamogga",
    "shimoga": "shivamogga",
    "tumakuru": "tumakuru",
    "tumkur": "tumakuru",
    "udupi": "udupi",
    "uttara kannada": "uttara-kannada",
    "vijayanagara": "vijayanagara",
    "vijayanagar": "vijayanagara",
    "vijayapura": "vijayapura",
    "bijapur": "vijayapura",
    "yadgir": "yadgir",
    "yadgiri": "yadgir",
}


def normalize_district_name(value):
    """Return a normalized spelling suitable for alias lookup."""
    if value is None:
        return ""

    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^A-Za-z0-9]+", " ", text).upper().split()).lower()


def canonical_district_id(value):
    """Map a known district spelling to its stable current district ID.

    Unknown values return ``None`` so callers can report them rather than
    accidentally joining unrelated records.
    """
    normalized = normalize_district_name(value)
    return _NAME_ALIASES.get(normalized)
