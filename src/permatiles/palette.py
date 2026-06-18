from dataclasses import dataclass

def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

@dataclass(frozen=True)
class Palette:
    land: tuple
    ocean: tuple
    lake: tuple
    river: tuple
    wet_edge: tuple
    paper: tuple

    @staticmethod
    def from_dict(d: dict) -> "Palette":
        return Palette(
            land=hex_to_rgb(d["land"]),
            ocean=hex_to_rgb(d["ocean"]),
            lake=hex_to_rgb(d["lake"]),
            river=hex_to_rgb(d["river"]),
            wet_edge=hex_to_rgb(d["wet_edge"]),
            paper=hex_to_rgb(d["paper"]),
        )
