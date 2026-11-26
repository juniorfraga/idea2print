"""Geometric verification of printable parts and assemblies."""
from dataclasses import dataclass
from itertools import combinations, permutations
from typing import Literal

import numpy as np
import trimesh

from idea2print.params import PrinterLimits


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    level: Literal["error", "warning"]


def _fits_bed(mesh: trimesh.Trimesh, limits: PrinterLimits) -> Check:
    size = mesh.extents
    # any axis permutation (6 orientations) that fits
    ok = any(all(size[p[i]] <= limits.bed_mm[i] for i in range(3)) for p in permutations(range(3)))
    detail = f"extents {size.round(1).tolist()} mm vs bed {list(limits.bed_mm)}"
    return Check("fits_bed", ok, detail, "error")


def _min_wall(mesh: trimesh.Trimesh, limits: PrinterLimits) -> Check:
    try:
        pts, face_idx = trimesh.sample.sample_surface(mesh, 2000, seed=0)
        t = trimesh.proximity.thickness(mesh, pts, exterior=False, normals=mesh.face_normals[face_idx], method="ray")
        valid = np.isfinite(t) & (t > 0)
        if valid.mean() < 0.5:
            return Check("min_wall", False, "thickness could not be measured reliably", "warning")
        t = t[valid]
        p2 = float(np.percentile(t, 2))
    except Exception as e:  # broken meshes must still yield a Check
        return Check("min_wall", False, f"could not measure wall thickness: {e}", "warning")
    return Check("min_wall", bool(p2 >= limits.min_wall_mm), f"p2 thickness {p2:.2f} mm vs min {limits.min_wall_mm} mm", "warning")


def _overhang(mesh: trimesh.Trimesh, limits: PrinterLimits) -> Check:
    nz = mesh.face_normals[:, 2]
    base = mesh.bounds[0][2]
    low_z = mesh.vertices[mesh.faces][:, :, 2].min(axis=1)
    bad = (nz < -np.sin(np.radians(limits.max_overhang_deg))) & (low_z > base + 0.3)
    area = float(mesh.area_faces[bad].sum())
    ok = bool(area <= 0.01 * mesh.area)
    return Check("overhang", ok, f"{area:.1f} mm2 overhang beyond {limits.max_overhang_deg} deg", "warning")


def verify_part(name: str, mesh: trimesh.Trimesh, limits: PrinterLimits) -> list[Check]:
    wt = Check("watertight", bool(mesh.is_watertight), f"{name}: " + ("closed" if mesh.is_watertight else "mesh has open edges"), "error")
    return [wt, _fits_bed(mesh, limits), _min_wall(mesh, limits), _overhang(mesh, limits)]


def check_collisions(meshes: dict[str, trimesh.Trimesh], tol_mm3: float = 1.0) -> list[Check]:
    out = []
    open_names = {n for n, m in meshes.items() if not m.is_watertight}
    for n in open_names:
        out.append(Check("collision", False, f"{n} is not watertight; collision not tested", "error"))
    for (na, a), (nb, b) in combinations(meshes.items(), 2):
        if na in open_names or nb in open_names:
            continue
        if (a.bounds[1] < b.bounds[0]).any() or (b.bounds[1] < a.bounds[0]).any():
            continue  # AABBs disjoint
        inter = trimesh.boolean.intersection([a, b], engine="manifold")
        vol = inter.volume if len(inter.faces) and inter.extents.min() > 1e-6 else 0.0  # empty/flat contact: volume math warns
        if vol > tol_mm3:
            out.append(Check("collision", False, f"{na} and {nb} overlap by {vol:.1f} mm3", "error"))
    return out
