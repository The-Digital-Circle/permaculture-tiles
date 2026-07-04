import numpy as np
from scipy import ndimage
from .textures import sample_periodic

_DEFAULT_OPTS = {
    "disp_amp": 0.55, "coast_aa": 0.5, "arid_sigma": 5.0,
    "pool_k": 0.72,                       # how dark a fully-concentrated pigment spot goes (×rgb)
    "sea_gran": 0.20, "land_gran": 0.30,  # granulation strength (pigment settling into paper tooth)
    "rim_off": 1.6, "rim_px": 3.0, "rim_strength": 0.65,   # soft in-hue pooled wet edge at coasts
    "gap_px": 2.0, "gap_strength": 0.72,  # cream paper gap straddling the shoreline
    "river_alpha": 0.20, "river_px": 1,
    "speckle_alpha": 0.10, "speckle_thresh": 0.984,
}


def _colorize(d, base, paper):
    """Pigment on paper (the light side of a wash): the paper colour shows through where density `d`
    is low, full pigment where high. Dark pigment concentration is layered on separately."""
    b = np.array(base, np.float32)
    p = np.array(paper, np.float32)
    dd = d[..., None]
    return np.clip(p * (1 - dd) + b * dd, 0, 255)


def render_padded(masks, palette, textures, gx0, gy0, pad, size, *, opts=None):
    """Watercolour compositor. Every wash is pigment-on-paper (paper breathes through as light flecks)
    with a granular pigment concentration on top (settles into the paper tooth as darker specks); each
    shoreline is a crisp ragged brush edge with a soft in-hue POOLED wet edge just inside it and a cream
    PAPER GAP straddling it — never an ink line. Open water depends ONLY on the tile-periodic sea
    textures; all land-dependent effects are gated behind `land.any()` and multiplied by the land mask,
    so pure-ocean tiles stay byte-identical everywhere and remain prunable."""
    o = {**_DEFAULT_OPTS, **(opts or {})}
    P = size + 2 * pad
    ox, oy = gx0 - pad, gy0 - pad
    paper_c = np.array(palette.paper, np.float32)
    k = o["pool_k"]

    # base sea wash + tile-periodic granulation (darker where pigment settled) — seam-safe by design
    img = _colorize(sample_periodic(textures["sea_density"], ox, oy, P, P), palette.sea, palette.paper)
    sdark = (o["sea_gran"] * (1 - sample_periodic(textures["sea_grain"], ox, oy, P, P)))[..., None]
    img = img * (1 - sdark) + img * k * sdark

    if masks["land"].any():
        land_d = sample_periodic(textures["land_density"], ox, oy, P, P)   # world-continuous

        # ragged brush-edge coasts: warp masks by a world-coordinate displacement field. Kept CRISP
        # (order-1 interpolation gives ~1px anti-alias; only a sub-pixel gaussian, no soft feather).
        nx = sample_periodic(textures["disp_x"], ox, oy, P, P) - 0.5
        ny = sample_periodic(textures["disp_y"], ox, oy, P, P) - 0.5
        amp = pad * o["disp_amp"]
        rows, cols = np.mgrid[0:P, 0:P]
        coords = np.array([rows + ny * amp, cols + nx * amp])

        def warp(m):
            w = ndimage.map_coordinates(m.astype(np.float32), coords, order=1, mode="nearest")
            if o["coast_aa"]:
                w = ndimage.gaussian_filter(w, o["coast_aa"])
            return np.clip(w, 0, 1)

        land_a = warp(masks["land"])
        lake_a = warp(masks["lake"])
        arid_a = ndimage.gaussian_filter(warp(masks["arid"]) * land_a, o["arid_sigma"])

        # two-tone land (sage vs peach), then coral urban footprints, then lakes — all colourised
        # through the paper so the whole map stays one continuous watercolour
        land_col = (_colorize(land_d, palette.land, palette.paper) * (1 - arid_a[..., None])
                    + _colorize(land_d, palette.arid, palette.paper) * arid_a[..., None])
        img = img * (1 - land_a[..., None]) + land_col * land_a[..., None]
        if masks.get("urban") is not None and masks["urban"].any():
            urban_a = (warp(masks["urban"]) * land_a)[..., None]     # coral, only where it falls on land
            img = img * (1 - urban_a) + _colorize(land_d, palette.urban, palette.paper) * urban_a
        img = img * (1 - lake_a[..., None]) + _colorize(land_d, palette.lake, palette.paper) * lake_a[..., None]

        # pigment concentration on land: fine granulation everywhere + a soft in-hue pooled wet edge
        # just inside every shoreline. Multiplicative darkening keeps the hue (never a navy line).
        solid = np.clip(land_a + lake_a, 0, 1)
        dark = o["land_gran"] * (1 - sample_periodic(textures["land_grain"], ox, oy, P, P))
        gap = None
        wet = solid >= 0.5
        if wet.any() and (~wet).any():
            d_in = ndimage.distance_transform_edt(wet)
            rim = np.exp(-((d_in - o["rim_off"]) / o["rim_px"]) ** 2) * (d_in > 0)
            # brushy, BROKEN wet edge: strong on some stretches of coast, absent on others (real
            # pigment pools unevenly) — two decorrelated fields so it never traces a uniform outline
            rim *= np.clip(1.5 * (nx + 0.5) - 0.25, 0, 1) * (0.35 + 0.65 * (ny + 0.5))
            dark = dark + o["rim_strength"] * rim
            dist_coast = d_in + ndimage.distance_transform_edt(~wet)
            gap = np.clip(1 - dist_coast / o["gap_px"], 0, 1) * o["gap_strength"]
        ddark = (np.clip(dark, 0, 1) * solid)[..., None]        # gate to land -> ocean untouched
        img = img * (1 - ddark) + img * k * ddark

        # cream PAPER GAP over the top, exactly at the shoreline (Stamen leaves paper between colours)
        if gap is not None:
            g = gap[..., None]
            img = img * (1 - g) + paper_c * g

        # rivers: faint threads, only where they fall on land
        if masks["river"].any():
            rmask = (ndimage.binary_dilation(masks["river"], iterations=int(o["river_px"]))
                     & (land_a > 0.5))
            ra = rmask[..., None].astype(np.float32) * o["river_alpha"]
            img = img * (1 - ra) + _colorize(land_d, palette.river, palette.paper) * ra

        # white spatter speckle on land (the footer's paper flecks); never open ocean
        if o["speckle_alpha"] > 0:
            sp = (sample_periodic(textures["speckle"], ox, oy, P, P) > o["speckle_thresh"]).astype(np.float32)
            a = (sp * land_a * o["speckle_alpha"])[..., None]
            img = img * (1 - a) + np.array(palette.speckle, np.float32) * a

    img = img[pad:pad + size, pad:pad + size, :]
    out = np.empty((size, size, 4), dtype=np.uint8)
    out[..., :3] = img.astype(np.uint8)
    out[..., 3] = 255
    return out
