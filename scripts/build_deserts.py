"""Hand-authored arid regions -> data/arid.geojson (fallback to the Köppen raster).

Soft circular blobs over the world's major deserts, in EPSG:4326. The renderer softens and displaces
them, so rough placement reads as deliberate peach regions. Usage:

    python scripts/build_deserts.py data/arid.geojson
"""
import sys
import geopandas as gpd
from shapely.geometry import Point

# (name, lon, lat, radius_degrees)
DESERTS = [
    ("Sahara",        13,  23, 19),
    ("Arabian",       45,  22,  9),
    ("Thar",          71,  27,  4),
    ("Karakum",       60,  40,  7),
    ("Gobi",         102,  42,  8),
    ("Taklamakan",    82,  39,  5),
    ("Iran",          58,  32,  6),
    ("Australian",   132, -25, 11),
    ("Kalahari",      22, -23,  6),
    ("Namib",         15, -24,  3),
    ("Atacama",      -69, -23,  4),
    ("Patagonia",    -69, -46,  4),
    ("Southwest US", -111, 35,  7),
    ("Great Basin",  -117, 40,  4),
]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "data/arid.geojson"
    blobs = [Point(lon, lat).buffer(r) for _, lon, lat, r in DESERTS]
    merged = gpd.GeoSeries(blobs, crs=4326).union_all()
    gpd.GeoDataFrame(geometry=[merged], crs=4326).to_file(out, driver="GeoJSON")
    print(f"wrote {out}  ({len(DESERTS)} desert blobs)")


if __name__ == "__main__":
    main()
