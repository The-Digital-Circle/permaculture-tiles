from dataclasses import dataclass

def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def darker(color, factor: float = 0.80, sat: float = 1.10):
    """A deeper, slightly more saturated shade of the SAME hue — the watercolour dry-edge tone.
    Pulls the wash's own colour down in value and up a touch in saturation; introduces no new hue."""
    m = sum(color) / 3.0
    out = []
    for c in color:
        v = m + (c - m) * sat        # saturation nudge around the pixel mean
        out.append(int(max(0, min(255, round(v * factor)))))
    return tuple(out)

@dataclass(frozen=True)
class Palette:
    land: tuple
    arid: tuple
    sea: tuple
    lake: tuple
    river: tuple
    paper: tuple
    speckle: tuple = (255, 255, 255)
    accent: tuple = (224, 122, 95)

    @staticmethod
    def from_dict(d: dict) -> "Palette":
        g = lambda k, default: hex_to_rgb(d[k]) if k in d else default
        return Palette(
            land=hex_to_rgb(d["land"]),
            arid=g("arid", (233, 195, 156)),
            sea=hex_to_rgb(d["sea"]),
            lake=hex_to_rgb(d["lake"]),
            river=hex_to_rgb(d["river"]),
            paper=hex_to_rgb(d["paper"]),
            speckle=g("speckle", (255, 255, 255)),
            accent=g("accent", (224, 122, 95)),
        )
