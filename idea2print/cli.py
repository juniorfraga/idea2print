import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import trimesh

from idea2print.measure import measure_file
from idea2print.params import PrinterLimits
from idea2print.project import build_project
from idea2print.verify import verify_part


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="idea2print")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("build", "measure", "verify"):
        sub.add_parser(c).add_argument("path", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        r = build_project(a.path)
        for c in r.checks:
            if not c.ok:
                print(f"[{c.level}] {c.name}: {c.detail}")
        print(f"report: {r.report}")
        return 0 if r.ok else 1
    if a.cmd == "measure":
        print(json.dumps(asdict(measure_file(a.path)), indent=2))
        return 0
    mesh = trimesh.load(a.path, force="mesh")
    checks = verify_part(a.path.stem, mesh, PrinterLimits())
    for c in checks:
        print(f"[{'OK' if c.ok else c.level}] {c.name}: {c.detail}")
    return 0 if all(c.ok or c.level != "error" for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
