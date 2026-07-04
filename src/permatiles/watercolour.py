import numpy as np
from scipy import ndimage
from .textures import sample_periodic
from .palette import darker

_DEFAULT_OPTS = {
    "coast_sigma": 1.6, "disp_amp": 0.9, "edge_px": 6.0, "edge_strength": 0.5,
    "river_px": 1, "river_alpha": 0.22, "speckle_alpha": 0.0, "speckle_thresh": 0.985,
}

def _wash(color, tex, lo=0.86, hi=1.06):
    """Tint an RGB colour by a [0,1] texture -> float (H,W,3): mild light/dark pigment variation."""
    c = np.array(color, dtype=np.float32)
    shade = (lo + (hi - lo) * tex)[..., None]
    return np.clip(c[None, None, :] * shade, 0, 255)

def render_padded(masks, palette, textures, gx0, gy0, pad, size, *, opts=None):
    """Watercolour compositor. See the plan / design doc for the layer model. Open water depends
    only on the tile-periodic 'ocean' texture: every land-dependent effect is gated behind
    `land.any()` and weighted by land coverage, so pure-ocean tiles are byte-identical everywhere."""
    o = {**_DEFAULT_OPTS, **(opts or {})}
    P = size + 2 * pad
    ox, oy = gx0 - pad, gy0 - pad
    ocean_t = sample_periodic(textures["ocean"], ox, oy, P, P)

    img = _wash(palette.sea, ocean_t)                      # base sea wash (tile-periodic only)

    if masks["land"].any():
        paper = sample_periodic(textures["paper"], ox, oy, P, P)
        gran = sample_periodic(textures["granulation"], ox, oy, P, P)

        # ragged capillary edges: warp masks by a world-coordinate displacement field
        nx = sample_periodic(textures["disp_x"], ox, oy, P, P) - 0.5
        ny = sample_periodic(textures["disp_y"], ox, oy, P, P) - 0.5
        amp = pad * o["disp_amp"]
        rows, cols = np.mgrid[0:P, 0:P]
        coords = np.array([rows + ny * amp, cols + nx * amp])
        def warp(m):
            return np.clip(ndimage.map_coordinates(m.astype(np.float32), coords, order=1,
                                                   mode="nearest"), 0, 1)
        land_w = warp(masks["land"])
        lake_w = warp(masks["lake"])
        arid_w = warp(masks["arid"]) * land_w
        land_a = ndimage.gaussian_filter(land_w, o["coast_sigma"])
        lake_a = ndimage.gaussian_filter(lake_w, o["coast_sigma"])

        # base washes: two-tone land (sage vs peach), then lakes
        land_rgb = (_wash(palette.land, paper) * (1 - arid_w[..., None])
                    + _wash(palette.arid, paper) * arid_w[..., None])
        img = img * (1 - land_a[..., None]) + land_rgb * land_a[..., None]
        img = img * (1 - lake_a[..., None]) + _wash(palette.lake, paper) * lake_a[..., None]

        # in-hue wet edges: pool a deeper shade of each wash's OWN hue at its boundary
        land_bin = land_a > 0.5
        ep = o["edge_px"]
        def band(dist):
            return np.clip(1 - dist / ep, 0, 1) * (0.7 + 0.6 * gran)
        if land_bin.any():
            sea_band = band(ndimage.distance_transform_edt(~land_bin)) * (1 - land_a)
        else:
            # no land pixel clears the 0.5 alpha threshold (a sub-pixel speck): ~land_bin is all-True,
            # which is a degenerate distance_transform_edt input — guard it, mirroring land_bin.all() below.
            sea_band = np.zeros_like(land_a)
        if land_bin.all():
            land_band = np.zeros_like(land_a)
        else:
            land_band = band(ndimage.distance_transform_edt(land_bin)) * land_a
        land_edge_rgb = (np.array(darker(palette.land), np.float32) * (1 - arid_w[..., None])
                         + np.array(darker(palette.arid), np.float32) * arid_w[..., None])
        def pool(im, b, tone):
            a = np.clip(b * o["edge_strength"], 0, 1)[..., None]
            return im * (1 - a) + tone * a
        img = pool(img, sea_band, np.array(darker(palette.sea), np.float32))
        img = pool(img, land_band, land_edge_rgb)

        # rivers: faint threads, only where they fall on land
        if masks["river"].any():
            rmask = (ndimage.binary_dilation(masks["river"], iterations=int(o["river_px"]))
                     & (land_a > 0.5))
            ra = rmask[..., None].astype(np.float32) * o["river_alpha"]
            img = img * (1 - ra) + _wash(palette.river, paper) * ra

        # optional speckle: land + coastal water only (never open ocean)
        if o["speckle_alpha"] > 0:
            sp = (sample_periodic(textures["speckle"], ox, oy, P, P) > o["speckle_thresh"]).astype(np.float32)
            w = np.clip(land_a + sea_band, 0, 1)
            a = (sp * w * o["speckle_alpha"])[..., None]
            img = img * (1 - a) + np.array(palette.speckle, np.float32) * a

    img = img[pad:pad + size, pad:pad + size, :]
    out = np.empty((size, size, 4), dtype=np.uint8)
    out[..., :3] = img.astype(np.uint8)
    out[..., 3] = 255
    return out
