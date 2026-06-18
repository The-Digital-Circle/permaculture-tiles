"""Stitch a zoom's PNG tiles (with ocean.png for pruned positions) into one big PNG for review.
Usage: python scripts/contact_sheet.py build/tiles <zoom> out.png"""
import os
import sys
from PIL import Image

def main():
    tree, z, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    n = 1 << z
    ocean = Image.open(os.path.join(tree, "ocean.png")).convert("RGB")
    size = ocean.size[0]
    sheet = Image.new("RGB", (n * size, n * size))
    for x in range(n):
        for y in range(n):
            p = os.path.join(tree, str(z), str(x), f"{y}.png")
            img = Image.open(p).convert("RGB") if os.path.exists(p) else ocean
            sheet.paste(img, (x * size, y * size))
    sheet.save(out)
    print(f"wrote {out} ({n*size}x{n*size})")

if __name__ == "__main__":
    main()
