"""Render a block of tiles around a lon/lat into one stitched image for close-up taste review.

    python scripts/beauty.py <lon> <lat> <zoom> <cols> <rows> [out.png]

Uses cli.build_textures(cfg) + render_tile end to end, so what you see is exactly the pipeline output.
"""
import io
import sys
from PIL import Image
from permatiles import cli, data, tiles, geo
from permatiles.palette import Palette


def tile_xy(lon, lat, z):
    x3, y3 = geo.lonlat_to_3857(lon, lat)
    span = geo.tile_span_m(z)
    return int((x3 + geo.ORIGIN) / span), int((geo.ORIGIN - y3) / span)


def main():
    lon, lat, z = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
    cols = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    rows = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    out = sys.argv[6] if len(sys.argv) > 6 else "build/beauty.png"
    cfg = cli.load_config("config/render.toml")
    gd = data.load(cfg["data_dir"])
    tex = cli.build_textures(cfg)
    opts = cli.render_opts(cfg)
    pal = Palette.from_dict(cfg["palette"])
    size = cfg["tile_size"]
    cx, cy = tile_xy(lon, lat, z)
    x0, y0 = cx - cols // 2, cy - rows // 2
    sheet = Image.new("RGB", (cols * size, rows * size), tuple(pal.sea))
    for j in range(rows):
        for i in range(cols):
            png = tiles.render_tile(z, x0 + i, y0 + j, gd, tex, pal, cfg["pad"], size, opts=opts)
            if png:
                sheet.paste(Image.open(io.BytesIO(png)).convert("RGB"), (i * size, j * size))
    sheet.save(out)
    print(f"wrote {out} ({cols*size}x{rows*size})")


if __name__ == "__main__":
    main()
