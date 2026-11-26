"""params.toml loader: every measurement carries an origin label."""
import tomllib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Origin = Literal["informada", "projeto", "estimada"]
ORIGINS = ("informada", "projeto", "estimada")


class ParamError(ValueError):
    pass


@dataclass(frozen=True)
class Param:
    value: float | int | str
    origin: Origin
    source: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class PrinterLimits:
    bed_mm: tuple[float, float, float] = (256, 256, 256)
    min_wall_mm: float = 1.2
    max_overhang_deg: float = 45.0


@dataclass(frozen=True)
class Params(Mapping[str, Param]):
    items_: dict[str, Param] = field(default_factory=dict)
    printer: PrinterLimits = PrinterLimits()

    def __getitem__(self, key: str) -> Param:
        return self.items_[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.items_)

    def __len__(self) -> int:
        return len(self.items_)

    def v(self, key: str) -> float | int | str:
        return self.items_[key].value

    def estimated(self) -> list[str]:
        return [k for k, p in self.items_.items() if p.origin == "estimada"]


def _positive(imp: dict, key: str) -> float:
    v = imp[key]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
        raise ParamError(f"impressao.{key}: must be a positive number, got {v!r}")
    return float(v)


def _printer(imp: dict) -> PrinterLimits:
    kw: dict = {}
    if "bed_mm" in imp:
        b = imp["bed_mm"]
        if (
            not isinstance(b, list)
            or len(b) != 3
            or any(isinstance(x, bool) or not isinstance(x, (int, float)) or x <= 0 for x in b)
        ):
            raise ParamError(f"impressao.bed_mm: must be 3 positive numbers, got {b!r}")
        kw["bed_mm"] = tuple(float(x) for x in b)
    if "min_wall_mm" in imp:
        kw["min_wall_mm"] = _positive(imp, "min_wall_mm")
    if "max_overhang_deg" in imp:
        kw["max_overhang_deg"] = _positive(imp, "max_overhang_deg")
        if kw["max_overhang_deg"] >= 90:
            raise ParamError(f"impressao.max_overhang_deg: must be < 90, got {imp['max_overhang_deg']!r}")
    return PrinterLimits(**kw)


def load_params(path: Path) -> Params:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    items: dict[str, Param] = {}
    for key, m in data.get("medidas", {}).items():
        if not isinstance(m, dict):
            raise ParamError(f"medidas.{key}: must be a table with valor/origem, got {m!r}")
        if "valor" not in m:
            raise ParamError(f"medidas.{key}: 'valor' missing")
        origin = m.get("origem")
        if origin is None:
            raise ParamError(f"medidas.{key}: 'origem' missing (use {'|'.join(ORIGINS)})")
        if origin not in ORIGINS:
            raise ParamError(f"medidas.{key}: invalid origem '{origin}' (use {'|'.join(ORIGINS)})")
        if origin == "projeto" and not m.get("fonte"):
            raise ParamError(f"medidas.{key}: origem 'projeto' requires 'fonte'")
        items[key] = Param(m["valor"], origin, m.get("fonte"), m.get("nota"))
    return Params(items, _printer(data.get("impressao", {})))
