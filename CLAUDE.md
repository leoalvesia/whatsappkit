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
python3 -m unittest tests/plugin_test.py      # só Python (312 testes, 49 classes)
node --test tests/bridge.test.js              # só o bridge (23 asserções; o processo
                                              # não encerra sozinho: importar bridge.js
                                              # sobe o Express na 3000)
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

`personal_contacts.json` **pode** ser versionado num repositório GitHub privado (`CONFIG_REPO` + `CONFIG_GITHUB_TOKEN`) — é opcional. Sem os dois, o plugin nem tenta o push e não avisa o dono. O sync roda sempre em thread daemon via `_run_sync_in_background` — **nunca no boot**, só no intervalo periódico (`WHATSAPP_SYNC_INTERVAL_HOURS`) ou por comando no chat. Contatos são classificados por LLM em `Cliente | Amigo | AmigoProximo | Parente | Filho | Vendedor`; o campo `notes` entra no prompt como instrução obrigatória; `full_summary` acumula por sessão e é comprimido em `summary` quando fica longo. Campos auto-gerados (`tone`, `summary`, `guidelines`) não são sobrescritos por update manual.

## Armadilhas de arquivo duplicado

O mesmo arquivo existe em vários caminhos — edite o certo:

- `bridge.js` (raiz, 77 KB) é a **fonte da verdade**. `docs/bridge-artifacts/bridge.js` e `deploy/docs/bridge-artifacts/bridge.js` (63 KB) são artefatos defasados.
- `google_api.py` existe na raiz e em `deploy/scripts/google_api.py`.
- `skills/whatsapp-logs-diagnostics/SKILL.md` está duplicado em `deploy/skills/`.

## Deploy de alterações

O runbook completo está em `.gemini/skills/deploy-plugin/SKILL.md` (escrito para o Gemini CLI, mas o procedimento é agnóstico): commit e push no `main` → botão **Pull** do plugin na aba *Plugins* do Dashboard do Hermes → **Restart** do container no Portainer → conferir `grep "whatsapp-manager" /opt/data/.hermes/logs/hermes.log | tail -20` procurando por `bridge.js atualizado` → testar com `stop_bot` no WhatsApp. Alterações no plugin só carregam após o restart. `bot_state.json` sobrevive ao restart.

## Grafo de conhecimento (graphify)

`graphify-out/` está commitado (grafo + cache AST + `GRAPH_REPORT.md`). `GEMINI.md` e `.agents/rules/graphify.md` mandam usar `graphify query "<pergunta>"` antes de grepar, `graphify path "<A>" "<B>"` para relações e `graphify explain "<conceito>"`; e `graphify update .` após mudar código. Verifique se o CLI `graphify` existe antes de depender disso — sem ele, `GRAPH_REPORT.md` ainda serve para visão de arquitetura.

## Ao replicar este kit para outro cliente

Tudo o que muda por cliente é **variável de ambiente**. Não edite código para trocar de cliente — se você se pegar fazendo isso, é sinal de que falta parametrizar algo.

| Variável | Para que serve |
|---|---|
| `WHATSAPP_OWNER_NAME` | Nome do dono nos prompts, via `_owner_name()`. `_owner_name_norms()` e `_is_owner_name()` derivam dele as variações usadas para reconhecer as mensagens do dono no histórico |
| `WHATSAPP_OWNER_NUMBER` | Número sem `+`. Também lido pelo `bridge.js` |
| `WHATSAPP_PIX_KEY` | Chave Pix quando o item do catálogo não define a sua. **Sem default de propósito** — errar aqui manda o pagamento do cliente para a conta errada |
| `OPENROUTER_API_KEY` | Provider padrão. Deixe `GOOGLE_API_KEY` e `OPENAI_API_KEY` **vazias**: a cadeia é Google → OpenAI → OpenRouter e para na primeira chave preenchida |
| `WHATSAPP_*_MODEL` / `*_PROVIDER` | Slugs do OpenRouter (`vendor/modelo`). Texto usa `deepseek/deepseek-v4-flash`; mídia precisa de modelo multimodal (`google/gemini-3.1-flash-lite`) porque o DeepSeek aceita só texto |
| `CONFIG_REPO` + `CONFIG_GITHUB_TOKEN` | Opcional — versiona contatos e personas num repo privado |
| `HERMES_SETUP_GITHUB_USER` | Dono do repositório de onde o plugin se atualiza |

Fora as envs, só os arquivos de conteúdo: `deploy/SOUL.md`, `SOUL_WHATSAPP.md`, `SOUL_EMAIL.md` e `support_rules.md` são **templates com placeholders `{{...}}`**. Preencha antes de subir — placeholder não substituído vai literal para o cliente, e um `support_rules.md` com produto errado faz o bot inventar oferta que não existe.

**Ainda embutem o nome do repositório:** `whatsapp_manager.py:3788, 3804, 7347, 7378, 7439` e `deploy/setup.sh:83`. E `whatsapp_manager.py:7347` embute a URL **inteira**, ignorando `HERMES_SETUP_GITHUB_USER` — um cliente com outro usuário GitHub precisa de patch nessa linha.

## Como o código chega na VPS

O `command:` do `deploy/docker-compose.easypanel.yml` faz `git clone` (ou `fetch` + `reset --hard`) do repositório a cada boot. Fluxo de atualização: `git push` na `main` → restart do serviço no EasyPanel.

Duas decisões deliberadas nesse bloco:
- **É clone, não download de arquivos avulsos.** O `setup.sh` original baixava 9 arquivos individuais e não criava `.git`, o que fazia `_self_update_plugin_code()` cair no fallback de lista fixa — arquivos novos nunca chegavam.
- **O perfil de isolamento é escrito pelo compose, não pelo repositório clonado.** Se o clone falhar, o container sobe seguro em vez de liberar terminal e leitura de arquivos para quem manda mensagem.

## Pareamento e status

Após subir o container: `/whatsapp/qr` (tela HTML), `/whatsapp/qr?format=png`, `/whatsapp/status` (JSON). O bridge sobe na porta 3000; `adapter.py` (`WhatsAppPlatformAdapter`) conversa com ele por HTTP via `WHATSAPP_BRIDGE_URL`. Endpoints extras já implementados no bridge: `POST /send-poll`, `POST /send-location`.
