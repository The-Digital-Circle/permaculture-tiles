import os
import numpy as np
from permatiles import textures, tiles
from permatiles.palette import Palette

PAL = Palette((205, 191, 163), (169, 199, 208), (183, 210, 216),
              (159, 191, 201), (110, 138, 147), (232, 224, 208))

def _tex():
    return {"paper": textures.fractal_noise(1024, 16, 4, 7),
            "ocean": textures.fractal_noise(256, 8, 3, 107)}

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
