"""RELATORIO.md writer (pt-BR)."""
from pathlib import Path

from idea2print.params import Params
from idea2print.verify import Check

FIXED = "Geometria verificada por software; teste físico pendente."


def write_report(path: Path, name: str, params: Params | None, checks: list[Check], files: dict[str, Path], notes: list[str] | None = None) -> Path:
    L = [f"# Relatório — {name}", "", FIXED, ""]
    if params is not None:
        L += ["## Medidas", "", "| medida | valor | origem | fonte |", "|---|---|---|---|"]
        L += [f"| {k} | {p.value} | {p.origin} | {p.source or p.note or ''} |" for k, p in params.items()]
        L += ["", "## Falta medir", ""]
        est = params.estimated()
        L += [f"- {k}: valor estimado ({params[k].value}); medir a peça real" for k in est] or ["- nada estimado"]
    if notes:
        L += ["", "## Montagem", ""] + [f"- {n}" for n in notes]
    L += ["", "## Verificações", ""]
    for c in checks:
        mark = "OK" if c.ok else ("ERRO" if c.level == "error" else "AVISO")
        L.append(f"- [{mark}] {c.name}: {c.detail}")
    L += ["", "## Arquivos", ""] + [f"- {p.name}" for p in files.values()]
    L += ["", FIXED, ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L), encoding="utf-8")
    return path
