import numpy as np
from permatiles import textures
from permatiles.palette import Palette
from permatiles.prune import is_pure_ocean, shared_ocean_tile

PAL = Palette(land=(169, 184, 154), arid=(233, 195, 156), sea=(143, 198, 192),
              lake=(167, 210, 201), river=(147, 198, 191), paper=(245, 239, 226),
              speckle=(255, 255, 255), accent=(224, 122, 95))

def test_is_pure_ocean():
    z = np.zeros((8, 8), dtype=bool)
    assert is_pure_ocean({"land": z, "lake": z, "river": z})
    land = z.copy(); land[0, 0] = True
    assert not is_pure_ocean({"land": land, "lake": z, "river": z})

def test_shared_ocean_tile_self_tiles():
    t = {"paper": textures.fractal_noise(1024, 16, 4, 7),
         "ocean": textures.fractal_noise(256, 8, 3, 107),
         "granulation": textures.granulation(512, 5),
         "disp_x": textures.fractal_noise(512, 8, 4, 991),
         "disp_y": textures.fractal_noise(512, 8, 4, 613),
         "speckle": textures.fractal_noise(256, 64, 1, 300)}
    tile = shared_ocean_tile(PAL, t, pad=24, size=256).astype(int)
    doubled = np.concatenate([tile, tile], axis=1)        # lay two copies side by side
    seam = np.abs(doubled[:, 255, :3] - doubled[:, 256, :3]).mean()
    interior = np.abs(doubled[:, 100, :3] - doubled[:, 101, :3]).mean()
    assert seam <= interior + 4                           # join is no worse than ordinary variation
