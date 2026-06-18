import io
import numpy as np
from PIL import Image

def to_png8(rgba: np.ndarray, max_colors: int = 256) -> bytes:
    """RGBA uint8 (H,W,4) -> palette PNG bytes (<=max_colors). Watercolour quantises with no
    visible loss and roughly halves tile size."""
    rgb = Image.fromarray(rgba, mode="RGBA").convert("RGB")
    pal = rgb.quantize(colors=max_colors, method=Image.MEDIANCUT)
    buf = io.BytesIO()
    pal.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

def png_color_count(png_bytes: bytes) -> int:
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    colors = img.getcolors(maxcolors=1 << 24)
    return len(colors) if colors else (1 << 24)
