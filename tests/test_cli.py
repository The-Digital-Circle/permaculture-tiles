from permatiles import cli

def test_load_config(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('zoom_min = 0\nzoom_max = 2\nseed = 1\n[palette]\nland="#000000"\n')
    cfg = cli.load_config(str(p))
    assert cfg["zoom_max"] == 2
    assert cfg["palette"]["land"] == "#000000"

def test_build_textures_shapes():
    cfg = {"paper_tex_size": 256, "paper_cells": 8, "paper_octaves": 2,
           "ocean_cells": 4, "ocean_octaves": 2, "seed": 1}
    tex = cli.build_textures(cfg)
    assert tex["paper"].shape == (256, 256)
    assert tex["ocean"].shape == (256, 256)
