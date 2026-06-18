import os
from pmtiles.reader import Reader, MmapSource
from permatiles import pack

def _write_tree(root):
    # minimal z0-z1 tree: z0/0/0, z1/0/0, z1/1/1
    for z, x, y, payload in [(0, 0, 0, b"A"), (1, 0, 0, b"B"), (1, 1, 1, b"C")]:
        d = os.path.join(root, str(z), str(x))
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{y}.png"), "wb") as f:
            f.write(payload)

def test_plan_bands_groups_under_cap():
    sizes = {0: 1, 1: 1, 2: 10, 3: 10}
    bands = pack.plan_bands(sizes, cap=15)
    assert bands == [{"zmin": 0, "zmax": 2}, {"zmin": 3, "zmax": 3}]

def test_pack_band_roundtrip(tmp_path):
    tree = tmp_path / "tiles"
    _write_tree(str(tree))
    out = str(tmp_path / "band.pmtiles")
    pack.pack_band(str(tree), out, 0, 1, attribution="Natural Earth")
    with open(out, "rb") as f:
        r = Reader(MmapSource(f))
        assert r.get(0, 0, 0) == b"A"
        assert r.get(1, 1, 1) == b"C"

def test_write_manifest(tmp_path):
    out = str(tmp_path / "band.pmtiles")
    tree = tmp_path / "tiles"
    _write_tree(str(tree))
    pack.pack_band(str(tree), out, 0, 1, attribution="Natural Earth")
    m = pack.write_manifest(str(tmp_path), [{"file": "band.pmtiles", "zmin": 0, "zmax": 1}],
                            ocean_tile="ocean.png", tile_size=256, maxzoom=8,
                            attribution="Natural Earth")
    assert m["ocean_tile"] == "ocean.png"
    assert m["tiles"][0]["minzoom"] == 0 and m["tiles"][0]["maxzoom"] == 1
    assert len(m["tiles"][0]["sha256"]) == 64
    assert os.path.exists(tmp_path / "manifest.json")
