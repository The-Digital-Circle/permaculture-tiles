from permatiles import cli

def test_load_config(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('zoom_min = 0\nzoom_max = 2\nseed = 1\n[palette]\nland="#000000"\n')
    cfg = cli.load_config(str(p))
    assert cfg["zoom_max"] == 2
    assert cfg["palette"]["land"] == "#000000"

def test_build_textures_shapes():
    cfg = {"paper_tex_size": 256, "seed": 1}
    tex = cli.build_textures(cfg)
    assert tex["land_density"].shape == (256, 256)   # world-continuous field at paper_tex_size
    assert tex["sea_density"].shape == (256, 256)    # always the shared 256px tile

def _cfg():
    return {"seed": 7, "paper_tex_size": 256}

def test_build_textures_has_all_keys():
    tex = cli.build_textures(_cfg())
    assert set(tex) >= {"land_density", "sea_density", "disp_x", "disp_y", "speckle"}
    for k in ("land_density", "sea_density", "disp_x", "disp_y", "speckle"):
        assert tex[k].ndim == 2

def test_render_opts_pulls_render_block():
    cfg = {"render": {"gap_px": 2.4, "gap_strength": 0.8}}
    o = cli.render_opts(cfg)
    assert o["gap_px"] == 2.4 and o["gap_strength"] == 0.8
