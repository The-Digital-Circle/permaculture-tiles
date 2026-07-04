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


def paper_grain(size, seed, clump=0.35):
    """CRISP per-pixel paper grain in [0,1] — the texture real watercolour has and smooth value-noise
    lacks. Built from white noise (sharp, per-pixel) with a little neighbour-clumping so it reads as
    paper fibre rather than TV static. Periodic, so it tiles seamlessly and — being noise — shows no
    visible seam at the wrap. This is the source of the granular light/dark flecks in every wash."""
    rng = np.random.default_rng(seed)
    n = rng.random((size, size))
    if clump:
        nb = (n + np.roll(n, 1, 0) + np.roll(n, -1, 0) + np.roll(n, 1, 1) + np.roll(n, -1, 1)) / 5.0
        n = (1 - clump) * n + clump * nb
    return (n - n.min()) / (np.ptp(n) + 1e-9)


def _brush_tonal(size, seed, layers, angle=(0.0, np.pi)):
    """Overlapping soft brush strokes -> [0,1] tonal field (the footer's 'washes over each other').
    Stamped with wrap-around so the field tiles seamlessly. `layers` are (n, len_frac, wid_frac, opac)
    with lengths/widths given as (min,max) FRACTIONS of size, so the brush scale is period-relative.
    `angle` is the (min,max) stroke-angle range in radians: a NARROW range gives directionally-aligned
    brushwork (the footer look); the full (0,pi) gives isotropic strokes."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    canvas = np.zeros((size, size))
    for n, (lmin, lmax), (wmin, wmax), opac in layers:
        for _ in range(n):
            cx, cy = rng.uniform(0, size, 2)
            ang = rng.uniform(angle[0], angle[1])
            ca, sa = np.cos(ang), np.sin(ang)
            length = rng.uniform(lmin, lmax) * size
            width = rng.uniform(wmin, wmax) * size
            dx = ((xx - cx + size / 2) % size) - size / 2
            dy = ((yy - cy + size / 2) % size) - size / 2
            u = dx * ca + dy * sa
            v = -dx * sa + dy * ca
            along = np.clip(np.abs(u) - length / 2, 0, None)
            canvas += np.exp(-(np.hypot(along, v) / width) ** 2) * opac * rng.uniform(0.6, 1.0)
    return (canvas - canvas.min()) / (np.ptp(canvas) + 1e-9)


def brush_density(size, seed, *, base=0.80, span=0.20, tooth_amp=0.22, floor=0.35,
                  strokes=1.0, bloom=0.15, angle=(0.2, 1.0)):
    """Tileable [0,1] pigment-density field for a watercolour wash. The tonal variation is carried by
    LONG THIN directionally-aligned brush streaks (the footer's brushwork — subtle streaky banding, not
    smudgy round blobs), with only a little isotropic bloom, all under a CRISP fine paper tooth.
    Colourise it with `_colorize` in the compositor. `angle` is the stroke-direction range (keep it
    narrow for aligned brushwork); `strokes`/`bloom` set low for the shared sea tile (whose large-scale
    structure would otherwise repeat as a grid). Tiles seamlessly."""
    n_long, n_med = int(24 * strokes), int(30 * strokes)
    strokemap = _brush_tonal(size, seed, [
        (n_long, (0.32, 0.62), (0.010, 0.020), 0.7),   # long thin streaks -> directional banding
        (n_med,  (0.14, 0.28), (0.008, 0.015), 0.5),   # shorter streaks, same general direction
    ], angle=angle)
    patches = fractal_noise(size, base_cells=max(3, size // 40), octaves=2, seed=seed + 3)  # faint blooms
    tonal = base + span * ((1 - bloom) * strokemap + bloom * patches)
    tooth = paper_grain(size, seed + 7)          # CRISP per-pixel tooth -> sharp paper flecks, not blur
    d = tonal - (0.5 - tooth) * tooth_amp
    return np.clip(d, floor, 1.0)
