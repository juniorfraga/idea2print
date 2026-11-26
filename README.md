# idea2print

Open-source tool that turns an idea into a printable 3D file (STL, STEP, 3MF) with measured parametric CAD (CadQuery), software verification (watertight, bed fit, min wall, overhang, collisions), fit-test coupons and a report listing what still needs a physical measurement. Meant to be driven by an AI coding agent (Claude Code, Codex, Gemini CLI) through `SKILL.md`.

Status: functional route only. Packaging (`npx skills add`, `AGENTS.md`, EN + pt-BR docs, CI) coming in Plan 3.

## Install

```
git clone <this repo> && cd idea2print
uv sync
```

Point your agent at `SKILL.md` (for Claude Code: symlink the repo to `~/.claude/skills/idea2print`).

## Run the example

```
uv run idea2print build examples/estojo
```

Outputs go to `examples/estojo/out/`: STL/STEP per part, `estojo.3mf`, `coupon_*`, renders, `RELATORIO.md`.

Other commands: `uv run idea2print measure <mesh>` (JSON measurements of a downloaded mesh), `uv run idea2print verify <file.stl>`.

Geometry is verified by software; physical test is always pending. Print the coupons first.
