from pathlib import Path

import cadquery as cq
import numpy as np
import trimesh


def to_mesh(shape: cq.Workplane | cq.Shape, tol_mm: float = 0.05) -> trimesh.Trimesh:
    # all solids, not just .val(): a multi-solid Workplane must export whole
    solid = cq.Compound.makeCompound(shape.vals()) if isinstance(shape, cq.Workplane) else shape
    verts, tris = solid.tessellate(tol_mm)
    mesh = trimesh.Trimesh(
        np.array([v.toTuple() for v in verts]), np.array(tris), process=True
    )
    mesh.merge_vertices()
    return mesh


BED_GAP_MM = 10.0


def export_parts(parts: dict[str, cq.Workplane], out: Path, project: str) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    scene = trimesh.Scene()
    cursor = 0.0  # 3MF scene only: parts side by side on the bed, STLs keep their own frame
    for name, wp in parts.items():
        mesh = to_mesh(wp)
        mesh.export(out / f"{name}.stl")
        cq.exporters.export(wp, str(out / f"{name}.step"))
        lo, hi = mesh.bounds
        placed = mesh.copy()
        placed.apply_translation((cursor - lo[0], -lo[1], -lo[2]))
        cursor += hi[0] - lo[0] + BED_GAP_MM
        scene.add_geometry(placed, node_name=name, geom_name=name)
        paths[f"{name}.stl"] = out / f"{name}.stl"
        paths[f"{name}.step"] = out / f"{name}.step"
    paths["3mf"] = out / f"{project}.3mf"
    scene.export(paths["3mf"], file_type="3mf")
    return paths
