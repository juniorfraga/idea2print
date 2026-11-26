from pathlib import Path
from typing import Literal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

_VIEWS = {"iso": (25, -60), "top": (90, -90), "front": (0, -90)}  # (elev, azim)


def render_png(
    meshes: dict[str, trimesh.Trimesh], path: Path, view: Literal["iso", "top", "front"]
) -> Path:
    if not meshes:
        raise ValueError("render_png: no meshes to render")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(6, 6), dpi=100)
    ax = fig.add_subplot(projection="3d")
    palette = ["#4c78a8", "#f58518", "#54a24b", "#b279a2", "#9d755d", "#bab0ac"]
    ax.computed_zorder = False  # draw in insertion order: contents last, so they are not hidden by the base
    items = sorted(enumerate(meshes.items()), key=lambda t: t[1][0].startswith("content_"))
    for i, (name, m) in items:
        content = name.startswith("content_")
        color = "#e41a1c" if content else palette[i % len(palette)]  # contents stand out
        poly = Poly3DCollection(m.vertices[m.faces], facecolor=color, edgecolor="none", linewidth=0, alpha=1.0 if content else 0.6)
        ax.add_collection3d(poly)
    allv = np.vstack([m.vertices for m in meshes.values()])
    lo, hi = allv.min(0), allv.max(0)
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(hi - lo)
    ax.view_init(*_VIEWS[view])
    ax.set_xlabel("X (mm)"); ax.set_ylabel("Y (mm)"); ax.set_zlabel("Z (mm)")
    fig.savefig(path)
    plt.close(fig)
    return path
