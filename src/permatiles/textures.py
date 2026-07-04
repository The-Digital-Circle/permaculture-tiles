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

def make_tileable(arr: np.ndarray) -> np.ndarray:
    """Blend an array with its half-offset self so opposite edges match -> seamless when wrapped.
    Classic offset-and-cross-fade: guarantees continuity across the wrap in both axes."""
    a = arr.astype(np.float64)
    a = (a - a.min()) / (np.ptp(a) + 1e-9)
    h, w = a.shape
    rolled = np.roll(np.roll(a, h // 2, axis=0), w // 2, axis=1)
    yy = np.abs(np.linspace(-1, 1, h))[:, None]
    xx = np.abs(np.linspace(-1, 1, w))[None, :]
    wgt = np.clip(1 - np.maximum(yy, xx), 0, 1)     # trust centre, cross-fade to rolled at edges
    out = a * wgt + rolled * (1 - wgt)
    return (out - out.min()) / (np.ptp(out) + 1e-9)

def granulation(size: int, seed: int) -> np.ndarray:
    """Tileable pigment grain: a mid-frequency wash blotch times a fine paper-tooth speckle.
    High local variance (real granulation) unlike the smooth value-noise it replaces; seamless."""
    blotch = fractal_noise(size, base_cells=size // 16, octaves=3, seed=seed)
    tooth  = fractal_noise(size, base_cells=size // 3,  octaves=2, seed=seed + 51)
    g = 0.6 * blotch + 0.4 * tooth
    return (g - g.min()) / (np.ptp(g) + 1e-9)

def load_swatch(path: str, size: int | None = None) -> np.ndarray:
    """Load a PNG as a [0,1] luma texture, optionally resized, made seamlessly tileable."""
    from PIL import Image
    img = Image.open(path).convert("L")
    if size:
        img = img.resize((size, size), Image.LANCZOS)
    arr = np.asarray(img, dtype=np.float64) / 255.0
    return make_tileable(arr)
