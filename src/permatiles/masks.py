import numpy as np
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from shapely.geometry import box

def _transform(bounds, width, height):
    minx, miny, maxx, maxy = bounds
    return from_bounds(minx, miny, maxx, maxy, width, height)

def rasterise(geoms, bounds, width, height) -> np.ndarray:
    """Boolean mask (height×width) of geoms within bounds (EPSG:3857)."""
    shapes = [(g, 1) for g in geoms if g is not None and not g.is_empty]
    if not shapes:
        return np.zeros((height, width), dtype=bool)
    arr = rasterize(
        shapes, out_shape=(height, width), transform=_transform(bounds, width, height),
        fill=0, default_value=1, all_touched=True, dtype="uint8",
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
