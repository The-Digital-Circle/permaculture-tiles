import numpy as np
from permatiles import textures
from permatiles.palette import Palette, darker
from permatiles.watercolour import render_padded

PAL = Palette(land=(169, 184, 154), arid=(233, 195, 156), sea=(143, 198, 192),
              lake=(167, 210, 201), river=(147, 198, 191), paper=(245, 239, 226),
              speckle=(255, 255, 255), accent=(224, 122, 95))
SIZE, PAD = 256, 24

def _textures():
    return {"paper": textures.fractal_noise(1024, 16, 4, 7),
            "ocean": textures.fractal_noise(256, 8, 3, 107),
            "granulation": textures.granulation(512, 5),
            "disp_x": textures.fractal_noise(512, 8, 4, 991),
            "disp_y": textures.fractal_noise(512, 8, 4, 613),
            "speckle": textures.fractal_noise(256, 64, 1, 300)}

def _empty():
    p = SIZE + 2 * PAD
    z = np.zeros((p, p), dtype=bool)
    return {"land": z.copy(), "arid": z.copy(), "lake": z.copy(), "river": z.copy()}

def _land_centre(arid=False):
    p = SIZE + 2 * PAD
    m = _empty()
    m["land"][p // 2 - 40:p // 2 + 40, p // 2 - 40:p // 2 + 40] = True
    if arid:
        m["arid"][p // 2 - 40:p // 2 + 40, p // 2 - 40:p // 2 + 40] = True
    return m

def test_output_shape_and_dtype():
    out = render_padded(_empty(), PAL, _textures(), 0, 0, PAD, SIZE)
    assert out.shape == (SIZE, SIZE, 4) and out.dtype == np.uint8
    assert (out[..., 3] == 255).all()

def test_deterministic():
    t = _textures()
    a = render_padded(_land_centre(), PAL, t, 512, 768, PAD, SIZE)
    b = render_padded(_land_centre(), PAL, t, 512, 768, PAD, SIZE)
    assert np.array_equal(a, b)

def test_open_ocean_identical_across_tiles():
    t = _textures()
    a = render_padded(_empty(), PAL, t, 0, 0, PAD, SIZE)
    b = render_padded(_empty(), PAL, t, 256 * 5, 256 * 9, PAD, SIZE)
    assert np.array_equal(a, b)

def test_coastal_ocean_border_matches_shared_ocean():
    t = _textures()
    coastal = render_padded(_land_centre(), PAL, t, 256 * 3, 256 * 2, PAD, SIZE)
    ocean = render_padded(_empty(), PAL, t, 256 * 3, 256 * 2, PAD, SIZE)
    assert np.array_equal(coastal[0, :, :], ocean[0, :, :])
    assert np.array_equal(coastal[:, 0, :], ocean[:, 0, :])

def test_land_centre_is_sage_sea_corner_is_teal():
    out = render_padded(_land_centre(), PAL, _textures(), 0, 0, PAD, SIZE)[..., :3].astype(int)
    cx = SIZE // 2
    lr, lg, lb = out[cx, cx]
    sr, sg, sb = out[2, 2]
    assert lr - lb > 0          # sage land interior is warm: red exceeds blue
    assert sr - sb < 0          # teal sea corner is cool: blue exceeds red

def test_arid_centre_is_peach_not_sage():
    cx = SIZE // 2
    green = int(render_padded(_land_centre(arid=False), PAL, _textures(), 0, 0, PAD, SIZE)[cx, cx, 0])
    peach = int(render_padded(_land_centre(arid=True), PAL, _textures(), 0, 0, PAD, SIZE)[cx, cx, 0])
    assert peach > green        # peach arid land has more red than sage green land

def test_wet_edges_pool_darker_same_hue_no_navy():
    out = render_padded(_land_centre(), PAL, _textures(), 0, 0, PAD, SIZE)[..., :3].astype(int)
    brightness = out.sum(axis=2)
    assert brightness.min() < sum(PAL.land)          # a pooled edge deeper than the land base wash
    y, x = np.unravel_index(int(np.argmin(brightness)), brightness.shape)
    r, g, b = out[y, x]
    assert g >= b            # darkest pixel stays in-hue (sage/teal); never a navy outline (b>g)
