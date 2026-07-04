import numpy as np
from permatiles import textures
from permatiles.palette import Palette, darker
from permatiles.watercolour import render_padded

PAL = Palette(land=(169, 184, 154), arid=(233, 195, 156), sea=(143, 198, 192),
              lake=(167, 210, 201), river=(147, 198, 191), paper=(245, 239, 226),
              speckle=(255, 255, 255), accent=(224, 122, 95))
SIZE, PAD = 256, 24

def _textures():
    return {"land_density": textures.brush_density(512, 40),
            "sea_density": textures.brush_density(256, 100, base=0.90, span=0.08,
                                                  tooth_amp=0.14, floor=0.60, strokes=0.35),
            "land_grain": textures.paper_grain(512, 200),
            "sea_grain": textures.paper_grain(256, 210),
            "disp_x": textures.fractal_noise(512, 8, 4, 991),
            "disp_y": textures.fractal_noise(512, 8, 4, 613),
            "speckle": textures.fractal_noise(256, 64, 1, 300)}

def _empty():
    p = SIZE + 2 * PAD
    z = np.zeros((p, p), dtype=bool)
    return {"land": z.copy(), "arid": z.copy(), "lake": z.copy(), "river": z.copy()}

def _land_centre(arid=False, urban=False):
    p = SIZE + 2 * PAD
    m = _empty()
    m["land"][p // 2 - 40:p // 2 + 40, p // 2 - 40:p // 2 + 40] = True
    if arid:
        m["arid"][p // 2 - 40:p // 2 + 40, p // 2 - 40:p // 2 + 40] = True
    if urban:
        m["urban"] = np.zeros((p, p), dtype=bool)
        m["urban"][p // 2 - 20:p // 2 + 20, p // 2 - 20:p // 2 + 20] = True
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

def test_urban_centre_is_coral():
    cx = SIZE // 2
    out = render_padded(_land_centre(urban=True), PAL, _textures(), 0, 0, PAD, SIZE)[..., :3].astype(int)
    r, g, b = out[cx, cx]
    assert r > g > b            # coral urban fill is warm: red dominant, then green, then blue
    sage = render_padded(_land_centre(urban=False), PAL, _textures(), 0, 0, PAD, SIZE)[cx, cx, :3].astype(int)
    assert r - b > int(sage[0]) - int(sage[2])   # far warmer than the sage land it replaces

def test_paper_gap_at_coast_is_cream_not_ink():
    out = render_padded(_land_centre(), PAL, _textures(), 0, 0, PAD, SIZE)[..., :3].astype(int)
    paper = np.array(PAL.paper)
    d = np.abs(out - paper).sum(axis=2)              # per-pixel distance to the cream paper colour
    row = SIZE // 2
    interior = d[row, SIZE // 2]                     # sage land, far from any coast
    sea = d[row, 6]                                  # open teal sea
    coast = d[row, 68:108]                           # the left shoreline of the centred land square
    # the shoreline reverts toward paper (a cream gap), unlike the land wash or the open sea
    assert coast.min() < interior and coast.min() < sea
    gx = 68 + int(np.argmin(coast))
    r, g, b = out[row, gx]
    assert r > 170 and g > 170 and b > 150          # bright cream, never a dark ink outline
