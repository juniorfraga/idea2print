"""Build pipeline: params.toml + model.py -> verified files + RELATORIO.md."""
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path

from idea2print.export import export_parts, to_mesh
from idea2print.params import Params, load_params
from idea2print.render import render_png
from idea2print.report import write_report
from idea2print.verify import Check, check_collisions, verify_part


@dataclass
class BuildResult:
    checks: list[Check]
    files: dict[str, Path] = field(default_factory=dict)
    report: Path | None = None
    ok: bool = False


def _load_model(project: Path):
    name = f"idea2print_model_{id(project)}_{len(sys.modules)}"
    spec = importlib.util.spec_from_file_location(name, project / "model.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # @dataclass + `from __future__ import annotations` looks the module up here
    sys.path.insert(0, str(project.resolve()))  # sibling imports
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(name, None)
        sys.path.remove(str(project.resolve()))
    return mod


def _run(project: Path, out: Path, params: Params, checks: list[Check], files: dict[str, Path], notes: list[str]) -> None:
    model = _load_model(project)
    if hasattr(model, "notes"):
        notes += list(model.notes(params))
    printable = dict(model.parts(params))
    if hasattr(model, "coupons"):
        printable.update({f"coupon_{k}": v for k, v in model.coupons(params).items()})
    if not printable:
        raise ValueError("model.parts() returned no parts")
    meshes = {n: to_mesh(w) for n, w in printable.items()}
    for n, m in meshes.items():
        checks += verify_part(n, m, params.printer)
    files.update(export_parts(printable, out, project.resolve().name))
    if hasattr(model, "assembly"):
        asm = {n: to_mesh(w) for n, w in model.assembly(params).items()}
        try:
            checks += check_collisions(asm)
        except Exception as e:
            checks.append(Check("collision", False, str(e), "error"))
        has_lid = any(n.startswith("lid") for n in asm)
        # closed views: contents would draw over the lid
        closed = {n: m for n, m in asm.items() if not (has_lid and n.startswith("content_"))}
        for v in ("iso", "top"):
            files[f"{v}.png"] = render_png(closed, out / f"{v}.png", v)
        opened = {n: m for n, m in asm.items() if not n.startswith("lid")}  # convention: lid parts are named "lid*"
        if opened and len(opened) < len(asm):  # has a lid: also show it open, contents visible
            for v in ("iso", "top"):
                files[f"open_{v}.png"] = render_png(opened, out / f"open_{v}.png", v)
    else:
        for v in ("iso", "top"):
            files[f"{v}.png"] = render_png(meshes, out / f"{v}.png", v)


def build_project(project: Path, out: Path | None = None) -> BuildResult:
    project = Path(project)
    out = Path(out) if out else project / "out"
    proj_r, out_r = project.resolve(), out.resolve()
    if out_r == proj_r or out_r in proj_r.parents:
        raise ValueError(f"out directory {out} must not be the project directory or a parent of it")
    if out.is_dir():  # drop stale artifacts only, never unrelated files
        for pat in ("*.stl", "*.step", "*.3mf", "*.png", "RELATORIO.md"):
            for f in out.glob(pat):
                f.unlink()
    checks: list[Check] = []
    files: dict[str, Path] = {}
    notes: list[str] = []
    params: Params | None = None
    try:
        params = load_params(project / "params.toml")
        _run(project, out, params, checks, files, notes)
    except Exception as e:  # any failure must still produce a report
        checks.append(Check("build", False, f"{type(e).__name__}: {e}", "error"))
    report = write_report(out / "RELATORIO.md", project.resolve().name, params, checks, files, notes)
    ok = not any(c.level == "error" and not c.ok for c in checks)
    return BuildResult(checks, files, report, ok)
