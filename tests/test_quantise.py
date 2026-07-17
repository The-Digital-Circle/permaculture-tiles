import io
import pytest
import numpy as np
from PIL import Image
from permatiles.quantise import to_png8, png_color_count, to_webp, encode, ext_for

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

def _grainy_tile(seed=7):
    """A tile of live sage land (187,200,169) plus per-pixel granulation — a stand-in for the paper
    grain, which is the ONLY thing lossy WebP can plausibly destroy. Seeded, so the guard is stable."""
    rng = np.random.default_rng(seed)
    base = np.array([187, 200, 169], dtype=np.int16)
    noise = rng.integers(-6, 7, size=(256, 256, 1))
    rgb = np.clip(base + noise, 0, 255).astype(np.uint8)
    return np.dstack([rgb, np.full((256, 256), 255, np.uint8)]).astype(np.uint8)

def _grain(img):
    """The project's grain metric (scripts/make_swatches.py): mean |adjacent-pixel luma delta|."""
    g = np.asarray(img.convert("L"), dtype=np.float64) / 255.0
    return np.abs(np.diff(g, axis=1)).mean()

def test_webp_signature_and_much_smaller_than_png8():
    rgba = _grainy_tile()
    wp = to_webp(rgba, quality=90)
    assert wp[:4] == b"RIFF" and wp[8:12] == b"WEBP"
    assert len(wp) < len(to_png8(rgba)) / 2      # measured ~10 KB vs ~32 KB on this fixture

def test_webp_q90_keeps_the_paper_grain():
    # THE guard for this whole change. q90 measures ~97% here (87-92% on real tiles); the threshold
    # sits at 85% so a genuine quality regression trips it -- q85 scores 71%, q80 scores 24%.
    rgba = _grainy_tile()
    src = Image.fromarray(rgba, mode="RGBA").convert("RGB")
    got = _grain(Image.open(io.BytesIO(to_webp(rgba, quality=90))))
    assert got >= 0.85 * _grain(src)

def test_webp_q80_fails_the_grain_guard():
    # Proves the guard above can actually fire. A threshold nothing fails is not a guard.
    rgba = _grainy_tile()
    src = Image.fromarray(rgba, mode="RGBA").convert("RGB")
    got = _grain(Image.open(io.BytesIO(to_webp(rgba, quality=80))))
    assert got < 0.85 * _grain(src)

def test_encode_dispatches_on_format():
    rgba = _grainy_tile()
    assert encode(rgba, "png")[:8] == b"\x89PNG\r\n\x1a\n"
    assert encode(rgba, "webp", 90)[:4] == b"RIFF"
    assert encode(rgba)[:8] == b"\x89PNG\r\n\x1a\n"        # default png == v0.2.5 behaviour

def test_encode_rejects_unknown_format():
    with pytest.raises(ValueError):
        encode(_grainy_tile(), "jpeg")

def test_ext_for():
    assert ext_for("png") == "png"
    assert ext_for("webp") == "webp"
    with pytest.raises(ValueError):
        ext_for("gif")
