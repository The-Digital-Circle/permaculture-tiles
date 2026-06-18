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
