import os
from . import geo
from .masks import rasterise, clip_geoms
from .watercolour import render_padded
from .prune import is_pure_ocean
from .quantise import to_png8

def _padded_bounds(z, x, y, pad, size):
    minx, miny, maxx, maxy = geo.tile_bounds_3857(z, x, y)
    m = (maxx - minx) * (pad / size)
    return (minx - m, miny - m, maxx + m, maxy + m)

def render_tile(z, x, y, geodata, textures, palette, pad, size):
    """Render one tile to PNG8 bytes, or None if it is pure open ocean (pruned)."""
    P = size + 2 * pad
    pb = _padded_bounds(z, x, y, pad, size)
    masks = {
        "land":  rasterise(clip_geoms(geodata.land, pb),  pb, P, P),
        "lake":  rasterise(clip_geoms(geodata.lakes, pb), pb, P, P),
        "river": rasterise(clip_geoms(geodata.rivers, pb), pb, P, P),
    }
    centre = {k: v[pad:pad + size, pad:pad + size] for k, v in masks.items()}
    if is_pure_ocean(centre):
        return None
    gx0, gy0 = geo.world_px_origin(z, x, y)
    return to_png8(render_padded(masks, palette, textures, gx0, gy0, pad, size))

def render_zoom(z, geodata, textures, palette, out_dir, pad, size, workers=1, bbox_tiles=None):
    """Render every tile at zoom z, write the PNG tree under out_dir/z/x/y.png, skip pruned tiles.
    bbox_tiles, if given, restricts to (x0,y0,x1,y1) inclusive."""
    n = geo.num_tiles(z)
    x0, y0, x1, y1 = bbox_tiles or (0, 0, n - 1, n - 1)
    written = pruned = 0
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            png = render_tile(z, x, y, geodata, textures, palette, pad, size)
            if png is None:
                pruned += 1
                continue
            d = os.path.join(out_dir, str(z), str(x))
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, f"{y}.png"), "wb") as f:
                f.write(png)
            written += 1
    return {"zoom": z, "written": written, "pruned": pruned}
