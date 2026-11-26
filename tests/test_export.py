import cadquery as cq
import pytest
import trimesh

from idea2print.export import export_parts, to_mesh
from idea2print.render import render_png


def _parts():
    return {
        "a": cq.Workplane("XY").box(10, 10, 10),
        "b": cq.Workplane("XY").circle(5).extrude(10),
    }


def test_to_mesh_box_watertight():
    m = to_mesh(cq.Workplane("XY").box(10, 10, 10))
    assert m.is_watertight
    assert m.volume == pytest.approx(1000, rel=0.01)


def test_stl_step_3mf_written(tmp_path):
    out = export_parts(_parts(), tmp_path, "proj")
    for name in ("a", "b"):
        assert (tmp_path / f"{name}.stl").exists()
        assert (tmp_path / f"{name}.step").exists()
    assert out["3mf"] == tmp_path / "proj.3mf" and out["3mf"].exists()


def test_3mf_roundtrip_volume(tmp_path):
    out = export_parts(_parts(), tmp_path, "proj")
    scene = trimesh.load(out["3mf"])
    assert len(scene.geometry) == 2
    assert set(scene.geometry) == {"a", "b"}
    for name in ("a", "b"):
        stl = trimesh.load(tmp_path / f"{name}.stl")
        assert scene.geometry[name].volume == pytest.approx(stl.volume, rel=0.01)


def test_render_png_nonempty(tmp_path):
    meshes = {k: to_mesh(v) for k, v in _parts().items()}
    for view in ("iso", "top", "front"):
        p = render_png(meshes, tmp_path / f"{view}.png", view)
        assert p.stat().st_size > 10_000


def test_multi_solid_part_exported_whole():
    wp = cq.Workplane("XY").add(cq.Workplane("XY").box(10, 10, 10).val()).add(
        cq.Workplane("XY").center(30, 0).box(10, 10, 10).val()
    )
    assert len(wp.vals()) == 2
    assert to_mesh(wp).volume == pytest.approx(2000, rel=0.01)


def test_3mf_parts_laid_out_without_overlap(tmp_path):
    from itertools import combinations

    out = export_parts(_parts(), tmp_path, "proj")
    scene = trimesh.load(out["3mf"])
    geoms = list(scene.geometry)
    boxes = {}
    for n in geoms:
        m = scene.geometry[n].copy()
        for nd in scene.graph.nodes_geometry:
            T, g = scene.graph[nd]
            if g == n:
                m.apply_transform(T)
        boxes[n] = m.bounds
    for lo_hi in boxes.values():
        assert lo_hi[0][2] == pytest.approx(0, abs=1e-6)
    for a, b in combinations(boxes.values(), 2):
        assert any(a[1][i] <= b[0][i] or b[1][i] <= a[0][i] for i in range(3))
