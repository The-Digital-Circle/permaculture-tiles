import os
import requests
import geopandas as gpd
from shapely.geometry import box

NE_BASE = "https://naciscdn.org/naturalearth/10m/physical"
LAYERS = {
    "land":   "ne_10m_land.zip",
    "ocean":  "ne_10m_ocean.zip",
    "lakes":  "ne_10m_lakes.zip",
    "rivers": "ne_10m_rivers_lake_centerlines.zip",
}
MERC_LAT = 85.0511287798066

def merc_clip_box():
    """lon/lat clip box at the Web-Mercator latitude limit (Antarctica etc. go to infinity in 3857)."""
    return box(-180, -MERC_LAT, 180, MERC_LAT)

def download(data_dir: str) -> None:
    os.makedirs(data_dir, exist_ok=True)
    for fn in LAYERS.values():
        dest = os.path.join(data_dir, fn)
        if os.path.exists(dest):
            continue
        r = requests.get(f"{NE_BASE}/{fn}", timeout=180)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)

class GeoData:
    def __init__(self, land, ocean, lakes, rivers):
        self.land = land
        self.ocean = ocean
        self.lakes = lakes
        self.rivers = rivers

def load(data_dir: str) -> "GeoData":
    clip = merc_clip_box()
    frames = {}
    for name, fn in LAYERS.items():
        gdf = gpd.read_file(f"zip://{os.path.join(data_dir, fn)}")
        if gdf.crs is None:
            gdf = gdf.set_crs(4326)
        gdf = gpd.clip(gdf, clip).to_crs(3857)
        frames[name] = gdf.reset_index(drop=True)
    return GeoData(frames["land"], frames["ocean"], frames["lakes"], frames["rivers"])
