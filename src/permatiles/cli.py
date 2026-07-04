import argparse
import os
import tomllib
from . import data, tiles, pack
from .palette import Palette
from .textures import fractal_noise, brush_density, paper_grain
from .prune import shared_ocean_tile
from .quantise import to_png8

def load_config(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)

def build_textures(cfg: dict) -> dict:
    # 'sea_density' is ONE tile-periodic (256px) pigment field reused for every open-water tile, so
    # the ocean stays seamless and prunable; its stroke count and contrast are kept low so the
    # unavoidable repeat reads as a calm wash, not a pattern. 'land_density' is a large
    # world-continuous field, so land brushwork varies from tile to tile.
    seed = cfg["seed"]
    tsize = cfg["paper_tex_size"]
    return {
        "land_density": brush_density(tsize, seed + 40,
                                      base=cfg.get("land_base", 0.82),
                                      span=cfg.get("land_span", 0.16),
                                      tooth_amp=cfg.get("tooth_amp", 0.20),
                                      floor=cfg.get("land_floor", 0.52),
                                      bloom=cfg.get("land_bloom", 0.15),
                                      angle=(cfg.get("land_angle_lo", 0.2),
                                             cfg.get("land_angle_hi", 1.0))),
        "sea_density": brush_density(256, seed + 100,
                                     base=cfg.get("sea_base", 0.90),
                                     span=cfg.get("sea_span", 0.06),
                                     tooth_amp=cfg.get("sea_tooth_amp", 0.14),
                                     floor=cfg.get("sea_floor", 0.60),
                                     strokes=cfg.get("sea_strokes", 0.0),
                                     bloom=cfg.get("sea_bloom", 0.0)),
        "land_grain": paper_grain(tsize, seed + 200),   # CRISP per-pixel granulation (world-continuous)
        "sea_grain": paper_grain(256, seed + 210),      # CRISP, tile-periodic (seam-safe)
        "disp_x": fractal_noise(tsize, 8, 4, seed + 991),
        "disp_y": fractal_noise(tsize, 8, 4, seed + 613),
        "speckle": fractal_noise(256, 64, 1, seed + 300),
    }

def render_opts(cfg: dict) -> dict:
    return dict(cfg.get("render", {}))

def cmd_render(cfg: dict):
    gd = data.load(cfg["data_dir"])
    tex = build_textures(cfg)
    pal = Palette.from_dict(cfg["palette"])
    opts = render_opts(cfg)
    os.makedirs(cfg["out_dir"], exist_ok=True)
    workers = cfg.get("workers", 1)
    for z in range(cfg["zoom_min"], cfg["zoom_max"] + 1):
        if workers > 1 and z >= 4:
            print(tiles.render_zoom_parallel(z, gd, tex, pal, cfg["out_dir"], cfg["pad"],
                                             cfg["tile_size"], workers, opts=opts))
        else:
            print(tiles.render_zoom(z, gd, tex, pal, cfg["out_dir"], cfg["pad"], cfg["tile_size"],
                                    opts=opts))
    with open(os.path.join(cfg["out_dir"], "ocean.png"), "wb") as f:
        f.write(to_png8(shared_ocean_tile(pal, tex, cfg["pad"], cfg["tile_size"], opts=opts)))

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
