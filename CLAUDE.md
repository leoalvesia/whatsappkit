# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Documentação e código deste projeto são em português (pt-BR). Mantenha esse idioma em comentários, logs e mensagens ao usuário.

## O que é este repositório

Plugin **`whatsapp-manager`** (v1.1) para o **Hermes Agent v2026** — não é uma aplicação autônoma. Não existe entrypoint local: nada de `npm start`. O código é instalado dentro do container do Hermes, que carrega `whatsapp_manager.py` e chama `register(ctx)` (final do arquivo) para registrar hooks. Deploy é via docker-compose no Portainer/Swarm ou EasyPanel.

Licença **BUSL-1.1** (Licensor: André Alencar, Change Date 2031-06-25 → MIT). Copiar/modificar/redistribuir é permitido; o Additional Use Grant limita o uso a "development, evaluation, and personal testing" — uso em produção exige licença comercial do autor.

## Comandos

```bash
npm install                                   # deps do bridge (package-lock.json é gitignorado de propósito)
npm test                                      # suíte completa: node --test tests/bridge.test.js && python3 -m unittest tests/plugin_test.py
python3 -m unittest tests/plugin_test.py      # só Python (311 testes, 48 classes)
node --test tests/bridge.test.js              # só o bridge
python3 validate_dedup.py                     # validação de dedup (roda dentro do container)
```

Rodar um único teste ou classe:

```bash
python3 -m unittest tests.plugin_test.TestSalesDetection
python3 -m unittest tests.plugin_test.TestSalesDetection.test_find_product_matches_partial_keyword
```

**Requer Python ≥ 3.12.** `whatsapp_manager.py` usa f-strings com backslash na parte de expressão (PEP 701); em 3.11 o arquivo nem compila.

**A suíte tem efeitos colaterais reais.** Importar `whatsapp_manager` dispara `register()`, que escreve em `/opt/data/.hermes/...` e faz requisições HTTP ao GitHub no boot. Fora do container Linux isso cria diretórios no host (em Windows, `C:\opt\data`). Os testes assumem paths POSIX — em Windows, asserts de path (`/opt/data/...` vs `\opt\data\...`) falham por diferença de separador, sem ser bug real. Rode a suíte no container ou em Linux.

Scripts de diagnóstico ficam em `deploy/scripts/` (`diagnose_bridge_dedup.py`, `diagnose_native_whatsapp_conflict.sh`, `capture_logs.sh`, `test_*.py` avulsos que não fazem parte de `npm test`).

## Arquitetura

### Divisão plugin × core (importante e contraintuitivo)

Desde o Hermes Agent v0.19 ("Quicksilver"), o **core** (`hermes_plugins.whatsapp_platform`) é dono do ciclo de vida do processo Node: spawn, pidfile com detecção de PID reciclado, restart em crash, e parsing das mensagens recebidas. Este plugin **não spawna mais o `bridge.js`** — `register()` apenas copia o arquivo para `/opt/data/.hermes/platforms/whatsapp/bridge/` para o core encontrar. Isso eliminou o container duplicado e o erro de desconexão `440 conflict / replaced`. Toda a regra de negócio fica nos hooks Python.

### Os hooks (`whatsapp_manager.py`, ~7.200 linhas)

| Hook | Linha | Responsabilidade |
|---|---|---|
| `pre_gateway_dispatch` | ~5485 | O maior. Roteia dono × cliente, executa comandos de controle, update de contato em linguagem natural, catálogo de produtos e registro de vendas |
| `pre_llm_call` | ~6730 | Detecta pergunta cross-session ("o que a Isabel falou sobre X?") e injeta histórico de `whatsapp_messages.db` + `state.db` no contexto |
| `pre_tool_call` | ~7017 | Firewall: aborta qualquer chamada de ferramenta vinda do perfil `whatsapp` (clientes) |
| `post_llm_call` | ~7048 | Suprime avisos do sistema (reset de 24h, metadados `◆ Model: ...`) |
| `register` | ~7211 | Instala `bridge.js` no volume, migra a sessão Baileys do path antigo, inicializa SOULs e `personal_contacts.json` |

### Dois perfis de isolamento

- **`default`** — dono, no SelfChat. Persona `SOUL.md`, histórico completo, todas as ferramentas.
- **`whatsapp`** — clientes. Persona `SOUL_WHATSAPP.md` + `support_rules.md`, `toolsets: []`, todas as 25 famílias de ferramentas desativadas, `skills.enabled: false`. `pre_tool_call` é a segunda camada, no backend.

### Pausa global × silêncio por chat (não confundir)

São mecanismos distintos, em camadas diferentes:

- **Pausa global** — `stop_bot` / `start_bot` (sinônimos `!pausar`, `!retomar`, `!parar`, `!iniciar`). Aplicada no Node (`bridge.js`), persistida em `bot_state.json` dentro de `SESSION_DIR`. Descarta na origem mensagens de qualquer um que não seja o dono. **Só funciona se enviada pelo dono no self-chat** — digitar na conversa de cliente não faz nada.
- **Silêncio de 10 min** (`WHATSAPP_SILENCE_DURATION_MIN`) — por chat individual. Dois gatilhos: o dono **lê** a conversa (detectado por `chats.update` quando não-lidas cai para `0`/`-1`), ou o dono **envia mensagem manual** (`fromMe: true` e o id não está em `recentlySentIds`). Mensagens começando com `!` ou comandos de controle não disparam o silêncio.

`DESIGN.md` tem o fluxograma completo em Mermaid.

### Volume `/opt/data` — persistente × efêmero

Persistem: `.hermes/platforms/whatsapp/session/` (creds Baileys), `.hermes/whatsapp_messages.db`, `.hermes/state.db`, `personal_contacts.json`, `support_rules.md`, `SOUL*.md`.

**É wipeado em rebuild:** `.hermes/platforms/whatsapp/bridge/bridge.js`. Editar o `bridge.js` do volume é inútil — edite `bridge.js` na raiz do repo, que é o que `register()` copia para lá.

### Sync de contatos

`personal_contacts.json` é versionado num repositório GitHub privado (`CONFIG_REPO`, default `hermes_agent_context_contatcs`). O sync roda sempre em thread daemon via `_run_sync_in_background` — **nunca no boot**, só no intervalo periódico (`WHATSAPP_SYNC_INTERVAL_HOURS`) ou por comando no chat. Contatos são classificados por LLM em `Cliente | Amigo | AmigoProximo | Parente | Filho | Vendedor`; o campo `notes` entra no prompt como instrução obrigatória; `full_summary` acumula por sessão e é comprimido em `summary` quando fica longo. Campos auto-gerados (`tone`, `summary`, `guidelines`) não são sobrescritos por update manual.

## Armadilhas de arquivo duplicado

O mesmo arquivo existe em vários caminhos — edite o certo:

- `bridge.js` (raiz, 77 KB) é a **fonte da verdade**. `docs/bridge-artifacts/bridge.js` e `deploy/docs/bridge-artifacts/bridge.js` (63 KB) são artefatos defasados.
- `google_api.py` existe na raiz e em `deploy/scripts/google_api.py`.
- `skills/whatsapp-logs-diagnostics/SKILL.md` está duplicado em `deploy/skills/`.

## Grafo de conhecimento (graphify)

`graphify-out/` está commitado (grafo + cache AST + `GRAPH_REPORT.md`). `GEMINI.md` e `.agents/rules/graphify.md` mandam usar `graphify query "<pergunta>"` antes de grepar, `graphify path "<A>" "<B>"` para relações e `graphify explain "<conceito>"`; e `graphify update .` após mudar código. Verifique se o CLI `graphify` existe antes de depender disso — sem ele, `GRAPH_REPORT.md` ainda serve para visão de arquitetura.

## Ao replicar este kit para outro cliente

O repositório está costurado com dados do autor original. Antes de subir uma instância para outro cliente, troque:

- **`HERMES_SETUP_GITHUB_USER`** (ou `DEV_GITHUB_USER`) — o plugin baixa código e personas de `https://raw.githubusercontent.com/$USER/hermes-whatsapp-mixed/main/...` em runtime e se auto-atualiza a partir dali. O default é `empreendedorserial` em ~10 pontos de `whatsapp_manager.py` e em `deploy/setup.sh:83`. Sem trocar, a instância do cliente puxa código do repositório original e sobrescreve customizações. Atenção: `whatsapp_manager.py:7347` tem a URL **fixa** com `empreendedorserial`, ignorando a variável.
- `WHATSAPP_OWNER_NUMBER` / `WHATSAPP_OWNER_NAME` / `WHATSAPP_CONNECTION_NAME` — `deploy/.env.example` vem com o número real do autor.
- `CONFIG_REPO` + `CONFIG_GITHUB_TOKEN` — repositório privado de contatos, um por cliente.
- `GOOGLE_API_KEY` e os `WHATSAPP_*_MODEL`.
- `deploy/SOUL.md`, `deploy/SOUL_WHATSAPP.md`, `deploy/SOUL_EMAIL.md`, `deploy/support_rules.md`, `deploy/personal_contacts.json.example`.
- O nome "André" aparece hardcoded em ~69 pontos de `whatsapp_manager.py` (prompts e o nome da função `_collect_andre_messages_by_relationship`) e em ~30 outros arquivos.

## Pareamento e status

Após subir o container: `/whatsapp/qr` (tela HTML), `/whatsapp/qr?format=png`, `/whatsapp/status` (JSON). O bridge sobe na porta 3000; `adapter.py` (`WhatsAppPlatformAdapter`) conversa com ele por HTTP via `WHATSAPP_BRIDGE_URL`. Endpoints extras já implementados no bridge: `POST /send-poll`, `POST /send-location`.
