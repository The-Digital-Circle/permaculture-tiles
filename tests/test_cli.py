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

def _cfg():
    return {"seed": 7, "paper_tex_size": 512, "paper_cells": 16, "paper_octaves": 4,
            "ocean_cells": 8, "ocean_octaves": 3, "ocean_contrast": 0.4, "textures": {}}

def test_build_textures_has_all_keys():
    tex = cli.build_textures(_cfg())
    assert set(tex) >= {"paper", "ocean", "granulation", "disp_x", "disp_y", "speckle"}
    for k in ("granulation", "disp_x", "disp_y", "speckle"):
        assert tex[k].ndim == 2

def test_render_opts_pulls_render_block():
    cfg = {"render": {"edge_px": 5, "edge_strength": 0.6}}
    o = cli.render_opts(cfg)
    assert o["edge_px"] == 5 and o["edge_strength"] == 0.6
