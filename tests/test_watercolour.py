import numpy as np
from permatiles import textures
from permatiles.palette import Palette
from permatiles.watercolour import render_padded

PAL = Palette((205, 191, 163), (169, 199, 208), (183, 210, 216),
              (159, 191, 201), (110, 138, 147), (232, 224, 208))
SIZE, PAD = 256, 24

def _textures():
    return {"paper": textures.fractal_noise(1024, 16, 4, 7),
            "ocean": textures.fractal_noise(256, 8, 3, 107)}

def _empty():
    p = SIZE + 2 * PAD
    z = np.zeros((p, p), dtype=bool)
    return {"land": z.copy(), "lake": z.copy(), "river": z.copy()}

def test_output_shape_and_dtype():
    out = render_padded(_empty(), PAL, _textures(), 0, 0, PAD, SIZE)
    assert out.shape == (SIZE, SIZE, 4)
    assert out.dtype == np.uint8
    assert (out[..., 3] == 255).all()

def test_deterministic():
    a = render_padded(_empty(), PAL, _textures(), 512, 768, PAD, SIZE)
    b = render_padded(_empty(), PAL, _textures(), 512, 768, PAD, SIZE)
    assert np.array_equal(a, b)

def test_open_ocean_identical_across_tiles():
    # all-ocean tiles at different x,y must be byte-identical (period == tile size)
    t = _textures()
    a = render_padded(_empty(), PAL, t, 0, 0, PAD, SIZE)
    b = render_padded(_empty(), PAL, t, 256 * 5, 256 * 9, PAD, SIZE)
    assert np.array_equal(a, b)

def test_coastal_ocean_border_matches_shared_ocean():
    # a tile with land only in the centre keeps ocean borders equal to the all-ocean tile
    t = _textures()
    p = SIZE + 2 * PAD
    masks = _empty()
    masks["land"][p // 2 - 10:p // 2 + 10, p // 2 - 10:p // 2 + 10] = True
    coastal = render_padded(masks, PAL, t, 256 * 3, 256 * 2, PAD, SIZE)
    ocean = render_padded(_empty(), PAL, t, 256 * 3, 256 * 2, PAD, SIZE)
    assert np.array_equal(coastal[0, :, :], ocean[0, :, :])     # top border row
    assert np.array_equal(coastal[:, 0, :], ocean[:, 0, :])     # left border col
