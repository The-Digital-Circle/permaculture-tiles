import numpy as np
from permatiles import textures

def test_noise_shape_and_range():
    n = textures.seamless_value_noise(64, 8, seed=1)
    assert n.shape == (64, 64)
    assert n.min() >= 0.0 and n.max() <= 1.0

def test_fractal_shape_and_range():
    n = textures.fractal_noise(64, 4, octaves=3, seed=2)
    assert n.shape == (64, 64)
    assert n.min() >= 0.0 and n.max() <= 1.0

def test_sample_periodic_identity():
    tex = textures.fractal_noise(32, 4, octaves=2, seed=3)
    got = textures.sample_periodic(tex, 0, 0, 32, 32)
    assert np.array_equal(got, tex)

def test_sample_periodic_wraps_at_period():
    tex = textures.fractal_noise(32, 4, octaves=2, seed=4)
    a = textures.sample_periodic(tex, 0, 0, 8, 8)
    b = textures.sample_periodic(tex, 32, 64, 8, 8)   # offsets are multiples of 32
    assert np.array_equal(a, b)

def test_granulation_range():
    g = textures.granulation(256, seed=3)
    assert g.shape == (256, 256)
    assert g.min() >= 0.0 and g.max() <= 1.0

def test_granulation_grainier_than_smooth_noise():
    # the whole point: granulation has real high-frequency grain, unlike the smooth value-noise
    # (used for 'paper') that produced the cloudy blobs — so its adjacent-pixel variation is larger.
    g = textures.granulation(256, seed=3)
    smooth = textures.fractal_noise(256, 16, 4, 3)
    assert np.abs(np.diff(g)).mean() > np.abs(np.diff(smooth)).mean()

def test_granulation_seamless_no_excess_seam():
    # built from periodic noise, so it tiles: the wrap-edge jump is no worse than ordinary interior
    # detail (an absolute threshold would wrongly flag grain as a seam).
    g = textures.granulation(256, seed=3)
    interior = float(np.abs(np.diff(g, axis=1)).max())
    seam = float(np.abs(g[:, -1] - g[:, 0]).max())
    assert seam <= interior * 2.0 + 1e-6

def test_make_tileable_reduces_edge_mismatch():
    # a smooth ramp has maximally different left/right edges; make_tileable must close that gap
    ramp = np.tile(np.linspace(0, 1, 128), (128, 1))
    raw_gap = abs(ramp[:, -1].mean() - ramp[:, 0].mean())      # ~1.0
    t = textures.make_tileable(ramp)
    new_gap = abs(t[:, -1].mean() - t[:, 0].mean())
    assert new_gap < raw_gap * 0.6
