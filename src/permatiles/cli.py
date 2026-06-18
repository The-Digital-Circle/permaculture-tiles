import argparse
import os
import tomllib
from . import data, tiles, pack
from .palette import Palette
from .textures import fractal_noise
from .prune import shared_ocean_tile
from .quantise import to_png8

def load_config(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)

def build_textures(cfg: dict) -> dict:
    # Ocean is a single 256px tile reused everywhere, so its contrast is compressed toward the mean
    # (ocean_contrast < 1) to keep the unavoidable tile repetition too subtle to read as a pattern,
    # while staying perfectly seamless.
    ocean = fractal_noise(256, cfg["ocean_cells"], cfg["ocean_octaves"], cfg["seed"] + 100)
    k = cfg.get("ocean_contrast", 1.0)
    ocean = 0.5 + (ocean - 0.5) * k
    return {
        "paper": fractal_noise(cfg["paper_tex_size"], cfg["paper_cells"], cfg["paper_octaves"], cfg["seed"]),
        "ocean": ocean,
    }

def cmd_render(cfg: dict):
    gd = data.load(cfg["data_dir"])
    tex = build_textures(cfg)
    pal = Palette.from_dict(cfg["palette"])
    os.makedirs(cfg["out_dir"], exist_ok=True)
    for z in range(cfg["zoom_min"], cfg["zoom_max"] + 1):
        print(tiles.render_zoom(z, gd, tex, pal, cfg["out_dir"], cfg["pad"], cfg["tile_size"],
                                workers=cfg.get("workers", 1)))
    with open(os.path.join(cfg["out_dir"], "ocean.png"), "wb") as f:
        f.write(to_png8(shared_ocean_tile(pal, tex, cfg["pad"], cfg["tile_size"])))

def cmd_pack(cfg: dict):
    out = cfg["out_dir"]
    sizes = {z: pack.measure_zoom_bytes(out, z) for z in range(cfg["zoom_min"], cfg["zoom_max"] + 1)}
    sizes = {z: b for z, b in sizes.items() if b > 0}
    bands = pack.plan_bands(sizes, cfg["pmtiles_cap"])
    files = []
    for b in bands:
        name = f"tiles-z{b['zmin']}-{b['zmax']}.pmtiles"
        pack.pack_band(out, os.path.join(out, name), b["zmin"], b["zmax"], cfg["attribution"])
        files.append({"file": name, "zmin": b["zmin"], "zmax": b["zmax"]})
    m = pack.write_manifest(out, files, "ocean.png", cfg["tile_size"], cfg["zoom_max"], cfg["attribution"])
    print(f"packed {len(files)} band(s): {[f['file'] for f in files]}")
    return m

def main(argv=None):
    ap = argparse.ArgumentParser(prog="permatiles")
    ap.add_argument("command", choices=["download", "render", "pack", "all"])
    ap.add_argument("--config", default="config/render.toml")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    if args.command in ("download", "all"):
        data.download(cfg["data_dir"])
    if args.command in ("render", "all"):
        cmd_render(cfg)
    if args.command in ("pack", "all"):
        cmd_pack(cfg)
