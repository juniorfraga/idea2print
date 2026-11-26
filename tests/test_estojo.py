import importlib.util
import re
import shutil
from dataclasses import replace
from itertools import combinations
from pathlib import Path

import cadquery as cq

from idea2print.export import to_mesh
from idea2print.project import build_project
from idea2print.params import load_params
from idea2print.verify import check_collisions, verify_part

EST = Path(__file__).parent.parent / "examples" / "estojo"
spec = importlib.util.spec_from_file_location("estojo_model", EST / "model.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def _p(**over):
    p = load_params(EST / "params.toml")
    items = dict(p.items_)
    for k, v in over.items():
        items[k] = replace(items[k], value=v)
    return replace(p, items_=items)


def _interior(p):
    wall = p.v("wall_thickness")
    L, W, H = model.outer_size(p)
    return L - 2 * wall, W - 2 * wall, H - p.v("floor_thickness")


def test_slots_do_not_overlap():
    slots = model.layout(_p())
    assert set(slots) == {"vial_1", "vial_2", "sachets", "syringe_1", "syringe_2", "pack_1", "pack_2"}
    for (na, a), (nb, b) in combinations(slots.items(), 2):
        sep = a.x + a.w <= b.x or b.x + b.w <= a.x or a.y + a.d <= b.y or b.y + b.d <= a.y
        assert sep, f"{na} overlaps {nb}"


def test_slots_inside_base_interior():
    p = _p()
    Li, Wi, Hi = _interior(p)
    for n, s in model.layout(p).items():
        assert s.x >= 0 and s.y >= 0 and s.z >= 0, n
        assert s.x + s.w <= Li and s.y + s.d <= Wi and s.z + s.h <= Hi + 1e-9, n


def test_size_derived_from_params():
    L, W, H = model.outer_size(_p(syringe_extended_length=190.0))  # syringe longer than pack: it governs L
    assert abs(model.outer_size(_p(syringe_extended_length=210.0))[0] - (L + 20)) < 1e-9
    assert model.outer_size(_p(new_pack_length=300.0))[0] > L
    assert model.outer_size(_p(vial_height=48.1))[2] > H
    assert model.layout(_p(alcohol_sachet_count=12))["sachets"].h > model.layout(_p())["sachets"].h


def test_base_is_valid_solid():
    assert to_mesh(model.parts(_p())["base"]).is_watertight


def test_contents_fit_cavities():
    asm = {n: to_mesh(w) for n, w in model.assembly(_p()).items()}
    assert {"base", "content_vial_1", "content_vial_2", "content_syringe_1", "content_syringe_2",
            "content_pack_1", "content_pack_2", "content_sachets"} <= set(asm)
    assert check_collisions(asm) == []


def test_clips_only_on_barrel():
    p = _p()
    cap, barrel = p.v("syringe_cap_length"), p.v("syringe_barrel_length")
    s = model.layout(p)["syringe_1"]
    rs = model.clip_ranges(p, s)
    assert len(rs) == 2
    for a, b in rs:
        assert s.x + cap <= a and b <= s.x + cap + barrel
    moved = model.clip_ranges(_p(syringe_barrel_length=barrel + 40), s)
    assert moved[1][0] > rs[1][0] and moved[0][0] > rs[0][0]


def test_built_clips_only_on_barrel():
    import numpy as np

    p = _p()
    wall, floor = p.v("wall_thickness"), p.v("floor_thickness")
    mesh = to_mesh(model.parts(p)["base"])
    cap, barrel = p.v("syringe_cap_length"), p.v("syringe_barrel_length")
    r_in = p.v("syringe_body_diameter") / 2 + p.v("syringe_clip_clearance")
    for n in ("syringe_1", "syringe_2"):
        s = model.layout(p)[n]
        xs = np.arange(s.x + 0.25, s.x + s.w, 0.5)
        pts = np.array([[wall + x, wall + s.y + s.d / 2 + r_in + 0.5, floor + s.h / 2] for x in xs])
        solid = xs[mesh.contains(pts)]
        assert len(solid) > 0
        assert solid.min() >= s.x + cap - 1e-6 and solid.max() <= s.x + cap + barrel + 1e-6
        for a, b in model.clip_ranges(p, s):
            assert ((solid >= a) & (solid <= b)).any()


# ---- lid, hinge, latch (Task 7) ----
import numpy as np
import trimesh


def _meshes(p, lid_angle=0.0):
    asm = model.assembly(p)
    out = {n: to_mesh(w) for n, w in asm.items()}
    if lid_angle:
        out["lid"] = to_mesh(model.lid_at(p, lid_angle))
    return out


def _outline_area(mesh, z, box):
    from shapely.geometry import Polygon, box as sbox

    sec = mesh.section(plane_origin=(0, 0, z), plane_normal=(0, 0, 1))
    planar, T = sec.to_2D()
    full = None
    for poly in planar.polygons_full:
        poly = Polygon(poly.exterior)
        pts = np.c_[np.array(poly.exterior.coords), np.zeros(len(poly.exterior.coords)), np.ones(len(poly.exterior.coords))]
        w = (T @ pts.T).T[:, :2]
        q = Polygon(w).buffer(0)
        full = q if full is None else full.union(q)
    return full.intersection(sbox(*box)).area


def test_closed_no_collision():
    assert check_collisions(_meshes(_p())) == []


def test_lid_has_no_internal_features():
    p = _p()
    L, W, H = model.outer_size(p)
    wall, r = p.v("wall_thickness"), p.v("corner_radius")
    k = model.LID_CAVITY
    lid = to_mesh(model.assembly(p)["lid"])
    e = 0.01  # inset so coplanar contact with the skirt's inner face is not counted
    region = to_mesh(model._rbox(L - 2 * wall - 2 * e, W - 2 * wall - 2 * e, H + k - e, max(r - wall, 0.0)).translate((wall + e, wall + e, 0)))
    inter = trimesh.boolean.intersection([lid, region], engine="manifold")
    vol = inter.volume if len(inter.faces) else 0.0
    assert vol < 1.0, vol


def test_same_outline():
    # hinge barrels (y > W) and latch tab (y < 0) lie outside the box (0,0,L,W): clipping to it excludes them
    p = _p()
    L, W, H = model.outer_size(p)
    box = (0, 0, L, W)
    a_base = _outline_area(to_mesh(model.assembly(p)["base"]), H / 2, box)
    a_lid = _outline_area(to_mesh(model.assembly(p)["lid"]), H + model.LID_CAVITY + model.LID_PLATE / 2, box)
    assert abs(a_lid - a_base) / a_base < 0.005, (a_lid, a_base)
    assert a_base > 0.95 * L * W


def test_lid_print_orientation_flat_on_bed():
    lid = to_mesh(model.parts(_p())["lid"])
    assert lid.is_watertight and abs(lid.bounds[0][2]) < 1e-6
    L, W, H = model.outer_size(_p())
    assert lid.extents[2] > model.LID_PLATE + model.LID_CAVITY  # tab rises above the plate in print pose


def _hole_center(mesh, x):
    sec = mesh.section(plane_origin=(x, 0, 0), plane_normal=(1, 0, 0))
    planar, T = sec.to_2D()
    holes = []
    for poly in planar.polygons_full:
        for ring in poly.interiors:
            c = np.array(ring.centroid.coords[0])
            holes.append((T @ np.array([c[0], c[1], 0, 1]))[:3])
    assert holes, "no pin hole found"
    return min(holes, key=lambda h: np.hypot(h[1] - model.hinge_axis(_p())[0][1], h[2] - model.hinge_axis(_p())[0][2]))


def test_hinge_coaxial():
    p = _p()
    ax, d = model.hinge_axis(p)
    asm = _meshes(p)
    segs = model.hinge_segments(p)
    owners = {o for o, _, _ in segs}
    assert owners == {"base", "lid"}
    for owner, x0, x1 in segs:
        h = _hole_center(asm[owner], (x0 + x1) / 2)
        assert abs(h[1] - ax[1]) < 0.05 and abs(h[2] - ax[2]) < 0.05, (owner, h, ax)


def test_hinge_swing_clear():
    p = _p()
    for ang in (0, 45, 90, 110):
        asm = _meshes(p, ang)
        asm = {n: m for n, m in asm.items() if n in ("base", "lid")}
        assert check_collisions(asm) == [], ang
    # swing really moves the lid up
    assert to_mesh(model.lid_at(p, 90)).bounds[1][2] > to_mesh(model.lid_at(p, 0)).bounds[1][2] + 50


def test_base_walls_present():
    p = _p()
    L, W, H = model.outer_size(p)
    wall, floor, g = p.v("wall_thickness"), p.v("floor_thickness"), p.v("item_gap")
    mesh = to_mesh(model.parts(p)["base"])
    z = H / 2
    walls = [(wall / 2, W / 2, z), (L - wall / 2, W / 2, z), (L / 4, wall / 2, z), (L / 4, W - wall / 2, z)]
    assert mesh.contains(walls).all()
    assert not mesh.contains([(wall + g / 2, wall + g / 2, floor + 10)]).any()  # empty gap in the cavity


def test_lid_clearance_above_contents():
    p = _p()
    L, W, H = model.outer_size(p)
    asm = model.assembly(p)
    top = max(to_mesh(w).bounds[1][2] for n, w in asm.items() if n.startswith("content_"))
    lid = to_mesh(asm["lid"])
    zs = np.arange(H - 1, H + 8, 0.02)
    solid = lid.contains([(L / 2, W / 2, z) for z in zs])
    assert solid.any()
    assert zs[solid][0] - top >= 1.0 - 0.02  # underside of the plate measured from the mesh (0.02 scan step)


def test_coupons_small():
    cps = model.coupons(_p())
    assert set(cps) == {"clip", "hinge", "latch", "vial_ring"}
    for n, c in cps.items():
        bb = to_mesh(c).bounds
        ext = bb[1] - bb[0]
        assert (ext <= (40, 40, 25)).all() and ext.min() > 1, (n, ext)
        assert to_mesh(c).is_watertight, n


def test_full_build_ok(tmp_path):
    r = build_project(EST, tmp_path / "out")
    assert r.ok, [c for c in r.checks if c.level == "error" and not c.ok]
    assert "3mf" in r.files
    names = {k for k in r.files if k.endswith(".stl")}
    assert {"base.stl", "lid.stl"} <= names
    assert {f"coupon_{n}.stl" for n in ("clip", "hinge", "latch", "vial_ring")} <= names
    ext = [b - a for a, b in [to_mesh(w).bounds for w in model.parts(_p()).values()]]
    assert all((e <= 256).all() for e in ext)


def test_extreme_param_reports_bed_failure(tmp_path):
    proj = tmp_path / "estojo"
    shutil.copytree(EST, proj, ignore=shutil.ignore_patterns("out"))
    toml = (proj / "params.toml").read_text()
    head, tail = toml.split("[medidas.syringe_extended_length]")
    tail, n = re.subn(r"valor = [0-9.]+", "valor = 300", tail, count=1)
    assert n == 1  # the substitution must actually happen, whatever the current value
    (proj / "params.toml").write_text(head + "[medidas.syringe_extended_length]" + tail)
    r = build_project(proj)
    assert r.ok is False
    assert any(c.name == "fits_bed" and c.level == "error" and not c.ok for c in r.checks)
    assert (proj / "out" / "RELATORIO.md").exists()


def test_hinge_coupon_gap_is_real_clearance():
    p = _p()
    hinge = model.coupons(p)["hinge"]
    a, b = sorted((to_mesh(wp) for wp in [cq.Workplane("XY").newObject([s]) for s in hinge.solids().vals()]), key=lambda m: m.bounds[0][0])
    assert abs(b.bounds[0][0] - a.bounds[1][0] - p.v("hinge_clearance")) <= 0.05
    assert not [c for c in verify_part("hinge", to_mesh(hinge), p.printer) if c.level == "error" and not c.ok]


def test_report_has_hinge_pin_note(tmp_path):
    import re

    txt = build_project(EST, tmp_path).report.read_text()
    assert "## Montagem" in txt
    m = re.search(r"filamento de 1\.75 mm.*?com ([\d.]+) mm de comprimento", txt)
    assert m and 20 < float(m.group(1)) < 80
