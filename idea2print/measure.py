import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon


@dataclass
class Section:
    z: float
    width: float
    depth: float
    inner_diameters: list[float]


@dataclass
class ObjectMeasure:
    name: str
    extents_mm: tuple[float, float, float]
    watertight: bool
    sections: list[Section]


@dataclass
class MeasureReport:
    objects: list[ObjectMeasure]
    scale_suspect: bool


def _sections(mesh: trimesh.Trimesh, heights: int) -> list[Section]:
    lo, hi = mesh.bounds[:, 2]
    out = []
    for z in np.linspace(lo, hi, heights + 2)[1:-1]:
        cut = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if cut is None:
            continue
        planar, _ = cut.to_2D()
        width, depth = planar.extents
        diameters = [
            2 * math.sqrt(Polygon(ring).area / math.pi)
            for poly in planar.polygons_full
            for ring in poly.interiors
        ]
        out.append(Section(float(z), float(width), float(depth), diameters))
    return out


def measure_file(path: Path, heights: int = 5) -> MeasureReport:
    scene = trimesh.load(path, force="scene")
    objects = []
    for i, mesh in enumerate(scene.dump()):
        if not isinstance(mesh, trimesh.Trimesh):
            continue
        name = mesh.metadata.get("name") or f"object_{i}"
        objects.append(
            ObjectMeasure(
                name=str(name),
                extents_mm=tuple(float(e) for e in mesh.extents),
                watertight=bool(mesh.is_watertight),
                sections=_sections(mesh, heights),
            )
        )
    biggest = max((max(o.extents_mm) for o in objects), default=0.0)
    return MeasureReport(objects, scale_suspect=biggest < 5 or biggest > 1000)
