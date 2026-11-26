import shutil
import subprocess
import sys
from pathlib import Path

import cadquery as cq

from idea2print.export import to_mesh
from idea2print.project import build_project
from idea2print.render import render_png

FIX = Path(__file__).parent / "fixtures"


def test_build_writes_everything(tmp_path):
    r = build_project(FIX / "caixa", tmp_path)
    assert r.ok is True
    for n in ("caixa.stl", "caixa.step", "3mf"):
        assert r.files[n].exists()
    for v in ("iso", "top"):
        assert (tmp_path / f"{v}.png").exists()
    assert r.report == tmp_path / "RELATORIO.md" and r.report.exists()


def test_report_lists_estimated(tmp_path):
    txt = build_project(FIX / "caixa", tmp_path).report.read_text()
    assert "Falta medir" in txt and "hole_diameter" in txt


def test_report_never_claims_ready(tmp_path):
    txt = build_project(FIX / "caixa", tmp_path).report.read_text().lower()
    assert "pronto para imprimir" not in txt and "validado" not in txt
    assert "teste físico pendente" in txt


def test_assembly_collision_fails_build(tmp_path):
    r = build_project(FIX / "colide", tmp_path)
    assert r.ok is False
    txt = r.report.read_text()
    assert "caixa" in txt and "content_bloco" in txt


def test_cli_exit_code(tmp_path):
    shutil.copytree(FIX / "caixa", tmp_path / "caixa")
    run = lambda *a: subprocess.run([sys.executable, "-m", "idea2print.cli", *a], capture_output=True, text=True)
    assert run("build", str(tmp_path / "caixa")).returncode == 0
    shutil.copytree(FIX / "colide", tmp_path / "colide")
    assert run("build", str(tmp_path / "colide")).returncode == 1
    stl = tmp_path / "caixa" / "out" / "caixa.stl"
    assert run("verify", str(stl)).returncode == 0
    m = run("measure", str(stl))
    assert m.returncode == 0 and '"objects"' in m.stdout


def test_broken_model_still_writes_report(tmp_path):
    proj = tmp_path / "p"
    shutil.copytree(FIX / "caixa", proj)
    (proj / "model.py").write_text("raise RuntimeError('boom')\n")
    r = build_project(proj)
    assert r.ok is False and r.report.exists()
    assert "boom" in r.report.read_text()
    assert r.report == proj / "out" / "RELATORIO.md"


def test_collision_exception_becomes_error(tmp_path, monkeypatch):
    def bad(meshes, tol_mm3=1.0):
        raise RuntimeError("manifold exploded")

    monkeypatch.setattr("idea2print.project.check_collisions", bad)
    r = build_project(FIX / "caixa", tmp_path)
    assert r.ok is False and "manifold exploded" in r.report.read_text()


def test_render_empty_raises(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        render_png({}, tmp_path / "x.png", "iso")


def test_render_creates_parent_dir(tmp_path):
    m = {"a": to_mesh(cq.Workplane("XY").box(5, 5, 5))}
    assert render_png(m, tmp_path / "sub" / "d.png", "iso").exists()


def test_build_cleans_stale_outputs(tmp_path):
    (tmp_path / "stale.stl").write_text("x")
    (tmp_path / "RELATORIO.md").write_text("old")
    (tmp_path / "notes.txt").write_text("keep")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.png").write_text("keep")
    build_project(FIX / "caixa", tmp_path)
    assert not (tmp_path / "stale.stl").exists()
    assert (tmp_path / "notes.txt").exists() and (tmp_path / "sub" / "a.png").exists()


def test_build_refuses_out_equal_project(tmp_path):
    import pytest

    proj = tmp_path / "p"
    shutil.copytree(FIX / "caixa", proj)
    for bad in (proj, tmp_path):
        with pytest.raises(ValueError):
            build_project(proj, bad)
    assert (proj / "model.py").exists()


def test_build_renders_open_views_when_lid(tmp_path):
    est = Path(__file__).parent.parent / "examples" / "estojo"
    r = build_project(est, tmp_path / "e")
    txt = r.report.read_text()
    for n in ("open_iso.png", "open_top.png"):
        assert (tmp_path / "e" / n).exists() and n in txt
    build_project(FIX / "caixa", tmp_path / "c")
    assert not (tmp_path / "c" / "open_iso.png").exists()


def test_load_model_future_annotations_dataclass_and_sibling(tmp_path):
    proj = tmp_path / "p"
    shutil.copytree(FIX / "caixa", proj)
    (proj / "helper.py").write_text("K = 1\n")
    (proj / "model.py").write_text(
        "from __future__ import annotations\n"
        "from dataclasses import dataclass\n"
        "import cadquery as cq\n"
        "from helper import K\n"
        "@dataclass\nclass S:\n    w: float\n"
        "def parts(p):\n    return {'caixa': cq.Workplane('XY').box(S(10).w * K, 10, 10)}\n"
    )
    r = build_project(proj)
    assert r.ok is True, [c.detail for c in r.checks if not c.ok]
    assert str(proj.resolve()) not in sys.path


def test_closed_views_hide_contents_only_with_lid(tmp_path, monkeypatch):
    import idea2print.project as proj_mod

    seen = []
    real = proj_mod.render_png
    monkeypatch.setattr(proj_mod, "render_png", lambda m, p, v: (seen.append((p.name, set(m))), real(m, p, v))[1])
    proj = tmp_path / "lid"
    shutil.copytree(FIX / "caixa", proj)
    (proj / "model.py").write_text(
        "import cadquery as cq\n"
        "def parts(p):\n    return {'base': cq.Workplane('XY').box(10, 10, 10)}\n"
        "def assembly(p):\n    return {'base': cq.Workplane('XY').box(10, 10, 10),"
        " 'lid': cq.Workplane('XY').box(10, 10, 2).translate((0, 0, 20)),"
        " 'content_x': cq.Workplane('XY').box(2, 2, 2).translate((30, 0, 0))}\n"
    )
    build_project(proj, tmp_path / "o1")
    got = dict(seen)
    assert "content_x" not in got["iso.png"] and "content_x" not in got["top.png"]
    assert "content_x" in got["open_iso.png"]
    seen.clear()
    proj2 = tmp_path / "nolid"
    shutil.copytree(proj, proj2)
    (proj2 / "model.py").write_text(
        (proj / "model.py").read_text().replace("'lid': cq.Workplane('XY').box(10, 10, 2).translate((0, 0, 20)),", "")
    )
    build_project(proj2, tmp_path / "o2")
    assert "content_x" in dict(seen)["iso.png"]


def test_build_dot_path_names_outputs_from_dir(tmp_path, monkeypatch):
    proj = tmp_path / "minhacaixa"
    shutil.copytree(FIX / "caixa", proj)
    monkeypatch.chdir(proj)
    r = build_project(Path("."))
    assert (proj / "out" / "minhacaixa.3mf").exists()
    assert "# Relatório — minhacaixa" in r.report.read_text()
