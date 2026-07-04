from permatiles.palette import Palette, hex_to_rgb, darker

def test_hex_to_rgb():
    assert hex_to_rgb("#ff8000") == (255, 128, 0)
    assert hex_to_rgb("00ff00") == (0, 255, 0)

def test_palette_from_dict():
    d = {"land": "#a9b89a", "arid": "#e9c39c", "sea": "#8fc6c0", "lake": "#a7d2c9",
         "river": "#93c6bf", "paper": "#f5efe2", "speckle": "#ffffff", "accent": "#e07a5f"}
    p = Palette.from_dict(d)
    assert p.land == (169, 184, 154)
    assert p.arid == (233, 195, 156)
    assert p.sea == (143, 198, 192)
    assert p.speckle == (255, 255, 255)

def test_from_dict_defaults_optional_roles():
    # speckle/accent may be omitted; arid falls back to a warm sand if absent
    d = {"land": "#a9b89a", "sea": "#8fc6c0", "lake": "#a7d2c9", "river": "#93c6bf",
         "paper": "#f5efe2"}
    p = Palette.from_dict(d)
    assert p.speckle == (255, 255, 255)
    assert p.arid is not None and len(p.arid) == 3

def test_darker_is_same_hue_but_deeper():
    base = (143, 198, 192)          # teal
    d = darker(base)
    assert sum(d) < sum(base)                       # deeper in value
    # same hue family: green & blue still dominate red, ordering preserved
    assert d[1] >= d[0] and d[2] >= d[0]
