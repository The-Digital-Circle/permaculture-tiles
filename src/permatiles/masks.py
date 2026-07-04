import numpy as np
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from shapely.geometry import box

def _transform(bounds, width, height):
    minx, miny, maxx, maxy = bounds
    return from_bounds(minx, miny, maxx, maxy, width, height)

def rasterise(geoms, bounds, width, height, *, all_touched=False, min_area_px=0.0) -> np.ndarray:
    """Boolean mask (height×width) of geoms within bounds (EPSG:3857).

    all_touched=False (default) avoids the single-pixel diamond specks that all_touched=True
    scatters across open ocean at low zoom. min_area_px drops features whose projected area is
    below that many pixels, so sub-pixel islands/lakes vanish instead of flickering as noise."""
    minx, miny, maxx, maxy = bounds
    px_area = ((maxx - minx) / width) * ((maxy - miny) / height)
    shapes = []
    for g in geoms:
        if g is None or g.is_empty:
            continue
        if min_area_px > 0 and px_area > 0 and (g.area / px_area) < min_area_px:
            continue
        shapes.append((g, 1))
    if not shapes:
        return np.zeros((height, width), dtype=bool)
    arr = rasterize(
        shapes, out_shape=(height, width), transform=_transform(bounds, width, height),
        fill=0, default_value=1, all_touched=all_touched, dtype="uint8",
    )
    return arr.astype(bool)

def clip_geoms(gdf, bounds):
    """Geometries of a (3857) GeoDataFrame that intersect bounds.

    Uses the R-tree spatial index so the common case at high zoom — a tile with no nearby coastline,
    i.e. open ocean — returns an empty list in microseconds instead of scanning every polygon. This
    is what makes the ~65k z8 tiles (mostly pruned ocean) tractable."""
    minx, miny, maxx, maxy = bounds
    b = box(minx, miny, maxx, maxy)
    try:
        idx = gdf.sindex.query(b, predicate="intersects")
        return list(gdf.geometry.iloc[idx])
    except Exception:
        return list(gdf[gdf.intersects(b)].geometry)
