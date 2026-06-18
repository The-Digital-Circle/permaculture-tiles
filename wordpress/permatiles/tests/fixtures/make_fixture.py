"""Build a tiny root-only PMTiles fixture for the PHP reader unit tests.
Run once with the generator venv:  ../../.venv/bin/python make_fixture.py
Tiles: z0/0/0='AAA', z1/0/0='BBB', z1/1/1='CCC', z2/2/1='DDD'. Others absent."""
import os
from pmtiles.writer import Writer
from pmtiles.tile import TileType, Compression, zxy_to_tileid

TILES = {(0, 0, 0): b"AAA", (1, 0, 0): b"BBB", (1, 1, 1): b"CCC", (2, 2, 1): b"DDD"}
here = os.path.dirname(__file__)
with open(os.path.join(here, "mini.pmtiles"), "wb") as f:
    w = Writer(f)
    for (z, x, y), data in sorted(TILES.items(), key=lambda kv: zxy_to_tileid(*kv[0])):
        w.write_tile(zxy_to_tileid(z, x, y), data)
    w.finalize(
        {"tile_type": TileType.PNG, "tile_compression": Compression.NONE,
         "min_zoom": 0, "max_zoom": 2,
         "min_lon_e7": -1800000000, "max_lon_e7": 1800000000,
         "min_lat_e7": -850000000, "max_lat_e7": 850000000,
         "center_zoom": 0, "center_lon_e7": 0, "center_lat_e7": 0},
        {"attribution": "fixture"},
    )
print("wrote mini.pmtiles")
