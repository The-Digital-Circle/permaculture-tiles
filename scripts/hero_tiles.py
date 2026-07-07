"""Render a handful of stress-test tiles into one labelled sheet for taste iteration.

    python scripts/hero_tiles.py [zoom]

Regions stress the look: ragged coast, archipelago, desert-sea, lakes, open ocean, coast+ocean.
Renders FROM cli.build_textures(cfg) (not a hand-built fixture), so it doubles as the end-to-end
build_textures -> render_tile integration smoke.
"""
import io
import math
import sys
from PIL import Image, ImageDraw
from permatiles import cli, data, tiles, geo
from permatiles.palette import Palette

REGIONS = [
    ("Norway fjords",   10.5, 61.0),   # ragged sage coast
    ("Indonesia",      117.0, -2.0),    # archipelago, many small coasts
    ("Libya coast",     20.0, 31.5),    # peach desert meets teal sea
    ("Great Lakes",    -83.0, 44.0),    # inland lakes
    ("Open Pacific",  -140.0, -10.0),   # open ocean (shared tile)
    ("Sahel edge",       6.0, 15.5),    # peach desert -> sage vegetation transition
    ("Central Australia", 133.0, -25.0),   # interior must read as arid, not blotches
]


def tile_xy(lon, lat, z):
    x3, y3 = geo.lonlat_to_3857(lon, lat)
    span = geo.tile_span_m(z)
    x = int((x3 + geo.ORIGIN) / span)
    y = int((geo.ORIGIN - y3) / span)
    return x, y


def main():
    z = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    cfg = cli.load_config("config/render.toml")
    gd = data.load(cfg["data_dir"])
    tex = cli.build_textures(cfg)
    opts = cli.render_opts(cfg)
    pal = Palette.from_dict(cfg["palette"])
    size = cfg["tile_size"]
    cols = 3
    rows = math.ceil(len(REGIONS) / cols)
    lab = 20
    sheet = Image.new("RGB", (cols * size, rows * (size + lab)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (name, lon, lat) in enumerate(REGIONS):
        x, y = tile_xy(lon, lat, z)
        png = tiles.render_tile(z, x, y, gd, tex, pal, cfg["pad"], size, opts=opts)
        img = (Image.open(io.BytesIO(png)).convert("RGB") if png
               else Image.new("RGB", (size, size), tuple(pal.sea)))
        col, row = i % cols, i // cols
        ox, oy = col * size, row * (size + lab)
        sheet.paste(img, (ox, oy + lab))
        draw.text((ox + 4, oy + 4), f"{name} z{z} {x}/{y}" + (" [ocean]" if png is None else ""),
                  fill="black")
    out = sys.argv[2] if len(sys.argv) > 2 else "build/hero.png"
    sheet.save(out)
    print(f"wrote {out}  ({cols*size}x{rows*(size+lab)})")


if __name__ == "__main__":
    main()
