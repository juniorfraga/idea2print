# Plano 1 — decisões tomadas pelo controlador (rulings)

Extraído do ledger de execução em 07/11/2026. Cada linha: decisão — motivo — custo se errada.

- | T6 vs T7 | T6 testa assembly (content_*) mas T7 é quem "produz" assembly | CONFLITO → Ruling 1 |
- | T7 auto | test_lid_has_no_internal_features por volume ±2% exige forma de referência não definida | AMBÍGUO → Ruling 2 |
- | T9 auto | Step 2 "sessão nova do Claude Code" não é executável por subagente | → Ruling 3 |
- | Regra do mantenedor vs SDD | subagente não pode commitar (config privada) | → Ruling 4 |
- Ruling 1: T6 cria assembly(p) com base + content_*; T7 acrescenta lid fechado — senão T6 não testa encaixe — custo se errado: nenhum.
- Ruling 2: "sem feature interna" = volume da interseção da tampa fechada com o interior da base (contorno interno extrudado em toda a altura) < 1 mm³ — mais robusto que volume ±2% — custo: teste diferente do texto do plano.
- Ruling 3: T9 subagente escreve SKILL.md/README e roda o fluxo seguindo o SKILL.md no exemplo; teste numa sessão nova real é do controlador na verificação final — custo: aceite em 2 passos.
- Ruling 4: implementador NÃO commita; deixa mudanças no working tree; controlador commita após o relatório e antes da revisão (review-package BASE..HEAD) — regra do mantenedor prevalece sobre a skill.
- Ruling 5: re-review escopada dispensada p/ rodada só de Minor — suíte 10/10 é o sinal — custo: minor mal corrigido passa até a revisão final.
- Ruling 6: Path3D/AttributeError promovido de Minor a Important — arquivo baixado real é o propósito do módulo — custo: 1 teste a mais.
- Ruling 7: incluir no fix o warning do trimesh (AABB) e min_wall com <50% amostras válidas → reprova — saída limpa e anti-falso-pass — custo: diff maior na rodada.
- Ruling 8: levar à Task 5 — to_mesh/export usar todos os sólidos (shape.val() trunca multi-sólido = exportação silenciosamente incompleta), render_png guardar dict vazio e criar pasta — custo: Task 5 um pouco maior.
- Ruling 9: build deve limpar out/ no início — STL antigo ao lado de relatório de erro pode ser impresso por engano (anti-objetivo) — levado à Task 6.
- Ruling 10: clips só no corpo (params syringe_cap_length/syringe_barrel_length, estimada) — segurança do briefing — custo: 2 params a mais.
- Ruling 11: cor por peça e sem arestas no render entra nesta rodada (implementador quente) em vez da onda final — custo: rodada maior.
- Ruling 12: re-review escopada dispensada na rodada só-doc da Task 9 — conferência por grep das 5 frases — custo: frase ruim passa até revisão final.
- Ruling 13: onda final inclui findings 1-7 e 9; finding 8 (BoundingBox de 1 sólido) adiado — lid hoje é 1 sólido — custo: zmin errado se a tampa virar multi-sólido.
- Ruling 14: 3MF em fila tem 503.7 mm de largura (> mesa 256) — base+tampa não cabem numa placa mesmo; usuário usa Arrange/várias placas no slicer; 3MF com placas da Bambu fica para o Plano 3 — custo: passo manual no slicer.

## Pendências conhecidas (para o Plano 3 / backlog)
- Task 2: minor (deferred): cena vazia → scale_suspect True sem doc; nomes 3MF caem em object_{i} sem teste; min versions networkx/lxml no pyproject não conferidas
- Task 2: minor (deferred): índice object_{i} avança em item pulado (cosmético)
- Task 3: minor (deferred): overhang em malha degenerada não provado; min_wall só testado em caixas
- Task 3: minor (deferred): ramo min_wall<50% sem teste; open_names em set (ordem não determinística); boolean manifold pode levantar em par não-manifold → levar à Task 5 (build captura e vira error Check)
- Task 4: minor (deferred): merge_vertices redundante; STEP não recarregado em teste; render test fraco (só tamanho); zero extent em set_box_aspect
- Task 5: minor (deferred): model.py ausente → AttributeError em vez de FileNotFoundError; cli verify usa PrinterLimits padrão; '|' em fonte quebra tabela; assert 'caixa' trivial no teste de colisão
- Task 6: minor (deferred): _interior do teste derivado de outer_size (auto-referente); flex do clip 0,8D não validado (gabarito físico na Task 8); render mostra arestas de triângulos
- Task 6: minor (deferred): clip deslocado mas sobrepondo a faixa não pego; pasta chamada x.png em out quebra o build sem relatório; case-insensitive macOS no guard
- Task 7: minor (deferred): teste de orientação da tampa frouxo; aba sem teste de flexão (só físico); folga radial da dobradiça só pela tolerância de colisão
- Task 7: minor (deferred): hipotenusa do gusset externo = balanço 1,5 mm; união coplanar dos gussets depende do manifold
- Task 8: minor (deferred): troca do TOML por replace de string no teste extremo (frágil mas falha alto); coupon de dobradiça sem pino
- Aceite (agente novo via skill instalada): build exit 0, entrega completa (arquivos, cupons primeiro, 18 'falta medir', pino 60 mm, segurança); notas: warnings do terminal sem nome da peça, [AVISO]/[warning] idioma misto, coluna fonte mostra nota, 'count' em 'medir', build >2 min
