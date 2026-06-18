import numpy as np
from .watercolour import render_padded

def is_pure_ocean(centre_masks) -> bool:
    """True when the tile's own 256px area contains no land, lake, or river — pure open water.
    Pass the *centre* (unpadded) masks so neighbouring land in the margin does not count."""
    return not (centre_masks["land"].any() or centre_masks["lake"].any()
                or centre_masks["river"].any())

def shared_ocean_tile(palette, textures, pad, size):
    """The one canonical open-water tile. Rendered from all-ocean masks at the tile-grid origin,
    so it is tile-periodic and seamless against itself and against coastal tiles' open water."""
    P = size + 2 * pad
    empty = np.zeros((P, P), dtype=bool)
    masks = {"land": empty, "lake": empty.copy(), "river": empty.copy()}
    return render_padded(masks, palette, textures, 0, 0, pad, size)
