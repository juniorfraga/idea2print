---
name: idea2print
description: Turn an idea into a printable 3D file (STL, STEP, 3MF) with measured, parametric CAD, verification and fit-test coupons. Use when the user wants to 3D print something, model a part or case, make an STL/3MF, or asks things like "quero imprimir em 3D", "modelar peça", "gerar STL", "porta-copo", "estojo", "caixa", "suporte", "3D print this", "design a bracket/holder/case". Currently handles functional (CadQuery) parts only.
---

# idea2print

Idea -> measured parameters -> CadQuery model -> verified STL/STEP/3MF + coupons + report.
Reply in the user's language. This file is in English; talk to the user in theirs.

Run every command from the repo root of this skill (the folder containing this file; it is a `uv` project). Project paths passed to the CLI must be absolute or relative to that root:

```
uv run idea2print build <project_dir>   # writes <project_dir>/out/ ; exit 0 = ok, 1 = error
uv run idea2print measure <mesh_file>   # JSON: extents, watertight, cross-sections, inner diameters
uv run idea2print verify <file.stl>     # per-part checks with default printer limits
```

## Hard rules

1. Never ask for or accept passwords, API keys or tokens in chat. If a tool needs one, tell the user to put it in a local config file themselves.
2. Never take a dimension from an AI-generated image. Images are visual reference only.
3. Every number in `params.toml` carries its origin (`informada` | `projeto` | `estimada`). No unlabeled values. `informada` = given by the user or a deliberate design decision (not necessarily physically confirmed); after a coupon/physical check the user may confirm a value as `informada`.
4. Never say "ready to print" or "validated". Say: **"geometry verified by software; physical test pending."**
5. Always tell the user to print the coupons first (`out/coupon_*`) and check fit before the full part.
6. Never download third-party files without the user's OK. Never redistribute third-party geometry unless its license allows it.
7. Medical / food / body-contact objects: repeat these notes in the delivery message (see step 7).

## Flow

### 1. Short interview
Ask only what you need, few questions at a time: what is it, what is it for, what goes inside/on it, printer (bed size, nozzle), material (PLA/PETG/...). Put printer limits in `[impressao]` of `params.toml` if they differ from defaults.

### 2. Research — not available yet
Automatic research on MakerWorld/Printables/Thingiverse is **not available yet**. Instead ask the user for links to similar projects (record each project's license too) and for the measurements they have. If they download a model file (STL/3MF/OBJ; a STEP file must be exported to STL/3MF first, `measure` fails on STEP), run `uv run idea2print measure <file>` and show them the extents and cross-section inner diameters so they confirm which number is the one they need (e.g. cavity diameter). If the JSON has `scale_suspect: true`, the units are probably wrong (inches/cm): confirm with the user before using any dimension. A measurement taken from someone else's project is origin `projeto` and needs its link in `fonte`.

### 3. Fill the gaps, record origins
Ask only for measurements still missing. Prefer real measurement with calipers/ruler. Never invent a value silently: every provisional value is `estimada` with a `nota` and appears in "Falta medir".

Project folder: `<anywhere>/<name>/` containing `params.toml` and `model.py`.

```toml
[impressao]                 # optional; defaults: bed 256x256x256, min wall 1.2, overhang 45
bed_mm = [256, 256, 256]
min_wall_mm = 1.2
max_overhang_deg = 45

[medidas.vial_diameter]
valor = 16.0
origem = "informada"        # informada | projeto | estimada
nota = "paquimetro"         # optional

[medidas.hole_d]
valor = 6
origem = "projeto"
fonte = "https://..."       # REQUIRED when origem = "projeto"
```

Missing `origem`, unknown `origem`, or `projeto` without `fonte` makes the build fail with a clear message.

### 4. Concept image — optional, engines not available yet
Image engines are a later addition. If the user wants a picture, describe the design in words and ask them to confirm. Nothing in an image defines a dimension.

### 5. Write `model.py`
Functional route only (CadQuery). Organic / AI-mesh / hybrid routes are **not available yet**: say so and offer the nearest functional design.

Contract (`p` is the params object; read values with `p.v("key")`, never hard-code a measurement):

```python
import cadquery as cq

def parts(p):       # REQUIRED. {name: cq.Workplane}. Each part in PRINT orientation, flat on the bed.
    return {"base": ..., "lid": ...}

def assembly(p):    # optional. Closed pose, all parts in final position, for collision check + renders.
    return {"base": ..., "lid": ..., "content_vial": ...}
    # keys starting "content_" = gauges of the real objects (convention only; every pair of
    # assembly parts is collision-tested, so a gauge overlapping a wall is an error)
    # keys starting "lid" = removed to render the open view (open_iso.png / open_top.png)

def coupons(p):     # optional but expected for fits. {name: cq.Workplane}, small test pieces,
    return {"clip": ..., "hinge": ...}   # exported as coupon_<name>.* and verified like parts
```

Reference projects: `examples/estojo/` (full case with hinge, latch, clips, coupons) and `tests/fixtures/caixa/` (minimal). Copy their structure. Build coupons from the same feature functions as the real part so they test the same geometry. Add clearances through measures (e.g. `vial_clearance`), not magic numbers.

### 6. Build and fix until `ok`
```
uv run idea2print build <project_dir>
```
- Prints only failures: `[error] ...` (blocks, exit 1) and `[warning] ...` (does not block). Last line: `report: <dir>/out/RELATORIO.md`. A clean build prints only that line; success = exit 0, there is no "ok" message.
- Checks per part: watertight (error), fits bed (error), min wall (warning), overhang area (warning); in `assembly()`: any two parts overlapping (including `content_*` gauges vs walls) is an error.
- A build error is also written into `RELATORIO.md`; read it, fix `params.toml`/`model.py`, rebuild. Loop until exit 0.
- Warnings: do not hide them. Fix if cheap (thicker wall, chamfer); otherwise tell the user what each warning means for printing (overhang -> may need supports).
- Outputs in `out/`: `<part>.stl` + `<part>.step`, `<folder-name>.3mf`, `coupon_*`, `iso.png`, `top.png` (and `open_iso.png`, `open_top.png` when the assembly has `lid*` keys) rendered from the model, and `RELATORIO.md`.
- Look at the PNGs yourself if you can, to catch an obviously wrong shape. `idea2print` re-run deletes stale `*.stl/*.step/*.3mf/*.png/RELATORIO.md` in `out/` only.

### 7. Deliver
Message to the user, in their language:
1. Path to `out/` and the list of files (STL per part, STEP, 3MF, coupons, renders, report).
2. The **"Falta medir"** list from `RELATORIO.md` (every `estimada` value) and what to measure physically.
3. Which coupons to print first and what each checks (ring -> diameter, hinge -> pin/clearance, clip -> grip, latch -> snap).
4. Exact wording: "geometry verified by software; physical test pending." (in the user's language). Never "ready to print".
5. Warnings from the build and what they mean.
6. Hinge pin (when the model has `notes()`, it is in the report "Montagem" section): tell the user to cut a piece of filament of diameter `hinge_pin_diameter` and length = hinge length (the report gives it) to use as the hinge pin.
7. Small coupons can show thin-wall warnings that the big part averages away (`min_wall` uses a 2nd-percentile over samples): read the warnings on the coupons too.
8. If any measure came from a third-party project (`projeto`): suggest first printing a thin gauge (e.g. a 3 mm ring) to confirm that number.
9. Medical / food objects, repeat all of:
   - FDM parts are not sterile and do not control temperature.
   - Never design for reusing used syringes or needles.
   - Clips/latches must never press a syringe plunger.
   - Food contact: layer lines harbor bacteria; do not claim food-safe.

After the user prints coupons and reports real fits, update `params.toml` (origin `informada`, i.e. confirmed by the user), rebuild, and repeat step 7.

## Not available yet (Plan 2/3)
Automatic web research, concept-image engines, organic/AI-mesh and hybrid routes, setup wizard. For all of them: ask the user for links/measurements, and use `idea2print measure` on files they downloaded.
