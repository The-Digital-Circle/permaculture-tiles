import numpy as np
from permatiles import textures
from permatiles.palette import Palette
from permatiles.prune import is_pure_ocean, shared_ocean_tile

PAL = Palette((205, 191, 163), (169, 199, 208), (183, 210, 216),
              (159, 191, 201), (110, 138, 147), (232, 224, 208))

def test_is_pure_ocean():
    z = np.zeros((8, 8), dtype=bool)
    assert is_pure_ocean({"land": z, "lake": z, "river": z})
    land = z.copy(); land[0, 0] = True
    assert not is_pure_ocean({"land": land, "lake": z, "river": z})

def test_shared_ocean_tile_self_tiles():
    t = {"paper": textures.fractal_noise(1024, 16, 4, 7),
         "ocean": textures.fractal_noise(256, 8, 3, 107)}
    tile = shared_ocean_tile(PAL, t, pad=24, size=256).astype(int)
    doubled = np.concatenate([tile, tile], axis=1)        # lay two copies side by side
    seam = np.abs(doubled[:, 255, :3] - doubled[:, 256, :3]).mean()
    interior = np.abs(doubled[:, 100, :3] - doubled[:, 101, :3]).mean()
    assert seam <= interior + 4                           # join is no worse than ordinary variation
