import os
import requests
import geopandas as gpd
from shapely.geometry import box

NE_BASE = "https://naciscdn.org/naturalearth/10m/physical"
NE_CULTURAL = "https://naciscdn.org/naturalearth/10m/cultural"
LAYERS = {
    "land":   "ne_10m_land.zip",
    "ocean":  "ne_10m_ocean.zip",
    "lakes":  "ne_10m_lakes.zip",
    "rivers": "ne_10m_rivers_lake_centerlines.zip",
}
URBAN_FILE = "ne_10m_urban_areas.zip"   # cultural layer: built-up urban footprints (painted coral)
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
    dest = os.path.join(data_dir, URBAN_FILE)
    if not os.path.exists(dest):
        r = requests.get(f"{NE_CULTURAL}/{URBAN_FILE}", timeout=180)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)

class GeoData:
    def __init__(self, land, ocean, lakes, rivers, arid=None, urban=None):
        self.land = land
        self.ocean = ocean
        self.lakes = lakes
        self.rivers = rivers
        self.arid = arid
        self.urban = urban

def load(data_dir: str) -> "GeoData":
    clip = merc_clip_box()
    frames = {}
    for name, fn in LAYERS.items():
        gdf = gpd.read_file(f"zip://{os.path.join(data_dir, fn)}")
        if gdf.crs is None:
            gdf = gdf.set_crs(4326)
        gdf = gpd.clip(gdf, clip).to_crs(3857)
        frames[name] = gdf.reset_index(drop=True)
    arid = None
    arid_path = os.path.join(data_dir, "arid.geojson")
    if os.path.exists(arid_path):
        a = gpd.read_file(arid_path)
        if a.crs is None:
            a = a.set_crs(4326)
        arid = gpd.clip(a, clip).to_crs(3857).reset_index(drop=True)
    urban = None
    urban_path = os.path.join(data_dir, URBAN_FILE)
    if os.path.exists(urban_path):
        u = gpd.read_file(f"zip://{urban_path}")
        if u.crs is None:
            u = u.set_crs(4326)
        urban = gpd.clip(u, clip).to_crs(3857).reset_index(drop=True)
    return GeoData(frames["land"], frames["ocean"], frames["lakes"], frames["rivers"], arid, urban)
