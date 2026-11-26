import numpy as np
import pytest
import trimesh

from idea2print.measure import measure_file


def _box(path, extents):
    trimesh.creation.box(extents=extents).export(path)
    return path


def test_cup_holder_inner_diameter(tmp_path):
    p = tmp_path / "holder.stl"
    trimesh.creation.annulus(r_min=49.5, r_max=53, height=20).export(p)
    report = measure_file(p)
    diameters = [d for s in report.objects[0].sections for d in s.inner_diameters]
    assert any(abs(d - 99.0) <= 0.5 for d in diameters)


def test_extents(tmp_path):
    report = measure_file(_box(tmp_path / "b.stl", (10, 20, 30)))
    assert report.objects[0].extents_mm == pytest.approx((10, 20, 30))
    sec = report.objects[0].sections[0]
    assert (sec.width, sec.depth) == pytest.approx((10, 20))


def test_scale_suspect_tiny(tmp_path):
    assert measure_file(_box(tmp_path / "s.stl", (2, 2, 2))).scale_suspect is True
    assert measure_file(_box(tmp_path / "n.stl", (50, 50, 50))).scale_suspect is False


def test_3mf_multiple_objects_with_transform(tmp_path):
    scene = trimesh.Scene()
    scene.add_geometry(trimesh.creation.box(extents=(10, 10, 10)), node_name="a", geom_name="a")
    t = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1])
    t[0, 3] = 100
    scene.add_geometry(trimesh.creation.box(extents=(10, 20, 30)), node_name="b", geom_name="b", transform=t)
    p = tmp_path / "s.3mf"
    scene.export(p)
    report = measure_file(p)
    assert len(report.objects) == 2
    assert sorted(o.extents_mm for o in report.objects) == [pytest.approx((10, 10, 10)), pytest.approx((20, 10, 30))]


def test_skips_non_mesh_items(tmp_path, monkeypatch):
    scene = trimesh.Scene([trimesh.creation.box(extents=(10, 10, 10)), trimesh.load_path(np.array([[0, 0, 0], [5, 5, 5]]))])
    monkeypatch.setattr(trimesh, "load", lambda *a, **k: scene)
    assert len(measure_file(tmp_path / "x.3mf").objects) == 1
