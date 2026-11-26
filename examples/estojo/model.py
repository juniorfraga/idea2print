"""Estojo: 2 vials, 2 used syringes (clips), 2 sealed packs, alcohol sachets. All content lives in the BASE."""
from dataclasses import dataclass

import cadquery as cq

RIB = 1.6  # thickness of holder ribs/rings (>= printer min wall)
CLIP_T = 3.0  # clip ring thickness along the syringe axis
LID_PLATE = 2.4  # smooth top plate thickness
LID_CAVITY = 1.2  # lid interior depth above the rim (clearance over the tallest content)
HINGE_R = 3.6  # barrel outer radius
HINGE_GAP = 0.6  # back wall -> barrel clearance
HINGE_SPAN = 60.0
HINGE_N = 5  # barrels, alternating base/lid/base/lid/base
LATCH_W = 24.0  # flexible tab width
LATCH_T = 1.6  # tab thickness
LATCH_TOOTH = 1.0  # tooth / ridge protrusion


@dataclass
class Slot:
    x: float
    y: float
    z: float
    w: float
    d: float
    h: float


def clip_ranges(p, slot: Slot) -> list[tuple[float, float]]:
    """X ranges (interior coords) of the clips: barrel only, never over the plunger rod."""
    cap, barrel = p.v("syringe_cap_length"), p.v("syringe_barrel_length")
    return [(slot.x + cap + f * barrel - CLIP_T / 2, slot.x + cap + f * barrel + CLIP_T / 2) for f in (0.25, 0.75)]


def _dims(p):
    v = p.v
    vial_slot = v("vial_diameter") + v("vial_clearance") + 2 * RIB
    ring_od = v("syringe_body_diameter") + 2 * v("syringe_clip_clearance") + 2 * RIB
    pack_d = v("new_pack_width") + 2 * v("syringe_clip_clearance") + 2 * RIB
    sach_w = v("alcohol_sachet_length") + 2 * v("syringe_clip_clearance") + 2 * RIB
    sach_d = v("alcohol_sachet_width") + 2 * v("syringe_clip_clearance") + 2 * RIB
    sach_h = v("alcohol_sachet_count") * v("alcohol_sachet_thickness")
    return vial_slot, ring_od, pack_d, sach_w, sach_d, sach_h


def layout(p) -> dict[str, Slot]:
    """Slots in base-interior coordinates (origin: inner lower-left corner at floor level)."""
    v = p.v
    g = v("item_gap")
    vial, ring, pack_d, sach_w, sach_d, sach_h = _dims(p)
    syr_w = v("syringe_extended_length") + 2 * v("syringe_clip_clearance")
    pack_w = v("new_pack_length") + 2 * v("syringe_clip_clearance")
    row_top = max(vial, sach_d)
    inner_l = max(syr_w, pack_w, 2 * vial + g + g + sach_w) + 2 * g
    # rows bottom -> top: packs, syringes, vials/sachets
    s: dict[str, Slot] = {}
    y = g
    for i in (1, 2):
        s[f"pack_{i}"] = Slot(g, y, 0, pack_w, pack_d, v("new_pack_thickness") + 2 * RIB)
        y += pack_d + g
    for i in (1, 2):
        s[f"syringe_{i}"] = Slot(g, y, 0, syr_w, ring, ring)
        y += ring + g
    vh = v("vial_height")
    for i in (1, 2):
        s[f"vial_{i}"] = Slot(g + (i - 1) * (vial + g), y, 0, vial, vial, vh)
    s["sachets"] = Slot(inner_l - g - sach_w, y, 0, sach_w, sach_d, sach_h + RIB)
    return s


def _interior_size(p):
    s = layout(p)
    g = p.v("item_gap")
    return (
        max(c.x + c.w for c in s.values()) + g,
        max(c.y + c.d for c in s.values()) + g,
        max(c.z + c.h for c in s.values()),
    )


def outer_size(p) -> tuple[float, float, float]:
    li, wi, hi = _interior_size(p)
    wall = p.v("wall_thickness")
    return (li + 2 * wall, wi + 2 * wall, hi + p.v("floor_thickness"))


def _rbox(x, y, h, r, z=0.0):
    o = cq.Workplane("XY").rect(x, y).extrude(h).translate((x / 2, y / 2, z))
    return o.edges("|Z").fillet(r) if r > 0.001 else o


def _box(x, y, z, w, d, h):
    return cq.Workplane("XY").box(w, d, h, centered=False).translate((x, y, z))


def _cyl_x(r, length, x, y, z):
    return cq.Workplane("XY").newObject([cq.Solid.makeCylinder(r, length, cq.Vector(x, y, z), cq.Vector(1, 0, 0))])


def _clip(p, x, cy, cz, h, oz, e=0.5):
    """One C-clip (ring od h, opening on top) at x, embedded e into the floor at oz."""
    r_in = p.v("syringe_body_diameter") / 2 + p.v("syringe_clip_clearance")
    opening = 0.8 * p.v("syringe_body_diameter") + p.v("syringe_clip_clearance")
    clip = _cyl_x(h / 2, CLIP_T, x, cy, cz).union(_box(x, cy - h / 2, oz - e, CLIP_T, h, h / 2 + e))
    clip = clip.cut(_cyl_x(r_in, CLIP_T, x, cy, cz))
    return clip.cut(_box(x - 0.1, cy - opening / 2, cz, CLIP_T + 0.2, opening, h))


def _base(p) -> cq.Workplane:
    v = p.v
    wall, floor = v("wall_thickness"), v("floor_thickness")
    L, W, H = outer_size(p)
    r = v("corner_radius")
    body = _rbox(L, W, H, r).cut(_rbox(L - 2 * wall, W - 2 * wall, H, max(r - wall, 0.0), z=floor).translate((wall, wall, 0)))
    e = 0.5  # embed holders into the floor so unions fuse
    sl = layout(p)
    vial, ring, pack_d, sach_w, sach_d, sach_h = _dims(p)
    ox, oy, oz = wall, wall, floor

    def add(solid):
        nonlocal body
        body = body.union(solid)

    for n in ("vial_1", "vial_2"):  # open-top rings: vial lifts out by hand
        s = sl[n]
        cx, cy = ox + s.x + s.w / 2, oy + s.y + s.d / 2
        ring_h = 0.5 * v("vial_height")
        outer = cq.Workplane("XY").circle(s.w / 2).extrude(ring_h + e).translate((cx, cy, oz - e))
        hole = cq.Workplane("XY").circle((v("vial_diameter") + v("vial_clearance")) / 2).extrude(ring_h + 1).translate((cx, cy, oz))
        add(outer.cut(hole))

    for n in ("syringe_1", "syringe_2"):  # C-clips, opening on top = 0.8*D + clearance
        s = sl[n]
        cy, cz = oy + s.y + s.d / 2, oz + s.h / 2
        for x0, _ in clip_ranges(p, s):
            add(_clip(p, ox + x0, cy, cz, s.h, oz))

    for n in ("pack_1", "pack_2"):  # straight channel: two rails, pack lies between them
        s = sl[n]
        for y in (oy + s.y, oy + s.y + s.d - RIB):
            add(_box(ox + s.x, y, oz - e, s.w, RIB, s.h + e))

    s = sl["sachets"]  # rim frame with finger notch on the front wall
    x0, y0 = ox + s.x, oy + s.y
    frame = _box(x0, y0, oz - e, s.w, s.d, s.h + e).cut(_box(x0 + RIB, y0 + RIB, oz, s.w - 2 * RIB, s.d - 2 * RIB, s.h + 1))
    notch_r = min(s.w / 4, s.h)
    notch = cq.Workplane("XZ").center(x0 + s.w / 2, oz + s.h).circle(notch_r).extrude(-(RIB + 1)).translate((0, y0 - 0.5, 0))
    add(frame.cut(notch))
    for x0, x1 in _barrel_xs(p, "base"):  # hinge barrels + web, pin hole through all
        add(_hinge_barrel(p, x0, x1, H - HINGE_R, H))
    add(_ridge(p))
    return body


def hinge_axis(p):
    L, W, H = outer_size(p)
    return (L / 2, W + HINGE_GAP + HINGE_R, H), (1.0, 0.0, 0.0)


def hinge_segments(p) -> list[tuple[str, float, float]]:
    L = outer_size(p)[0]
    g = p.v("hinge_clearance")
    n = (HINGE_SPAN - (HINGE_N - 1) * g) / HINGE_N
    x0 = L / 2 - HINGE_SPAN / 2
    return [("base" if i % 2 == 0 else "lid", x0 + i * (n + g), x0 + i * (n + g) + n) for i in range(HINGE_N)]


def _barrel_xs(p, owner):
    return [(a, b) for o, a, b in hinge_segments(p) if o == owner]


def _hinge_barrel(p, x0, x1, z0, z1):
    """Barrel around the hinge axis + web back to the body (z0..z1) with the pin hole cut through."""
    (_, ay, az), _d = hinge_axis(p)
    W = outer_size(p)[1]
    barrel = _cyl_x(HINGE_R, x1 - x0, x0, ay, az)
    web = _box(x0, W - 1.0, z0, x1 - x0, ay - W + 1.0, z1 - z0)
    hole = _cyl_x((p.v("hinge_pin_diameter") + p.v("hinge_clearance")) / 2, x1 - x0 + 2, x0 - 1, ay, az)
    return barrel.union(web).cut(hole)


def _latch_profile(pts, x0, w):
    return cq.Workplane("YZ").polyline(pts).close().extrude(w).translate((x0, 0, 0))


def _latch_z(p):
    """Ridge z range and tooth z range (closed pose), derived from the base height."""
    H = outer_size(p)[2]
    c = p.v("latch_clearance")
    zr0, zr1 = H - 7.5, H - 6.0
    zt1 = zr0 - c
    return (zr0, zr1), (zt1 - 1.5, zt1)


def _ridge(p):
    L = outer_size(p)[0]
    (zr0, zr1), _ = _latch_z(p)
    t = LATCH_TOOTH
    pts = [(0.5, zr0), (-t, zr0), (-t, zr1 - 1.0), (0.0, zr1), (0.5, zr1)]
    return _latch_profile(pts, L / 2 - LATCH_W / 2 - 2, LATCH_W + 4)


def _lid_closed(p) -> cq.Workplane:
    """Single source of lid geometry, in the CLOSED pose (underside on the base rim at z=H)."""
    v = p.v
    wall, r = v("wall_thickness"), v("corner_radius")
    L, W, H = outer_size(p)
    top = H + LID_CAVITY + LID_PLATE
    lid = _rbox(L, W, LID_CAVITY + LID_PLATE, r, z=H).cut(
        _rbox(L - 2 * wall, W - 2 * wall, LID_CAVITY, max(r - wall, 0.0), z=H).translate((wall, wall, 0)))
    for x0, x1 in _barrel_xs(p, "lid"):
        lid = lid.union(_hinge_barrel(p, x0, x1, H, top))
    return lid.union(_latch_tab(p))


def _latch_tab(p) -> cq.Workplane:
    """Flexible latch tab (closed pose): bridge over the plate, tab hanging outside the front wall, tooth under the ridge."""
    L, _, H = outer_size(p)
    top = H + LID_CAVITY + LID_PLATE
    c = p.v("latch_clearance")
    _, (zt0, zt1) = _latch_z(p)
    x0 = L / 2 - LATCH_W / 2
    y_in = -(LATCH_TOOTH + c)  # tab inner face: clears the ridge by c
    y_out = y_in - LATCH_T
    bottom = zt0 - 1.0
    tab = _box(x0, y_out, H + LID_CAVITY, LATCH_W, -y_out + 0.5, LID_PLATE)
    tab = tab.union(_box(x0, y_out, bottom, LATCH_W, LATCH_T, top - bottom))
    zb = H + LID_CAVITY  # tab root: small gussets on both faces against snapping across layer lines
    tab = tab.union(_latch_profile([(y_out, zb + 0.1), (y_out - 1.5, zb + 0.1), (y_out, zb - 1.5)], x0, LATCH_W))
    tab = tab.union(_latch_profile([(y_in, zb + 0.1), (y_in + 1.0, zb + 0.1), (y_in, zb - 1.0)], x0, LATCH_W))
    tooth = [(y_in + 0.2, zt0), (y_in + LATCH_TOOTH, zt0 + 1.0), (y_in + LATCH_TOOTH, zt1), (y_in + 0.2, zt1)]
    return tab.union(_latch_profile([(y_in - 0.2, zt0)] + tooth[1:] + [(y_in - 0.2, zt1)], x0, LATCH_W))


def lid_at(p, angle_deg: float) -> cq.Workplane:
    """Closed lid swung open by angle_deg about the hinge axis (front edge goes up)."""
    a, d = hinge_axis(p)
    return _lid_closed(p).rotate(a, (a[0] + d[0], a[1] + d[1], a[2] + d[2]), -angle_deg)


def parts(p) -> dict[str, cq.Workplane]:
    """Print orientation: lid flipped so the outer top face lies on the bed."""
    lid = _lid_closed(p).rotate((0, 0, 0), (1, 0, 0), 180)
    zmin = lid.val().BoundingBox().zmin
    return {"base": _base(p), "lid": lid.translate((0, 0, -zmin))}


def assembly(p) -> dict[str, cq.Workplane]:
    v = p.v
    wall, floor = v("wall_thickness"), v("floor_thickness")
    sl = layout(p)
    off = (wall, wall, floor)
    asm = {"base": _base(p), "lid": _lid_closed(p)}

    def cyl_z(s, d, h):
        return cq.Workplane("XY").circle(d / 2).extrude(h).translate((off[0] + s.x + s.w / 2, off[1] + s.y + s.d / 2, off[2] + s.z))

    for i in (1, 2):
        asm[f"content_vial_{i}"] = cyl_z(sl[f"vial_{i}"], v("vial_diameter"), v("vial_height"))
        s = sl[f"syringe_{i}"]
        asm[f"content_syringe_{i}"] = _cyl_x(
            v("syringe_body_diameter") / 2, v("syringe_extended_length"),
            off[0] + s.x + v("syringe_clip_clearance"), off[1] + s.y + s.d / 2, off[2] + s.h / 2)
        s = sl[f"pack_{i}"]
        asm[f"content_pack_{i}"] = _box(
            off[0] + s.x + v("syringe_clip_clearance"), off[1] + s.y + RIB + v("syringe_clip_clearance"), off[2],
            v("new_pack_length"), v("new_pack_width"), v("new_pack_thickness"))
    s = sl["sachets"]
    asm["content_sachets"] = _box(
        off[0] + s.x + RIB + v("syringe_clip_clearance"), off[1] + s.y + RIB + v("syringe_clip_clearance"), off[2],
        v("alcohol_sachet_length"), v("alcohol_sachet_width"), v("alcohol_sachet_count") * v("alcohol_sachet_thickness"))
    return asm


def _ground(wp: cq.Workplane, y0: float = 0.0) -> cq.Workplane:
    """Move so the bounding box starts at x=0, y=y0, z=0 (flat on the bed)."""
    b = wp.val().BoundingBox()
    return wp.translate((-b.xmin, y0 - b.ymin, -b.zmin))


def coupons(p) -> dict[str, cq.Workplane]:
    """Small fit-test pieces built from the case's own feature functions (print these first)."""
    v = p.v
    floor, wall = v("floor_thickness"), v("wall_thickness")
    L, W, H = outer_size(p)
    # one clip on a floor stub
    ring = v("syringe_body_diameter") + 2 * v("syringe_clip_clearance") + 2 * RIB
    stub = _box(0, 0, 0, 15.0, ring, floor)
    clip = stub.union(_clip(p, (15.0 - CLIP_T) / 2, ring / 2, floor + ring / 2, ring, floor))
    # one base barrel + one lid barrel, side by side as in the hinge
    (_, b0, b1), (_, l0, l1) = hinge_segments(p)[0], hinge_segments(p)[1]
    top = H + LID_CAVITY + LID_PLATE
    hb = _ground(_hinge_barrel(p, b0, b1, H - HINGE_R, H))
    hl = _ground(_hinge_barrel(p, l0, l1, H, top).rotate((0, 0, 0), (1, 0, 0), 180))
    hinge = hb.union(hl.translate((b1 - b0 + v("hinge_clearance"), 0, 0)))
    # wall stub with the ridge + lid piece with the tab (flipped to print position)
    x0 = L / 2 - LATCH_W / 2 - 2
    ridge = _box(x0, 0, H - 12.0, LATCH_W + 4, wall, 12.0).union(_ridge(p))
    plate = _box(L / 2 - LATCH_W / 2, 0, H + LID_CAVITY, LATCH_W, 8.0, LID_PLATE)
    tab = _latch_tab(p).union(plate).rotate((0, 0, 0), (1, 0, 0), 180)
    latch = _ground(ridge).union(_ground(tab, 14.0))
    # 3 mm vial ring with the real hole
    vial = v("vial_diameter") + v("vial_clearance")
    vring = cq.Workplane("XY").circle(vial / 2 + RIB).circle(vial / 2).extrude(3.0)
    return {"clip": clip, "hinge": hinge, "latch": latch, "vial_ring": vring}


def notes(p) -> list[str]:
    """Assembly notes rendered in RELATORIO.md."""
    length = hinge_segments(p)[-1][2] - hinge_segments(p)[0][1]
    return [
        f"Pino da dobradiça: corte um pedaço de filamento de {p.v('hinge_pin_diameter')} mm de diâmetro "
        f"com {length:.1f} mm de comprimento (não há peça de pino impressa)."
    ]
