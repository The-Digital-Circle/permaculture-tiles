"""Derive tileable watercolour grain textures from the perma.earth footer illustration.

The renderer tints a flat palette colour by a [0,1] luma grain texture. What we want from the footer
is its *paper tooth / granulation* — the high-frequency character of real watercolour — NOT the wash
colour or the large-scale value gradient. So we crop a clean sage region, take luma, HIGH-PASS it
(subtract a heavy blur) to isolate the grain, normalise around 0.5, and make it seamlessly tileable.

    python scripts/make_swatches.py assets/reference/ILUSTRA-12-HOME.jpg assets/textures
"""
import os
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
from permatiles.textures import make_tileable

# Clean-ish watercolour patches in the 1024x291 footer (avoid figures/trees/animals).
CROPS = {
    "paper": (820, 80, 966, 152),   # inside the right sage-hill wash body (below its top edge)
}


def high_pass_grain(patch_rgb, out_size=512, blur_sigma=22.0):
    # Subtract only the LOW-frequency wash gradient (large blur), keeping both the fine paper tooth
    # AND the organic mid-scale watercolour granulation that gives a wash its life. A small blur
    # would strip that mid-scale and leave a flat, uniform digital noise.
    luma = np.asarray(patch_rgb.convert("L").resize((out_size, out_size), Image.LANCZOS), np.float64)
    grain = luma - ndimage.gaussian_filter(luma, blur_sigma)
    grain = (grain - grain.min()) / (np.ptp(grain) + 1e-9)     # -> [0,1]
    return make_tileable(grain)


def main():
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    im = Image.open(src).convert("RGB")
    for name, box in CROPS.items():
        g = high_pass_grain(im.crop(box))
        Image.fromarray((np.clip(g, 0, 1) * 255).astype("uint8"), mode="L").save(
            os.path.join(outdir, f"{name}.png"))
        print(f"wrote {outdir}/{name}.png  (grain contrast {np.abs(np.diff(g)).mean():.4f})")


if __name__ == "__main__":
    main()
