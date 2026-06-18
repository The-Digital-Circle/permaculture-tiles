import geopandas as gpd
import pytest
from shapely.geometry import box, LineString
from permatiles import data, geo

@pytest.fixture
def synthetic_geodata():
    """A 'continent' filling (most of) the eastern half of the world in EPSG:3857, one lake, one
    river. Land starts a touch east of the x=0 tile seam so the western ocean column prunes cleanly
    (avoids an all_touched stray pixel exactly on the tile boundary)."""
    O = geo.ORIGIN
    land = gpd.GeoDataFrame(geometry=[box(O * 0.05, -O, O, O)], crs=3857)
    ocean = gpd.GeoDataFrame(geometry=[box(-O, -O, 0, O)], crs=3857)
    lakes = gpd.GeoDataFrame(geometry=[box(O * 0.4, O * 0.1, O * 0.5, O * 0.2)], crs=3857)
    rivers = gpd.GeoDataFrame(geometry=[LineString([(O * 0.2, 0), (O * 0.2, O * 0.3)])], crs=3857)
    return data.GeoData(land, ocean, lakes, rivers)
