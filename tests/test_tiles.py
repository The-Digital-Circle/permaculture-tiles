import os
import numpy as np
from permatiles import textures, tiles
from permatiles.palette import Palette

PAL = Palette(land=(169, 184, 154), arid=(233, 195, 156), sea=(143, 198, 192),
              lake=(167, 210, 201), river=(147, 198, 191), paper=(245, 239, 226),
              speckle=(255, 255, 255), accent=(224, 122, 95))

def _tex():
    return {"paper": textures.fractal_noise(1024, 16, 4, 7),
            "ocean": textures.fractal_noise(256, 8, 3, 107),
            "granulation": textures.granulation(512, 5),
            "disp_x": textures.fractal_noise(512, 8, 4, 991),
            "disp_y": textures.fractal_noise(512, 8, 4, 613),
            "speckle": textures.fractal_noise(256, 64, 1, 300)}

def test_render_zoom_writes_land_prunes_ocean(tmp_path, synthetic_geodata):
    # z1 has 4 tiles: eastern column (x=1) is land, western column (x=0) is open ocean -> pruned
    stats = tiles.render_zoom(1, synthetic_geodata, _tex(), PAL, str(tmp_path), pad=24, size=256)
    assert stats["written"] == 2
    assert stats["pruned"] == 2
    assert os.path.exists(tmp_path / "1" / "1" / "0.png")     # an eastern (land) tile
    assert not os.path.exists(tmp_path / "1" / "0")           # western column pruned

def test_render_tile_returns_none_for_open_ocean(synthetic_geodata):
    png = tiles.render_tile(1, 0, 0, synthetic_geodata, _tex(), PAL, pad=24, size=256)
    assert png is None

def test_lakes_and_rivers_gated_below_min_zoom(synthetic_geodata):
    # at z1 (below lake_min_zoom=4, river_min_zoom=6) inland water is suppressed: the tile still
    # renders (land present) but no lake/river pixels are drawn. We assert via mask build.
    from permatiles import tiles as T
    m = T.build_masks(1, 1, 0, synthetic_geodata, pad=24, size=256, opts=None)
    assert m["land"].any()
    assert not m["lake"].any()
    assert not m["river"].any()

def test_lakes_present_at_high_zoom(synthetic_geodata):
    # a z6 tile covering the synthetic lake's centroid actually draws lake pixels (gate open at z>=4)
    from permatiles import tiles as T, geo
    z = 6
    cx3, cy3 = geo.ORIGIN * 0.45, geo.ORIGIN * 0.15     # centroid of the fixture lake box
    span = geo.tile_span_m(z)
    x = int((cx3 + geo.ORIGIN) / span)
    y = int((geo.ORIGIN - cy3) / span)
    m = T.build_masks(z, x, y, synthetic_geodata, pad=24, size=256, opts=None)
    assert m["lake"].any()          # real assertion: lake is present, not gated away
