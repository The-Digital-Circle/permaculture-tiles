import numpy as np
import pytest
from shapely.geometry import box, MultiPolygon
from scripts.build_arid import decimation_factor, drop_specks, clean, arid_class_mask

def test_koppen_b_classes_are_arid():
    # Beck et al. class ids: 4=BWh 5=BWk 6=BSh 7=BSk are the arid 'B' climates
    grid = np.array([[1, 3, 4], [5, 6, 7], [8, 14, 29]], dtype=np.uint8)
    m = arid_class_mask(grid)
    assert m[0, 2] and m[1, 0] and m[1, 1] and m[1, 2]     # 4,5,6,7 -> arid
    assert not m[0, 0] and not m[0, 1] and not m[2, 0]     # 1,3,8 -> not arid


def test_decimation_factor_downsamples_fine_raster():
    assert decimation_factor(0.0083, 0.05) == 6          # ~1 km raster -> ~0.05 deg grid


def test_decimation_factor_never_upsamples_coarse_raster():
    assert decimation_factor(0.5, 0.05) == 1             # a 0.5 deg raster is read as-is


def test_drop_specks_removes_small_keeps_large():
    big = box(0, 0, 10, 10)                              # area 100
    speck = box(50, 50, 50.2, 50.2)                      # area 0.04
    out = drop_specks(MultiPolygon([big, speck]), 0.1)
    assert out.area == pytest.approx(100)                # speck gone, big kept


def test_clean_drops_specks_and_preserves_extent():
    big = box(0, 0, 10, 10)
    speck = box(50, 50, 50.05, 50.05)                    # area 0.0025 < min_area
    out = clean(MultiPolygon([big, speck]), clean_deg=0.05, simplify_deg=0.03, min_area_deg2=0.1)
    assert out.geom_type == "Polygon"                    # speck removed -> single polygon
    assert out.area == pytest.approx(100, rel=0.02)      # symmetric close => ~no net grow/shrink
    assert out.bounds == pytest.approx((0, 0, 10, 10), abs=0.02)


import os
import geopandas as gpd


def _arid_area_in_box(geom, w, s, e, n):
    return geom.intersection(box(w, s, e, n)).area


def test_arid_geojson_covers_australia_and_sahara():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "arid.geojson")
    g = gpd.read_file(path)
    geom = g.geometry.union_all() if hasattr(g.geometry, "union_all") else g.geometry.unary_union
    parts = list(geom.geoms) if geom.geom_type.startswith("Multi") else [geom]
    # Australia interior must read as predominantly arid. Natural-Earth named deserts gave ~75 deg^2
    # (the "yellow blotches" bug); the Köppen climate mask gives ~450. Primary regression guard.
    assert _arid_area_in_box(geom, 112, -39, 154, -10) >= 250
    # Saharan/Sahel belt at full extent.
    assert _arid_area_in_box(geom, -17, 15, 37, 31) >= 700
    # Deserts stay contiguous, not fragmented label-blobs.
    assert max(p.area for p in parts) >= 800
