import os
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from . import geo
from .masks import rasterise, clip_geoms
from .watercolour import render_padded
from .prune import is_pure_ocean
from .quantise import encode, ext_for

def _padded_bounds(z, x, y, pad, size):
    minx, miny, maxx, maxy = geo.tile_bounds_3857(z, x, y)
    m = (maxx - minx) * (pad / size)
    return (minx - m, miny - m, maxx + m, maxy + m)

_DEFAULT_MASK_OPTS = {"lake_min_zoom": 4, "river_min_zoom": 6, "urban_min_zoom": 5,
                      "draw_rivers": False, "draw_urban": False,
                      "min_area_px": 3.0, "coast_all_touched": True}

def _encoding(opts):
    """(format, quality, ext) for a render. Defaults to png: callers passing no opts keep v0.2.5
    behaviour byte-for-byte."""
    o = opts or {}
    fmt = o.get("tile_format", "png")
    return fmt, int(o.get("webp_quality", 90)), ext_for(fmt)

def build_masks(z, x, y, geodata, pad, size, opts=None):
    """Build the {land, arid, lake, river, urban} boolean mask dict (P,P) for one tile, P = size+2*pad.

    Lakes are zeroed below opts['lake_min_zoom'] (default 4), rivers below opts['river_min_zoom']
    (default 6) and urban footprints below opts['urban_min_zoom'] (default 5), so inland detail stops
    cluttering low-zoom tiles. Rivers and urban areas are additionally off entirely unless
    opts['draw_rivers'] / opts['draw_urban'] are set. Sub-pixel features are dropped via min_area_px
    (does not apply to line-geometry rivers, which have zero area)."""
    o = {**_DEFAULT_MASK_OPTS, **(opts or {})}
    P = size + 2 * pad
    pb = _padded_bounds(z, x, y, pad, size)
    def m(gdf, all_touched=False):
        return rasterise(clip_geoms(gdf, pb), pb, P, P,
                         all_touched=all_touched, min_area_px=o["min_area_px"])
    zeros = np.zeros((P, P), dtype=bool)
    land = m(geodata.land, all_touched=o["coast_all_touched"])
    arid = m(geodata.arid) if getattr(geodata, "arid", None) is not None else zeros.copy()
    lake = m(geodata.lakes) if z >= o["lake_min_zoom"] else zeros.copy()
    # River centerlines are thin threads with no width and look bad; off by default. Wide, lake-like
    # waters (Thames/Severn/St Lawrence estuaries) already render as sea through the coastline.
    river = rasterise(clip_geoms(geodata.rivers, pb), pb, P, P, all_touched=False, min_area_px=0.0) \
            if o["draw_rivers"] and z >= o["river_min_zoom"] else zeros.copy()
    # Built-up areas painted coral read as an unexplained orange speckle: a basemap has no legend, so
    # viewers asked what they meant. Off by default; flip draw_urban to bring the cities back.
    urban = m(geodata.urban) if o["draw_urban"] and getattr(geodata, "urban", None) is not None \
            and z >= o["urban_min_zoom"] else zeros.copy()
    return {"land": land, "arid": arid, "lake": lake, "river": river, "urban": urban}

def render_tile(z, x, y, geodata, textures, palette, pad, size, opts=None):
    """Render one tile to encoded bytes in opts['tile_format'] (default png), or None if it is pure
    open ocean (pruned)."""
    masks = build_masks(z, x, y, geodata, pad, size, opts)
    centre = {k: v[pad:pad + size, pad:pad + size] for k, v in masks.items()}
    if is_pure_ocean(centre):
        return None
    fmt, quality, _ = _encoding(opts)
    gx0, gy0 = geo.world_px_origin(z, x, y)
    return encode(render_padded(masks, palette, textures, gx0, gy0, pad, size, opts=opts),
                  fmt, quality)

def render_zoom(z, geodata, textures, palette, out_dir, pad, size, workers=1, bbox_tiles=None,
                opts=None):
    """Render every tile at zoom z, write the PNG tree under out_dir/z/x/y.png, skip pruned tiles.
    bbox_tiles, if given, restricts to (x0,y0,x1,y1) inclusive."""
    n = geo.num_tiles(z)
    x0, y0, x1, y1 = bbox_tiles or (0, 0, n - 1, n - 1)
    written = pruned = 0
    ext = _encoding(opts)[2]
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            data = render_tile(z, x, y, geodata, textures, palette, pad, size, opts)
            if data is None:
                pruned += 1
                continue
            d = os.path.join(out_dir, str(z), str(x))
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, f"{y}.{ext}"), "wb") as f:
                f.write(data)
            written += 1
    return {"zoom": z, "written": written, "pruned": pruned}

# --- parallel rendering (process pool); workers share geodata/textures via the initializer ---
_CTX = {}

def _init_worker(geodata, textures, palette, pad, size, opts=None):
    _CTX.update(geodata=geodata, textures=textures, palette=palette, pad=pad, size=size, opts=opts)

def _render_one(args):
    z, x, y = args
    data = render_tile(z, x, y, _CTX["geodata"], _CTX["textures"], _CTX["palette"],
                       _CTX["pad"], _CTX["size"], _CTX.get("opts"))
    return (z, x, y, data)

def render_zoom_parallel(z, geodata, textures, palette, out_dir, pad, size, workers, opts=None):
    """Same as render_zoom but fans tiles across a process pool. Used for the big zooms (z>=4)."""
    n = geo.num_tiles(z)
    jobs = [(z, x, y) for x in range(n) for y in range(n)]
    written = pruned = 0
    ext = _encoding(opts)[2]
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker,
                             initargs=(geodata, textures, palette, pad, size, opts)) as ex:
        for z_, x, y, data in ex.map(_render_one, jobs, chunksize=16):
            if data is None:
                pruned += 1
                continue
            d = os.path.join(out_dir, str(z_), str(x))
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, f"{y}.{ext}"), "wb") as f:
                f.write(data)
            written += 1
    return {"zoom": z, "written": written, "pruned": pruned}
