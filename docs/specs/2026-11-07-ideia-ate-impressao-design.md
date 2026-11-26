# idea2print — da ideia ao arquivo de impressão (design)

**Data:** 07/11/2026 · **Status:** aprovado pelo mantenedor em 07/11/2026 · **Nome do projeto:** `idea2print` · **Licença:** MIT

## 1. Intenção

Muita gente tem impressora 3D e não sabe modelar. O projeto é um **repositório open source no GitHub** que transforma uma ideia em linguagem natural em um arquivo pronto para imprimir, usando o agente de IA que a pessoa já tem (Claude Code, Codex, Gemini CLI / Antigravity).

Primeiro caso real, que serve de teste de aceitação: o **estojo de frascos/seringas** descrito no briefing original do estojo (não publicado).

Público: **global** — documentação e mensagens em **inglês + pt-BR**.

## 2. Objetivos

1. Conduzir a pessoa da ideia ao arquivo: entrevista → pesquisa → imagem conceitual → modelo 3D → verificação → arquivos.
2. **A pesquisa responde medidas.** Antes de perguntar uma medida, procurar em projetos existentes (ex.: porta-copo de um copo Stanley específico → um projeto no MakerWorld já traz o diâmetro). Só perguntar o que a pesquisa não resolveu.
3. Cobrir **peças funcionais** (caixas, suportes, organizadores — CAD paramétrico) **e orgânicas** (bonecos, decoração — malha gerada por IA a partir de imagem), e a mistura das duas.
4. **Vários motores por etapa, à escolha da pessoa**, com um assistente de instalação guiado que abre a página certa, ensina o passo a passo, testa e salva a escolha.
5. Funcionar em mais de um agente com o mesmo repositório.

## 3. Não-objetivos (V1)

- App com tela própria (site/desktop) e servidor MCP próprio.
- Fatiar automaticamente (gerar G-code) — a pessoa fatia no slicer dela.
- Perfis de impressão para várias impressoras — V1 entrega STL/3MF genérico + exemplo Bambu Lab A1.
- Publicar no MakerWorld/Printables.

## 4. Anti-objetivos (fracasso mesmo que "funcione")

- Tirar cotas da imagem gerada por IA (a imagem é referência visual, nunca desenho técnico — erro da V1 do estojo).
- Declarar "pronto para imprimir" sem verificação geométrica, ou "validado" sem teste físico.
- Redistribuir geometria de terceiros sem licença que permita.
- O agente pedir, digitar ou guardar senha de qualquer site.
- Travar o fluxo quando um motor falha, em vez de oferecer o próximo.

## 5. Restrições

- Máquina de desenvolvimento: Mac Intel i5-8500, 32 GB, **sem GPU dedicada** → modelos imagem→3D (TRELLIS, Hunyuan3D) não rodam localmente; só na nuvem.
- Python 3.13 + `uv` disponíveis; CadQuery/trimesh ainda não instalados.
- Mesa da Bambu A1: 256 × 256 × 256 mm (limite de verificação padrão, configurável).
- Login em sites (MakerWorld etc.) é sempre feito pela pessoa no navegador dela; a skill usa a sessão já aberta.
- Chaves e tokens ficam no computador da pessoa (config do usuário / variável de ambiente), nunca no repositório.

## 6. Abordagens consideradas

| Opção | Resumo | Trade-off | Decisão |
|---|---|---|---|
| **A. Skill + scripts Python** | `SKILL.md` (formato aberto Agent Skills) conduz a conversa; scripts fazem CAD, malha, verificação, export | menor esforço; mesmo repo serve vários agentes; cada agente interpreta a skill do seu jeito | **escolhida pelo mantenedor** |
| B. Servidor MCP | ferramentas como funções chamáveis por qualquer agente | mais padronizado, ~2× código | depois, se a comunidade pedir (scripts viram MCP sem reescrever) |
| C. App próprio com tela | site local com chat e visualizador 3D | funciona sem agente, mas exige IA própria paga e muito mais trabalho | fora |

Instalação proposta: `npx skills add <usuario>/<repo>` (CLI do ecossistema Agent Skills; diz suportar Claude Code, Codex e outros — suporte a Gemini/Antigravity **a confirmar** no build).

## 7. Fluxo da skill (decidido)

1. **Entrevista curta:** o que é, para que serve, o que vai dentro/em cima, impressora e material.
2. **Pesquisa** (MakerWorld, Printables, Thingiverse): projetos parecidos, licença, e **medidas** — tiradas da descrição do projeto ou medidas na própria malha baixada (ex.: diâmetro da cavidade de um porta-copo). Download só com OK da pessoa.
3. **Perguntas de medida** só do que a pesquisa não resolveu. Cada medida leva etiqueta de origem: `informada` · `de projeto (link)` · `estimada`.
4. **Imagem conceitual** + rodadas de ajuste até a pessoa aprovar.
5. **Rota de modelagem:**
   - funcional → CadQuery paramétrico (todas as medidas num arquivo de parâmetros);
   - orgânica → malha por IA a partir da imagem, depois conserto, escala real, base plana;
   - híbrida → malha orgânica unida a encaixe funcional medido.
6. **Verificação automática:** malha fechada/manifold, colisões em montagens (ex.: tampa fechada), cabe na mesa, paredes mínimas.
7. **Entrega:** STL por peça, STEP (rota funcional), 3MF, renders gerados **do modelo** (não de IA), gabaritos de teste curtos (clip, pino, fecho, anel de diâmetro), README com medidas e o que falta medir.

Medida vinda de projeto de terceiros → a skill sugere imprimir antes um gabarito fino (ex.: anel de 3 mm) para conferir.

## 8. Motores por etapa (decidido: vários, à escolha)

| Etapa | Motores | Observação |
|---|---|---|
| Imagem conceitual | Google Flow via flow-mcp · chave Gemini API · gerador nativo do agente · foto/rascunho da pessoa | imagem nunca define medida |
| Malha orgânica | Hugging Face Spaces grátis (TRELLIS.2 / Hunyuan3D-2.1 via `gradio_client`) · chave Meshy/Tripo (~US$0,10–0,30/modelo, a confirmar) · "traga sua malha" | Spaces podem dormir/quebrar e têm cota → cair no próximo |
| Pesquisa | MakerWorld (login no navegador) · Printables · Thingiverse | sem senha no agente |
| CAD funcional | CadQuery local (sempre) | instalado pelo assistente via `uv` |

**Assistente de instalação (1ª execução e sob demanda):** para cada motor escolhido, abre a URL exata (cadastro, página do token), mostra os cliques um a um, testa a conexão, grava a escolha. Se um motor falha em uso, oferece o próximo da lista.

## 9. Integração com o flow-mcp (decidido)

- Repositório de outro desenvolvedor: [GTAI-1/flow-mcp](https://github.com/GTAI-1/flow-mcp). **Não copiamos código**: o assistente instala do upstream num **commit fixado e auditado**, com crédito ao autor no README.
- **Licença:** `package.json` declara ISC, mas o repositório não tem arquivo LICENSE → abrir issue pedindo; até lá, só referência.
- Instalar com `npm ci --ignore-scripts` (3 dependências com script de instalação: onnxruntime-node, sharp, protobufjs).
- Avisos no README: automação do site do Google via Chrome (risco de bloqueio → usar conta Google separada, sem vínculo com negócio); exige plano Google AI Pro; Flow em inglês; quebra quando o Google muda a tela; porta CDP 9333 sem autenticação (qualquer processo local alcança a sessão enquanto o Chrome está aberto).
- Estado na máquina do autor (07/11/2026): atualizado para `1d17b7b`, patch local reaplicado, conhece "Nano Banana 2" e "Nano Banana Pro"; o Flow agora mostra também "Nano Banana 2 Light" e "2.1" — seleção por nome a conferir no build.

## 10. Segurança e uso (herdado do briefing do estojo)

Peça FDM não é estéril nem controla temperatura; nada de projetar para reutilizar seringa/agulha usada; travas não podem pressionar êmbolo. A skill repete esses avisos quando o objeto é de uso médico/alimentar.

## 11. Deixado para o construtor

Estrutura de pastas, nomes dos scripts, formato do arquivo de config (proposta: TOML em `~/.config/idea2print/`), biblioteca para 3MF e para renders, organização dos testes, ordem de implementação.

## 11b. Decisões tomadas pelo Claude após revisão de construtor (a conferir pelo mantenedor)

1. **Interface:** `SKILL.md` conduz; scripts rodam por `uv run scripts/<x>.py` a partir da raiz da skill. Agente sem suporte a skills → `AGENTS.md` no repo apontando para o `SKILL.md`.
2. **Assistente de instalação = roteiro que o agente executa passo a passo** (não script interativo).
3. **Segredos:** o agente nunca vê chave. Ele abre o arquivo de config local (ou a página do token) e a pessoa cola a chave lá; scripts leem de config/variável de ambiente.
4. **Pesquisa sem navegador automatizável:** Printables/Thingiverse por API pública; MakerWorld só com navegador; sem navegador, a pessoa cola links e a skill segue.
5. **Medir malha baixada (V1):** caixa externa + cortes transversais em alturas (trimesh) mostrados para a pessoa confirmar. Sem ajuste automático de cilindro.
6. **3MF válido:** reabre sem erro numa biblioteca 3MF e bate com o STL (volume/caixa). Metadados específicos da Bambu são opcionais; conferência no Bambu Studio é manual.
7. **Estojo V1:** sai com parâmetros provisórios rotulados (o briefing permite); medidas reais antes da impressão definitiva. Insumos do kit disponíveis.
8. **Etiqueta de origem:** arquivo de parâmetros TOML com `valor`, `origem` (`informada|projeto|estimada`) e `fonte` (link). Verificador **avisa** (não bloqueia) em `estimada`; README lista todas.
9. **Limiares padrão:** parede mínima 1,2 mm, balanço 45°, configuráveis por material/bico.
10. **Testes:** CI cobre CAD, malha e verificação; motores externos (Flow, Spaces, Meshy) só com mocks + teste de contrato, e smoke test manual.

## 12. Decidido em 07/11/2026

- Nome: **idea2print** (livre no GitHub e no PyPI na data).
- Licença: **MIT**. Peças geradas pertencem a quem gerou; modelos de terceiros seguem a licença de cada autor (a skill mostra na pesquisa).
- Repositório na conta GitHub do mantenedor (a criar).

## 13. Critério de pronto da V1

**Decisão do mantenedor (07/11/2026): as três rotas (funcional, orgânica, híbrida) entram na V1.** A V1 só está pronta quando os três casos abaixo saem pela própria skill:

1. **Funcional — estojo V2:** atende os critérios de aceitação do briefing (§7 do briefing): tudo na base, tampa lisa, sem colisões na montagem CAD, STL/STEP/3MF + fonte paramétrica + renders + gabaritos, e lista explícita do que ainda precisa ser medido fisicamente.
2. **Orgânica:** um objeto de exemplo (proposta do Claude: miniatura/boneco de ~8 cm a partir de imagem aprovada) gerado por **pelo menos um motor real** (Hugging Face Space, ou "traga sua malha" com arquivo gerado fora), depois consertado, escalado para a medida pedida, com base plana, aprovado na verificação e exportado em STL + 3MF. Se nenhum Space grátis estiver de pé no momento do teste, registrar e usar "traga sua malha" — a rota não pode depender de um único serviço.
3. **Híbrida:** a malha do caso 2 unida a um encaixe funcional medido (proposta: base com furo para um item de medida conhecida), aprovada na verificação.
