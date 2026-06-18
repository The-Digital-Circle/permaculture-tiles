import numpy as np
from scipy import ndimage
from .textures import sample_periodic

def _wash(color, tex, lo=0.82, hi=1.06):
    """Tint color (RGB tuple) by a [0,1] texture -> float RGB image, mild light/dark variation."""
    c = np.array(color, dtype=np.float32)
    shade = (lo + (hi - lo) * tex)[..., None]
    return np.clip(c[None, None, :] * shade, 0, 255)

def render_padded(masks, palette, textures, gx0, gy0, pad, size, *, river_px=1):
    """Composite one tile on a padded canvas and crop to centre. Returns uint8 RGBA (size,size,4).

    masks: bool arrays 'land','lake','river' of shape (P,P), P = size + 2*pad.
    textures: 'paper' (NxN seamless, world-continuous) and 'ocean' (256x256 seamless, tile-periodic).
    gx0,gy0: global pixel origin of the centre tile's top-left at this zoom.
    """
    P = size + 2 * pad
    paper, ocean = textures["paper"], textures["ocean"]
    ox, oy = gx0 - pad, gy0 - pad
    paper_f = sample_periodic(paper, ox, oy, P, P)
    ocean_f = sample_periodic(ocean, ox, oy, P, P)

    # --- bleed: warp land/lake by a smooth world-coordinate displacement field ---
    nx = sample_periodic(paper, ox + 991, oy + 17, P, P) - 0.5
    ny = sample_periodic(paper, ox + 37, oy + 613, P, P) - 0.5
    amp = pad * 0.6
    rows, cols = np.mgrid[0:P, 0:P]
    coords = np.array([rows + ny * amp, cols + nx * amp])
    def warp(mask):
        return ndimage.map_coordinates(mask.astype(np.float32), coords, order=1, mode="nearest") > 0.5
    land = warp(masks["land"])
    lake = warp(masks["lake"])
    river = masks["river"]

    # --- base washes (float RGB) ---
    img = _wash(palette.ocean, ocean_f)
    img = np.where(land[..., None], _wash(palette.land, paper_f), img)
    img = np.where(lake[..., None], _wash(palette.lake, paper_f), img)

    # --- wet edge: darker pooled band in the water just outside the coast ---
    coast = ndimage.binary_dilation(land, iterations=max(1, pad // 3)) & ~land
    edge = np.array(palette.wet_edge, dtype=np.float32)
    img = np.where(coast[..., None], 0.5 * img + 0.5 * edge[None, None, :], img)

    # --- rivers: thin lines, only where they fall on land ---
    rmask = (ndimage.binary_dilation(river, iterations=int(river_px)) & land) if river.any() \
        else np.zeros_like(land)
    img = np.where(rmask[..., None], _wash(palette.river, paper_f), img)

    # --- paper grain: land/lake/coast ONLY, so open ocean stays tile-periodic & shareable ---
    grain_mask = (land | lake | coast | rmask)
    grain = (0.9 + 0.1 * paper_f)[..., None]
    img = np.where(grain_mask[..., None], np.clip(img * grain, 0, 255), img)

    # --- crop centre and pack RGBA ---
    img = img[pad:pad + size, pad:pad + size, :]
    out = np.empty((size, size, 4), dtype=np.uint8)
    out[..., :3] = img.astype(np.uint8)
    out[..., 3] = 255
    return out
