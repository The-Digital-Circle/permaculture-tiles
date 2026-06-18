import math
from permatiles import geo

def test_num_tiles():
    assert geo.num_tiles(0) == 1
    assert geo.num_tiles(3) == 8

def test_z0_bounds_cover_world():
    minx, miny, maxx, maxy = geo.tile_bounds_3857(0, 0, 0)
    assert math.isclose(minx, -geo.ORIGIN, rel_tol=1e-9)
    assert math.isclose(maxx, geo.ORIGIN, rel_tol=1e-9)
    assert math.isclose(maxy, geo.ORIGIN, rel_tol=1e-9)

def test_tile_bounds_top_left_quadrant():
    minx, miny, maxx, maxy = geo.tile_bounds_3857(1, 0, 0)
    assert math.isclose(minx, -geo.ORIGIN, rel_tol=1e-9)
    assert math.isclose(maxx, 0.0, abs_tol=1e-6)
    assert math.isclose(maxy, geo.ORIGIN, rel_tol=1e-9)
    assert math.isclose(miny, 0.0, abs_tol=1e-6)

def test_lonlat_to_3857_extremes():
    assert math.isclose(geo.lonlat_to_3857(0, 0)[0], 0.0, abs_tol=1e-6)
    assert math.isclose(geo.lonlat_to_3857(180, 0)[0], geo.ORIGIN, rel_tol=1e-9)

def test_world_px_origin():
    assert geo.world_px_origin(2, 1, 3) == (256, 768)
