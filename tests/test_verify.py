import numpy as np
import trimesh

from idea2print.params import PrinterLimits
from idea2print.verify import check_collisions, verify_part

L = PrinterLimits()


def box(*ext, at=(0, 0, 0)):
    m = trimesh.creation.box(extents=ext)
    m.apply_translation(at)
    return m


def by_name(checks):
    return {c.name: c for c in checks}


def test_closed_box_passes():
    checks = verify_part("cube", box(20, 20, 20), L)
    assert {c.name for c in checks} == {"watertight", "fits_bed", "min_wall", "overhang"}
    assert all(c.ok for c in checks), checks


def test_open_mesh_reports_not_crashes():
    m = box(20, 20, 20)
    m.update_faces(np.arange(len(m.faces)) >= 2)  # drop one face (2 triangles)
    c = by_name(verify_part("open", m, L))
    assert c["watertight"].ok is False
    assert {"fits_bed", "min_wall", "overhang"} <= set(c)


def test_too_big_fails_bed():
    assert by_name(verify_part("big", box(300, 10, 10), L))["fits_bed"].ok is False
    assert by_name(verify_part("fit", box(250, 10, 10), L))["fits_bed"].ok is True


def test_thin_wall_warns():
    hollow = box(30, 30, 30).difference(box(28.4, 28.4, 28.4), engine="manifold")
    c = by_name(verify_part("thin", hollow, L))["min_wall"]
    assert c.ok is False and c.level == "warning"


def test_overhang_warns():
    t = box(40, 40, 3, at=(0, 0, 21.5)).union(box(5, 5, 20, at=(0, 0, 10)), engine="manifold")
    c = by_name(verify_part("T", t, L))["overhang"]
    assert c.ok is False and c.level == "warning" and "mm" in c.detail


def test_collision_detected():
    out = check_collisions({"a": box(10, 10, 10), "b": box(10, 10, 10, at=(5, 0, 0))})
    assert len(out) == 1 and out[0].level == "error" and not out[0].ok
    assert "a" in out[0].detail and "b" in out[0].detail
    far = check_collisions({"a": box(10, 10, 10), "b": box(10, 10, 10, at=(20, 0, 0))})
    assert far == []


def test_collision_with_open_mesh_reports_not_crashes():
    m = box(10, 10, 10)
    m.update_faces(np.arange(len(m.faces)) >= 2)
    out = check_collisions({"open": m, "b": box(10, 10, 10)})
    assert len(out) == 1 and out[0].level == "error" and "open" in out[0].detail


def test_collision_contained_detected():
    out = check_collisions({"big": box(30, 30, 30), "small": box(5, 5, 5)})
    assert len(out) == 1 and "big" in out[0].detail and "small" in out[0].detail
