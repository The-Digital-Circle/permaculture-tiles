from permatiles import data

def test_layers_present():
    assert set(data.LAYERS) == {"land", "ocean", "lakes", "rivers"}

def test_geodata_holds_frames(synthetic_geodata):
    gd = synthetic_geodata
    assert not gd.land.empty
    assert not gd.ocean.empty
    assert gd.land.crs.to_epsg() == 3857

def test_merc_clip_box_bounds():
    b = data.merc_clip_box().bounds   # (minx,miny,maxx,maxy) in lon/lat
    assert b[0] == -180 and b[2] == 180
    assert abs(b[1]) > 85.0 and abs(b[1]) < 85.1
