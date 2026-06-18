from permatiles.palette import Palette, hex_to_rgb

def test_hex_to_rgb():
    assert hex_to_rgb("#ff8000") == (255, 128, 0)
    assert hex_to_rgb("00ff00") == (0, 255, 0)

def test_palette_from_dict():
    d = {"land": "#010203", "ocean": "#040506", "lake": "#070809",
         "river": "#0a0b0c", "wet_edge": "#0d0e0f", "paper": "#101112"}
    p = Palette.from_dict(d)
    assert p.land == (1, 2, 3)
    assert p.paper == (16, 17, 18)
