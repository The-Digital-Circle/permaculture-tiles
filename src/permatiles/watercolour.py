import numpy as np
from scipy import ndimage
from .textures import sample_periodic

def _wash(color, tex, lo=0.82, hi=1.06):
    """Tint color (RGB tuple) by a [0,1] texture -> float RGB image, mild light/dark variation."""
    c = np.array(color, dtype=np.float32)
    shade = (lo + (hi - lo) * tex)[..., None]
    return np.clip(c[None, None, :] * shade, 0, 255)

def render_padded(masks, palette, textures, gx0, gy0, pad, size, *,
                  river_px=1, river_alpha=0.25, coast_sigma=2.5):
    """Composite one tile on a padded canvas and crop to centre. Returns uint8 RGBA (size,size,4).

    Soft, hand-painted watercolour: coastlines are feathered (no hard outline, Stamen-style) and
    rivers are faint threads. Open water depends only on the 256-period ocean texture, so it stays
    tile-periodic and identical in every tile (the shared ocean tile) — washes and grain are weighted
    by land/lake coverage so pure-ocean pixels are never touched.

    masks: bool arrays 'land','lake','river' of shape (P,P), P = size + 2*pad.
    textures: 'paper' (NxN seamless, world-continuous) and 'ocean' (256x256 seamless, tile-periodic).
    gx0,gy0: global pixel origin of the centre tile's top-left at this zoom.
    """
    P = size + 2 * pad
    paper, ocean = textures["paper"], textures["ocean"]
    ox, oy = gx0 - pad, gy0 - pad
    paper_f = sample_periodic(paper, ox, oy, P, P)
    ocean_f = sample_periodic(ocean, ox, oy, P, P)

    # --- bleed: warp land/lake by a smooth world-coordinate displacement field (kept as float) ---
    nx = sample_periodic(paper, ox + 991, oy + 17, P, P) - 0.5
    ny = sample_periodic(paper, ox + 37, oy + 613, P, P) - 0.5
    amp = pad * 0.6
    rows, cols = np.mgrid[0:P, 0:P]
    coords = np.array([rows + ny * amp, cols + nx * amp])
    def warp(mask):
        return ndimage.map_coordinates(mask.astype(np.float32), coords, order=1, mode="nearest")
    land_w = np.clip(warp(masks["land"]), 0, 1)
    lake_w = np.clip(warp(masks["lake"]), 0, 1)

    # --- feathered coast: soft alphas give an undefined, bleeding edge instead of an outline ---
    land_a = ndimage.gaussian_filter(land_w, coast_sigma)
    lake_a = ndimage.gaussian_filter(lake_w, coast_sigma)

    img = _wash(palette.ocean, ocean_f)
    img = img * (1 - land_a[..., None]) + _wash(palette.land, paper_f) * land_a[..., None]
    img = img * (1 - lake_a[..., None]) + _wash(palette.lake, paper_f) * lake_a[..., None]

    # --- rivers: faint threads, only where they fall on land ---
    if masks["river"].any():
        rmask = ndimage.binary_dilation(masks["river"], iterations=int(river_px)) & (land_a > 0.5)
        ra = rmask[..., None].astype(np.float32) * river_alpha
        img = img * (1 - ra) + _wash(palette.river, paper_f) * ra

    # --- paper grain weighted by land/lake coverage, so open ocean stays pristine & tile-periodic ---
    w = np.clip(land_a + lake_a, 0, 1)[..., None]
    grain = (0.9 + 0.1 * paper_f)[..., None]
    img = img * (1 - w) + np.clip(img * grain, 0, 255) * w

    # --- crop centre and pack RGBA ---
    img = img[pad:pad + size, pad:pad + size, :]
    out = np.empty((size, size, 4), dtype=np.uint8)
    out[..., :3] = img.astype(np.uint8)
    out[..., 3] = 255
    return out
