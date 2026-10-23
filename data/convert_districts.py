
import geopandas as gpd
from pathlib import Path

data_dir = Path(__file__).parent
shapefile = data_dir / "2011_Dist.shp"
output_dir = data_dir.parent / "public" / "data"
output_file = output_dir / "karnataka-districts.geojson"

output_dir.mkdir(parents=True, exist_ok=True)

districts = gpd.read_file(shapefile)

print("Columns:", list(districts.columns))
print("Coordinate system:", districts.crs)
print("Available states:")
print(districts["ST_NM"].dropna().unique())

karnataka = districts[
    districts["ST_NM"].astype(str).str.strip().str.casefold()
    == "karnataka"
].copy()

if karnataka.empty:
    raise ValueError(
        "No Karnataka records found. Check the printed state names and columns."
    )

if karnataka.crs is None:
    raise ValueError("The shapefile has no CRS; cannot safely convert coordinates.")

karnataka = karnataka.to_crs("EPSG:4326")
karnataka.to_file(output_file, driver="GeoJSON")

print(f"Exported {len(karnataka)} district features to {output_file}")
