"""Print N dominant colours of an image as hex — used to seed the palette from the
perma.earth footer watercolour. Usage: python scripts/extract_palette.py <image> [n]"""
import sys
from PIL import Image

def main():
    path = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    img = Image.open(path).convert("RGB").quantize(colors=n, method=Image.MEDIANCUT)
    pal = img.getpalette()[: n * 3]
    counts = sorted(img.getcolors(), reverse=True)  # (count, index)
    for _, idx in counts:
        r, g, b = pal[idx * 3: idx * 3 + 3]
        print(f"#{r:02x}{g:02x}{b:02x}")

if __name__ == "__main__":
    main()
