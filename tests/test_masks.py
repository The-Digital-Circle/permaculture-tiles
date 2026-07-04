import numpy as np
import geopandas as gpd
from shapely.geometry import box
from permatiles import masks

def test_rasterise_left_half():
    bounds = (0.0, 0.0, 10.0, 10.0)
    geoms = [box(0, 0, 4, 10)]            # left 40% of width
    arr = masks.rasterise(geoms, bounds, 10, 10)
    assert arr.dtype == bool
    assert arr[:, 0].all()               # leftmost column is land
    assert not arr[:, 9].any()           # rightmost column is water

def test_rasterise_empty():
    arr = masks.rasterise([], (0, 0, 10, 10), 10, 10)
    assert arr.shape == (10, 10)
    assert not arr.any()

def test_clip_geoms_filters_by_bbox():
    gdf = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1), box(100, 100, 101, 101)], crs=3857)
    got = masks.clip_geoms(gdf, (0, 0, 10, 10))
    assert len(got) == 1

def test_min_area_px_drops_subpixel_specks():
    bounds = (0.0, 0.0, 256.0, 256.0)          # 1 unit == 1 px
    speck = box(10, 10, 11, 11)                 # ~1 px^2
    big   = box(50, 50, 120, 120)               # large
    arr = masks.rasterise([speck, big], bounds, 256, 256, all_touched=True, min_area_px=4.0)
    assert not arr[245, 10]                      # speck near top (y flipped) dropped
    assert arr[256 - 85, 85]                     # big feature kept

def test_all_touched_false_by_default():
    bounds = (0.0, 0.0, 10.0, 10.0)
    arr = masks.rasterise([box(0, 0, 4, 10)], bounds, 10, 10)
    assert arr.dtype == bool
