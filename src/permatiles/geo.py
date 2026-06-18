import math

TILE = 256
R = 6378137.0
ORIGIN = math.pi * R          # 20037508.342789244
WORLD = 2 * ORIGIN

def num_tiles(z: int) -> int:
    return 1 << z

def tile_span_m(z: int) -> float:
    """Side length of one tile in EPSG:3857 metres at zoom z."""
    return WORLD / (1 << z)

def tile_bounds_3857(z: int, x: int, y: int):
    """(minx, miny, maxx, maxy) in EPSG:3857 for XYZ tile (y increases southward)."""
    span = tile_span_m(z)
    minx = -ORIGIN + x * span
    maxx = minx + span
    maxy = ORIGIN - y * span
    miny = maxy - span
    return (minx, miny, maxx, maxy)

def lonlat_to_3857(lon: float, lat: float):
    x = math.radians(lon) * R
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R
    return (x, y)

def world_px_origin(z: int, x: int, y: int):
    """Global pixel coords of the tile's top-left at zoom z (for world-coordinate sampling)."""
    return (x * TILE, y * TILE)
