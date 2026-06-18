import numpy as np
from permatiles.quantise import to_png8, png_color_count

def _gradient_tile():
    g = np.linspace(0, 255, 256, dtype=np.uint8)
    rgb = np.stack([np.tile(g, (256, 1)),
                    np.tile(g[:, None], (1, 256)),
                    np.full((256, 256), 128, dtype=np.uint8)], axis=-1)
    rgba = np.dstack([rgb, np.full((256, 256), 255, dtype=np.uint8)])
    return rgba.astype(np.uint8)

def test_png8_signature_and_colours():
    png = to_png8(_gradient_tile())
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert png_color_count(png) <= 256

def test_png8_smaller_than_raw():
    png = to_png8(_gradient_tile())
    assert len(png) < 256 * 256 * 3
