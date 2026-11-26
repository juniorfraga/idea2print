# idea2print — Plano 1: base + rota funcional + estojo V2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar o núcleo do idea2print (parâmetros com origem, medição de malha, verificação, exportação, renders, pipeline `build`) e, com ele, o estojo V2 do briefing — critério de pronto nº 1 do design.

**Architecture:** Pacote Python `idea2print` com CLI (`uv run idea2print <cmd>`). Cada projeto do usuário é uma pasta com `params.toml` (medidas + origem) e `model.py` (CadQuery) que expõe funções de contrato; o CLI constrói, verifica, exporta e gera um relatório. O `SKILL.md` conduz a conversa e chama o CLI.

**Tech Stack:** Python (versão fixada na Task 1 pelo que instalou no Mac Intel — ver nota de stack), uv, CadQuery, trimesh, manifold3d, matplotlib, pytest.

**Spec:** `docs/specs/2026-11-07-ideia-ate-impressao-design.md` (ler §5, §7, §11b, §13). Insumos do estojo: briefing original e kit de referência (não publicados; V1 e SnapLock ficam fora deste repo).

**Fora deste plano (planos seguintes):** Plano 2 = rotas orgânica e híbrida (motores de malha, conserto, escala, união) → critérios 2 e 3. Plano 3 = pesquisa (Printables/Thingiverse/MakerWorld), motores de imagem, assistente de instalação, empacotamento (`npx skills add`, `AGENTS.md`, README EN+pt-BR, CI).

**Nota de stack (07/11/2026):** `cadquery 2.8.0` puxa `numba 0.68` → `llvmlite 0.50`, que não tem wheel para macOS Intel e falha no build. **Combinação provada no Mac Intel do autor:** Python 3.12.14 + `cadquery 2.8.0` + `numba<0.61` (instalou 0.60.0, só wheels: `--only-binary llvmlite,numba`) + `trimesh 5.2.0` (tem `proximity.thickness`) + `manifold3d` + `matplotlib`; caixa com filete gerou sólido (volume 975,59 mm³).

## Global Constraints

- Licença MIT, `LICENSE` com "Copyright (c) 2026" + nome do autor.
- Origem de medida: exatamente `informada` | `projeto` | `estimada`; `projeto` exige `fonte` (URL). Verificador **avisa**, nunca bloqueia, por `estimada`.
- Limiares padrão: mesa 256 × 256 × 256 mm; parede mínima 1,2 mm; balanço 45°. Todos sobrescrevíveis em `[impressao]` do `params.toml`.
- Renders só a partir do modelo (nunca imagem de IA).
- Nenhuma credencial no repositório; config do usuário em `~/.config/idea2print/` (não usada neste plano).
- Código, identificadores e saída do CLI em inglês; `params.toml` do estojo e relatório em pt-BR (chaves em inglês).
- Nunca imprimir "ready to print"/"validado": o relatório diz "Geometria verificada por software; teste físico pendente."
- Estojo: tudo na BASE; tampa sem berço/clip interno; tampa e base com o mesmo contorno; cabe na Bambu A1.

## Review Focus

1. Malha baixada em polegadas ou cm (maior medida < 5 mm ou > 1000 mm) → `measure` marca `scale_suspect=True` em vez de devolver medida errada calada. Teste na Task 2.
2. 3MF com vários objetos e transformações → `measure` aplica as transformações e mede cada objeto. Teste na Task 2.
3. Malha de terceiros não fechada → `verify` reporta `watertight=False` e segue os outros checks, sem exceção. Teste na Task 3.
4. `params.toml` com chave sem `origem`, origem inválida ou `projeto` sem `fonte` → erro que cita a chave. Teste na Task 1.
5. Parâmetro extremo (seringa 300 mm) empurra o estojo para fora da mesa → `build` ainda escreve o relatório, com `fits_bed` reprovado e mensagem clara. Teste na Task 8.

---

### Task 1: Esqueleto do projeto + parâmetros com origem

**Files:**
- Create: `pyproject.toml`, `LICENSE`, `.gitignore` (`out/`, `.venv/`, `__pycache__/`), `idea2print/__init__.py`, `idea2print/params.py`
- Test: `tests/test_params.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) class Param: value: float | int | str; origin: Literal["informada","projeto","estimada"]; source: str | None; note: str | None`
- Produces: `class Params(Mapping[str, Param])` com `.v(key) -> float|int|str`, `.estimated() -> list[str]`, `.printer -> PrinterLimits`
- Produces: `@dataclass(frozen=True) class PrinterLimits: bed_mm: tuple[float,float,float] = (256,256,256); min_wall_mm: float = 1.2; max_overhang_deg: float = 45.0`
- Produces: `load_params(path: Path) -> Params`; `class ParamError(ValueError)`

Formato do `params.toml` (contrato de todos os projetos):

```toml
[impressao]            # opcional; sobrescreve PrinterLimits
bed_mm = [256, 256, 256]

[medidas.vial_diameter]
valor = 16.0
origem = "estimada"
nota = "frasco 3 mL, medir com paquímetro"

[medidas.cup_diameter]
valor = 99.0
origem = "projeto"
fonte = "https://makerworld.com/..."
```

- [ ] **Step 1:** Criar `pyproject.toml` (projeto `idea2print`, deps `cadquery`, `trimesh`, `manifold3d`, `matplotlib`; dev `pytest`; script `idea2print = "idea2print.cli:main"`), `LICENSE` MIT, `.gitignore`.
- [ ] **Step 2:** `uv sync` e `uv run python -c "import cadquery, trimesh, manifold3d"` → sem erro. Fixar `requires-python = ">=3.12,<3.13"` e, como marcador de plataforma, `"numba<0.61; sys_platform == 'darwin' and platform_machine == 'x86_64'"`, com comentário de uma linha dizendo o motivo (llvmlite novo sem wheel para Mac Intel).
- [ ] **Step 3: testes que falham** em `tests/test_params.py`:
  - `test_loads_value_origin_source`: arquivo acima → `p.v("cup_diameter") == 99.0`, `p["cup_diameter"].source.startswith("https://")`.
  - `test_estimated_lists_keys`: `p.estimated() == ["vial_diameter"]`.
  - `test_missing_origin_names_key`: `[medidas.x] valor=1` → `ParamError` com `"x"` na mensagem.
  - `test_invalid_origin_rejected`: `origem="chute"` → `ParamError` com `"chute"`.
  - `test_projeto_requires_fonte`: `origem="projeto"` sem `fonte` → `ParamError`.
  - `test_printer_defaults_and_override`: sem `[impressao]` → `bed_mm == (256,256,256)`, `min_wall_mm == 1.2`; com `bed_mm=[180,180,180]` → sobrescreve.
- [ ] **Step 4:** `uv run pytest tests/test_params.py -v` → FAIL (módulo inexistente).
- [ ] **Step 5:** Implementar `idea2print/params.py` com `tomllib`.
- [ ] **Step 6:** `uv run pytest tests/test_params.py -v` → 6 passed.
- [ ] **Step 7:** Commit `feat: params.toml with measurement origin labels`.

### Task 2: Medir malha baixada

**Files:**
- Create: `idea2print/measure.py`
- Test: `tests/test_measure.py`

**Interfaces:**
- Produces: `@dataclass class Section: z: float; width: float; depth: float; inner_diameters: list[float]`
- Produces: `@dataclass class ObjectMeasure: name: str; extents_mm: tuple[float,float,float]; watertight: bool; sections: list[Section]`
- Produces: `@dataclass class MeasureReport: objects: list[ObjectMeasure]; scale_suspect: bool`
- Produces: `measure_file(path: Path, heights: int = 5) -> MeasureReport` (STL, 3MF, OBJ; cada objeto de uma cena medido separado, transformações aplicadas)

`inner_diameters`: na seção plana em altura z, cada buraco do polígono vira o diâmetro do círculo de mesma área. É assim que um porta-copo baixado revela o diâmetro do copo.

- [ ] **Step 1: testes que falham:**
  - `test_cup_holder_inner_diameter`: tubo `trimesh.creation.annulus(r_min=49.5, r_max=53, height=20)` salvo em STL → alguma seção tem `inner_diameters` com valor em `99.0 ± 0.5`.
  - `test_extents`: caixa 10×20×30 → `extents_mm == pytest.approx((10,20,30))`.
  - `test_scale_suspect_tiny`: caixa 2×2×2 → `scale_suspect is True`; caixa 50×50×50 → `False`.
  - `test_3mf_multiple_objects_with_transform`: cena com 2 caixas (10³ e 20³, a segunda transladada +100 mm em X) exportada em 3MF → 2 objetos, extents 10 e 20.
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** Implementar com `trimesh.load(..., force="scene")`, `scene.dump()`, `mesh.section(...).to_planar()`, `polygons_full[i].interiors`. Suspeito: maior extent < 5 ou > 1000.
- [ ] **Step 4:** rodar → 4 passed.
- [ ] **Step 5:** Commit `feat: measure downloaded meshes (extents, sections, inner diameters)`.

### Task 3: Verificação geométrica

**Files:**
- Create: `idea2print/verify.py`
- Test: `tests/test_verify.py`

**Interfaces:**
- Consumes: `PrinterLimits` (Task 1)
- Produces: `@dataclass class Check: name: str; ok: bool; detail: str; level: Literal["error","warning"]`
- Produces: `verify_part(name: str, mesh: trimesh.Trimesh, limits: PrinterLimits) -> list[Check]` — `watertight` (error), `fits_bed` (error; ok se alguma das 6 orientações por eixo cabe), `min_wall` (warning), `overhang` (warning)
- Produces: `check_collisions(meshes: dict[str, trimesh.Trimesh], tol_mm3: float = 1.0) -> list[Check]` — par a par, volume da interseção (engine `manifold`) > `tol_mm3` → error citando o par

`min_wall`: 2.000 pontos amostrados na superfície, espessura por raio interno; reprova se o percentil 2 < `min_wall_mm` (usar `trimesh.proximity.thickness(method="ray")` se existir na versão instalada; senão, raio pela normal invertida com `mesh.ray.intersects_location`). `overhang`: faces com normal para baixo além de `max_overhang_deg`, acima de 0,3 mm da base; avisa se a área somada > 1% da total, informando mm².

- [ ] **Step 1: testes que falham:**
  - `test_closed_box_passes`: caixa 20³ → todos `ok`.
  - `test_open_mesh_reports_not_crashes`: caixa sem uma face → `watertight.ok is False` e os demais checks presentes.
  - `test_too_big_fails_bed`: caixa 300×10×10 → `fits_bed.ok is False`; 250×10×10 → `True`.
  - `test_thin_wall_warns`: caixa oca com parede 0,8 mm → `min_wall.ok is False`, `level == "warning"`.
  - `test_overhang_warns`: "T" (placa 40×40×3 sobre pilar 5×5×20) → `overhang.ok is False`.
  - `test_collision_detected`: duas caixas 10³ sobrepostas 5 mm → 1 error citando os dois nomes; afastadas → nenhum.
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** rodar → 6 passed.
- [ ] **Step 5:** Commit `feat: geometric verification (watertight, bed, wall, overhang, collisions)`.

### Task 4: Exportação e renders

**Files:**
- Create: `idea2print/export.py`, `idea2print/render.py`
- Test: `tests/test_export.py`

**Interfaces:**
- Produces: `to_mesh(shape: cq.Workplane | cq.Shape, tol_mm: float = 0.05) -> trimesh.Trimesh`
- Produces: `export_parts(parts: dict[str, cq.Workplane], out: Path, project: str) -> dict[str, Path]` — `<nome>.stl` e `<nome>.step` por peça + `<project>.3mf` com todas como objetos separados
- Produces: `render_png(meshes: dict[str, trimesh.Trimesh], path: Path, view: Literal["iso","top","front"]) -> Path` (matplotlib Agg, eixos em mm)

- [ ] **Step 1: testes que falham:**
  - `test_stl_step_3mf_written`: peças `a` (caixa 10³) e `b` (cilindro r5 h10) → `a.stl`, `a.step`, `b.stl`, `b.step` e `.3mf` existem.
  - `test_3mf_roundtrip_volume`: recarregar o 3MF → 2 objetos, volume de cada um = STL ± 1%.
  - `test_render_png_nonempty`: PNG > 10 kB.
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** Implementar (`cq.exporters.export` para STEP; `to_mesh` via `tessellate`; 3MF via `trimesh.Scene.export(file_type="3mf")`).
- [ ] **Step 4:** rodar → 3 passed.
- [ ] **Step 5:** Commit `feat: STL/STEP/3MF export and model renders`.

### Task 5: Pipeline `build` + relatório + CLI

**Files:**
- Create: `idea2print/project.py`, `idea2print/report.py`, `idea2print/cli.py`, `tests/fixtures/caixa/params.toml`, `tests/fixtures/caixa/model.py`, `tests/fixtures/colide/` (cópia da caixa com `assembly` colidindo)
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: Tasks 1–4
- Contrato do `model.py` de qualquer projeto:
  - `parts(p: Params) -> dict[str, cq.Workplane]` — peças imprimíveis, cada uma na orientação de impressão
  - `assembly(p: Params) -> dict[str, cq.Workplane]` (opcional) — peças montadas na posição fechada + gabaritos de conteúdo com nome `content_*`
  - `coupons(p: Params) -> dict[str, cq.Workplane]` (opcional) — gabaritos de teste curtos
- Produces: `build_project(project: Path, out: Path | None = None) -> BuildResult`; `BuildResult(checks: list[Check], files: dict[str, Path], report: Path, ok: bool)`; `ok` = nenhum Check `error`; padrão de `out` = `<project>/out`
- Produces: CLI `idea2print build <pasta>` (exit 0 se ok, 1 se houver error), `idea2print measure <arquivo>` (JSON no stdout), `idea2print verify <arquivo.stl>`
- `RELATORIO.md`: tabela das medidas (valor, origem, fonte); seção "Falta medir" com cada `estimada`; resultado de cada Check; lista de arquivos; frase fixa "Geometria verificada por software; teste físico pendente."

- [ ] **Step 1:** Fixture `caixa`: caixa 40×30×20 com furo `hole_diameter` (`estimada`).
- [ ] **Step 2: testes que falham:**
  - `test_build_writes_everything`: `build_project(caixa)` → `ok is True`; STL, STEP, 3MF, PNG iso/top e `RELATORIO.md` existem.
  - `test_report_lists_estimated`: relatório contém "Falta medir" e `hole_diameter`.
  - `test_report_never_claims_ready`: relatório não contém "pronto para imprimir" nem "validado"; contém "teste físico pendente".
  - `test_assembly_collision_fails_build`: fixture `colide` → `ok is False` e o relatório cita o par.
  - `test_cli_exit_code`: `idea2print build tests/fixtures/caixa` → exit 0.
- [ ] **Step 3:** rodar → FAIL.
- [ ] **Step 4:** Implementar (`importlib.util.spec_from_file_location` para carregar `model.py`; verifica cada peça de `parts` e `coupons`; colisões só no `assembly`).
- [ ] **Step 5:** rodar → 5 passed; `uv run pytest -q` → tudo verde.
- [ ] **Step 6:** Commit `feat: build pipeline, report and CLI`.

### Task 6: Estojo — layout e base

**Files:**
- Create: `examples/estojo/params.toml`, `examples/estojo/model.py`
- Test: `tests/test_estojo.py`

**Interfaces:**
- Consumes: contrato do `model.py` (Task 5)
- Produces: `@dataclass class Slot: x: float; y: float; z: float; w: float; d: float; h: float`; `layout(p: Params) -> dict[str, Slot]` no sistema da base (origem no canto interno inferior esquerdo); slots `vial_1`, `vial_2`, `sachets`, `syringe_1`, `syringe_2`, `pack_1`, `pack_2`
- Produces: `outer_size(p) -> tuple[float,float,float]` (L, W, altura da base) **derivado dos slots + parede + folgas**, nunca constante

`params.toml` — todos `estimada`, nota "medir — valor provisório da V1/briefing": `vial_diameter 16.0`, `vial_height 38.1`, `vial_clearance 1.4`, `syringe_body_diameter 8.0`, `syringe_extended_length 168.0`, `syringe_clip_clearance 0.3`, `new_pack_length 171.0`, `new_pack_width 18.0`, `new_pack_thickness 8.0`, `alcohol_sachet_length 60.0`, `alcohol_sachet_width 30.0`, `alcohol_sachet_count 6`, `alcohol_sachet_thickness 2.0`, `wall_thickness 2.8`, `floor_thickness 3.0`, `corner_radius 7.0`, `hinge_pin_diameter 1.75`, `hinge_clearance 0.45`, `latch_clearance 0.3`, `item_gap 3.0`.

Layout (briefing §2): fileira de cima = 2 frascos em pé à esquerda + nicho de sachês à direita; meio = 2 seringas deitadas, paralelas, 2 clips cada; baixo = 2 canais de embalagem lacrada. Comprimento interno = maior entre seringa estendida, embalagem e (frascos + sachês), mais folgas.

- [ ] **Step 1: testes que falham:**
  - `test_slots_do_not_overlap`: nenhum par de slots se intersecta.
  - `test_slots_inside_base_interior`: todo slot cabe no interior da base.
  - `test_size_derived_from_params`: `syringe_extended_length` +20 → L de `outer_size` +20; mudar `vial_height` → muda a altura.
  - `test_base_is_valid_solid`: `to_mesh(parts(p)["base"]).is_watertight`.
  - `test_contents_fit_cavities`: gabaritos `content_*` do `assembly` não colidem com a base.
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** Implementar layout e base. Componentes:
  - cavidades cilíndricas para os frascos;
  - berço com 2 clips em C por seringa (abertura = 0,8 × diâmetro + folga);
  - canais retos para as embalagens;
  - nicho de sachês com rebaixo para o dedo.

  Pode reaproveitar `rbox`/`hollow_shell` da V1 (script da V1, não publicado). Nada da V1 vai para a tampa.
- [ ] **Step 4:** rodar → 5 passed.
- [ ] **Step 5:** Commit `feat(estojo): derived layout and base with all compartments`.

### Task 7: Estojo — tampa lisa, dobradiça e fecho

**Files:**
- Modify: `examples/estojo/model.py`
- Test: `tests/test_estojo.py`

**Interfaces:**
- Produces: `parts(p)` → `base`, `lid` (face externa na mesa), `pin` se o pino for impresso
- Produces: `assembly(p)` → `base`, `lid` na posição fechada, `content_*`
- Produces: `hinge_axis(p) -> tuple[tuple[float,float,float], tuple[float,float,float]]` (ponto, direção) — o mesmo eixo para base e tampa

Dobradiça: barris alternados de base e tampa na traseira, furo `hinge_pin_diameter + hinge_clearance` para pino de filamento (como a V1). Pode trocar por pino impresso se justificar no commit. Fecho: aba flexível na frente da tampa, com dente que encaixa num ressalto da base e folga `latch_clearance`. A mecânica é original: nada da geometria do SnapLock é copiado, porque a licença não foi verificada.

- [ ] **Step 1: testes que falham:**
  - `test_lid_has_no_internal_features`: volume da tampa = casca simples do mesmo contorno + barris + aba (± 2%).
  - `test_same_outline`: silhueta XY da tampa fechada e da base coincidem (diferença de área < 0,5%).
  - `test_closed_no_collision`: `check_collisions(assembly(p))` → nenhum error.
  - `test_hinge_coaxial`: furos dos barris da base e da tampa fechada no mesmo eixo, desvio < 0,05 mm.
  - `test_hinge_swing_clear`: tampa girada 0°, 45°, 90°, 110° em `hinge_axis` não colide com a base.
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** rodar → 5 passed.
- [ ] **Step 5:** Commit `feat(estojo): smooth lid, hinge and snap latch`.

### Task 8: Estojo — gabaritos de teste e build completo

**Files:**
- Modify: `examples/estojo/model.py`
- Test: `tests/test_estojo.py`

**Interfaces:**
- Produces: `coupons(p)` → `coupon_clip` (1 clip, 15 mm), `coupon_hinge` (2 barris + furo do pino), `coupon_latch` (aba + ressalto), `coupon_vial_ring` (anel de 3 mm com o furo do frasco)

- [ ] **Step 1: testes que falham:**
  - `test_coupons_small`: cada coupon cabe em 40 × 40 × 25 mm.
  - `test_full_build_ok`: `build_project("examples/estojo")` → `ok is True`; `outer_size` dentro de 256³; 3MF com `base` e `lid` (+ `pin`).
  - `test_extreme_param_reports_bed_failure`: cópia temporária com `syringe_extended_length = 300` → `ok is False`, `fits_bed` em error, `RELATORIO.md` escrito.
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** Implementar `coupons`.
- [ ] **Step 4:** rodar → 3 passed; `uv run pytest -q` → tudo verde.
- [ ] **Step 5:** `uv run idea2print build examples/estojo` → exit 0. Abrir os PNGs iso/top e conferir: frascos à esquerda em cima, sachês à direita, seringas no meio, embalagens embaixo, tampa lisa.
- [ ] **Step 6:** Commit `feat(estojo): test coupons and end-to-end build` (sem `out/`).

### Task 9: SKILL.md e aceite do caso funcional

**Files:**
- Create: `SKILL.md`, `README.md` (mínimo: o que é, instalar com uv, rodar o exemplo — versão EN+pt-BR completa no Plano 3)

**Interfaces:**
- Consumes: CLI da Task 5

`SKILL.md` — frontmatter `name: idea2print` e `description` com gatilhos ("imprimir em 3D", "3D print", "STL", "modelar peça"). O corpo segue o fluxo do design §7, só com a rota funcional ativa:
1. entrevista curta;
2. pesquisa: *por enquanto*, pedir links e medidas à pessoa e rodar `idea2print measure` nos arquivos que ela baixar;
3. perguntar só o que faltou e gravar cada medida com origem em `params.toml`;
4. imagem conceitual opcional (motor no Plano 3). A imagem nunca define medida;
5. escrever `model.py` no contrato da Task 5, usando `examples/estojo` como referência;
6. `idea2print build`, corrigindo até `ok`;
7. entregar os arquivos e o "Falta medir", repetindo os avisos do design §10 quando o objeto for médico ou alimentar.

Regras fixas:
- nunca pedir senha ou chave no chat;
- nunca usar medida tirada de imagem;
- responder no idioma da pessoa.

- [ ] **Step 1:** Escrever `SKILL.md` e `README.md`.
- [ ] **Step 2:** Criar o symlink `~/.claude/skills/idea2print` apontando para o checkout deste repo. Numa sessão nova do Claude Code, pedir "quero imprimir o estojo do briefing" e seguir a skill até `build ok`.
- [ ] **Step 3:** Conferir a entrega contra o checklist §7 do briefing, item por item, e anotar no `RELATORIO.md` o que depende de medida física.
- [ ] **Step 4:** Commit `feat: SKILL.md and functional-route acceptance (estojo V2)`.
