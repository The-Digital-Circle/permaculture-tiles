"""Real desert regions -> data/arid.geojson.

Uses Natural Earth 10m 'geography_regions_polys' (FEATURECLA = "Desert"): 58 named deserts with real
shapes — Sahara, Libyan, Arabian, Kalahari, Namib, Gobi, Taklimakan, Thar, the Australian deserts,
Atacama, Sonoran, Chihuahuan, etc. — instead of hand-placed circles. The compositor clips the arid
mask to land and softens its edge (arid_sigma), so coastlines stay clean. Usage:

    python scripts/build_deserts.py data/arid.geojson
"""
import os
import sys
import geopandas as gpd
import requests

NE_URL = "https://naciscdn.org/naturalearth/10m/physical/ne_10m_geography_regions_polys.zip"
CACHE = "data/ne_10m_geography_regions_polys.zip"


def _regions_zip():
    if not os.path.exists(CACHE):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        r = requests.get(NE_URL, timeout=180)
        r.raise_for_status()
        with open(CACHE, "wb") as f:
            f.write(r.content)
    return CACHE


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "data/arid.geojson"
    g = gpd.read_file(f"zip://{_regions_zip()}")
    fc = g["FEATURECLA"].astype(str).str.contains("Desert", case=False, na=False)
    deserts = g[fc]
    if deserts.crs is None:
        deserts = deserts.set_crs(4326)
    merged = deserts.to_crs(4326).union_all()
    gpd.GeoDataFrame(geometry=[merged], crs=4326).to_file(out, driver="GeoJSON")
    print(f"wrote {out}  ({len(deserts)} real desert polygons)")


if __name__ == "__main__":
    main()
