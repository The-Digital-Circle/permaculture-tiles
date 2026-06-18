import os
import json
import hashlib
from pmtiles.writer import Writer
from pmtiles.tile import TileType, Compression, zxy_to_tileid

MERC_LAT_E7 = 850511287
LON_E7 = 1800000000

def measure_zoom_bytes(tree_dir, z) -> int:
    total = 0
    zdir = os.path.join(tree_dir, str(z))
    if not os.path.isdir(zdir):
        return 0
    for root, _, files in os.walk(zdir):
        for fn in files:
            total += os.path.getsize(os.path.join(root, fn))
    return total

def plan_bands(sizes: dict, cap: int):
    """Group contiguous zoom levels into bands each <= cap bytes (best effort)."""
    bands, cur, cur_bytes = [], [], 0
    for z in sorted(sizes):
        b = sizes[z]
        if cur and cur_bytes + b > cap:
            bands.append({"zmin": cur[0], "zmax": cur[-1]})
            cur, cur_bytes = [], 0
        cur.append(z)
        cur_bytes += b
    if cur:
        bands.append({"zmin": cur[0], "zmax": cur[-1]})
    return bands

def _entries(tree_dir, zmin, zmax):
    out = []
    for z in range(zmin, zmax + 1):
        zdir = os.path.join(tree_dir, str(z))
        if not os.path.isdir(zdir):
            continue
        for xs in os.listdir(zdir):
            xdir = os.path.join(zdir, xs)
            for ys in os.listdir(xdir):
                if not ys.endswith(".png"):
                    continue
                x, y = int(xs), int(ys[:-4])
                out.append((zxy_to_tileid(z, x, y), z, os.path.join(xdir, ys)))
    out.sort()                       # pmtiles requires ascending tile id
    return out

def pack_band(tree_dir, out_path, zmin, zmax, attribution):
    entries = _entries(tree_dir, zmin, zmax)
    zs = [z for _, z, _ in entries] or [zmin]
    with open(out_path, "wb") as f:
        w = Writer(f)
        for tid, _z, path in entries:
            with open(path, "rb") as tf:
                w.write_tile(tid, tf.read())
        w.finalize(
            {
                "tile_type": TileType.PNG,
                "tile_compression": Compression.NONE,
                "min_zoom": min(zs),
                "max_zoom": max(zs),
                "min_lon_e7": -LON_E7, "max_lon_e7": LON_E7,
                "min_lat_e7": -MERC_LAT_E7, "max_lat_e7": MERC_LAT_E7,
                "center_zoom": min(zs), "center_lon_e7": 0, "center_lat_e7": 0,
            },
            {"attribution": attribution},
        )
    return out_path

def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def write_manifest(out_dir, files, ocean_tile, tile_size, maxzoom, attribution):
    tiles = []
    for fdesc in files:
        path = os.path.join(out_dir, fdesc["file"])
        tiles.append({
            "file": fdesc["file"],
            "minzoom": fdesc["zmin"],
            "maxzoom": fdesc["zmax"],
            "xrange": fdesc.get("xrange"),
            "bounds": [-180, -85.0511, 180, 85.0511],
            "sha256": _sha256(path),
        })
    manifest = {"tiles": tiles, "ocean_tile": ocean_tile, "tile_size": tile_size,
                "maxzoom": maxzoom, "attribution": attribution}
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest
