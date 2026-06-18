import numpy as np

def seamless_value_noise(size: int, cells: int, seed: int) -> np.ndarray:
    """size×size float array in [0,1] that tiles seamlessly: bilinear interpolation over a
    periodic random lattice of cells×cells."""
    rng = np.random.default_rng(seed)
    lattice = rng.random((cells, cells))
    u = (np.arange(size) / size) * cells
    iu = np.floor(u).astype(int)
    f = u - iu
    i0 = iu % cells
    i1 = (iu + 1) % cells
    fy = f[:, None]; fx = f[None, :]
    y0 = i0[:, None]; y1 = i1[:, None]
    x0 = i0[None, :]; x1 = i1[None, :]
    v00 = lattice[y0, x0]; v01 = lattice[y0, x1]
    v10 = lattice[y1, x0]; v11 = lattice[y1, x1]
    top = v00 * (1 - fx) + v01 * fx
    bot = v10 * (1 - fx) + v11 * fx
    return top * (1 - fy) + bot * fy

def fractal_noise(size: int, base_cells: int, octaves: int, seed: int) -> np.ndarray:
    """Sum of seamless octaves, normalised to [0,1]. Stays seamless (every octave is periodic)."""
    out = np.zeros((size, size))
    amp = 1.0
    total = 0.0
    for o in range(octaves):
        out += amp * seamless_value_noise(size, base_cells * (2 ** o), seed + o)
        total += amp
        amp *= 0.5
    out /= total
    return out

def sample_periodic(tex: np.ndarray, gx0: int, gy0: int, w: int, h: int) -> np.ndarray:
    """Sample a periodic texture at global pixel offsets (gx0,gy0) for a w×h window.
    Continuous across adjacent windows; identical for windows a whole period apart."""
    T = tex.shape[0]
    xs = (gx0 + np.arange(w)) % T
    ys = (gy0 + np.arange(h)) % T
    return tex[np.ix_(ys, xs)]
