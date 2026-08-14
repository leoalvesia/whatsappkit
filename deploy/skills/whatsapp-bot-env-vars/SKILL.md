---
name: whatsapp-bot-env-vars
description: Sistema WhatsApp Bot completo — dual-mode (assistente pessoal + suporte a clientes) com histórico de conversas persistence via SQLite
category: devops
---

# WhatsApp Bot — Sistema Completo

## Arquitetura

```
WhatsApp (Baileys)
    ↓
bridge.js (porta 3000, loopback)
    ↓ POST /messages
whatsapp_message_server.py (porta 18732, loopback)
    ↓ SQLite INSERT
whatsapp_messages.db (30 dias retention)
    ↓ GET /chat/:id/messages
whatsapp-manager (plugin gerenciado pelo dashboard do Hermes)
    ↓ injeta contexto
pre_gateway_dispatch → reescreve mensagem com histórico
pre_llm_call → aplica persona (Modo A = André, Modo B = Cliente)
```

**Dois processos NÃO supervisionados pelo s6** — iniciados manualmente ou pelo gateway:

| Processo | Porta | Comando |
|---|---|---|
| WhatsApp bridge (Node.js) | 3000 | `node /opt/data/.hermes/platforms/whatsapp/bridge/bridge.js --port 3000 --session /opt/data/.hermes/platforms/whatsapp/session --mode bot` |
| Message server (Python) | 18732 | `bash /opt/data/start_whatsapp_message_server.sh` |

## Dual-Mode (comportamento)

**Modo A — Mensagens do DONO (André):**
- Hook `pre_llm_call` injeta contexto de assistente pessoal
- Ferramentas disponíveis (terminal, files, etc.)
- Modelo: `WHATSAPP_OWNER_MODEL` (default: `gemini-3.5-flash`)

**Modo B — Mensagens de CLIENTES:**
- Hook `pre_gateway_dispatch` reescreve mensagem: `{history}\n\n[ Nova mensagem do cliente ]\n{texto}`
- Hook `pre_llm_call` injeta persona de suporte + SOUL_WHATSAPP.md + support_rules.md
- Ferramentas DESABILITADAS para clientes (nenhum terminal/arquivos)
- Modelo: `WHATSAPP_CLIENT_MODEL` (default: `gemini-3.5-flash`)
- Delay: `WHATSAPP_FIRST_RESPONSE_DELAY_S` segundos (default: 30)

## Arquivos Principais

| Arquivo | Papel |
|---|---|
| `/opt/data/.hermes/scripts/whatsapp_message_server.py` | HTTP server — POST /messages (salva), GET /chat/:id/messages (busca) |
| `/opt/data/.hermes/scripts/whatsapp_message_history.py` | Módulo SQLite — save_message, get_chat_history, format_history_for_context |
| `/opt/data/.hermes/plugins/whatsapp-manager/__init__.py` | Plugin com hooks pre_gateway_dispatch e pre_llm_call (instalado/atualizado pelo dashboard do Hermes) |
| `/opt/data/.hermes/whatsapp_messages.db` | SQLite com 30 dias de retention |
| `/opt/data/start_whatsapp_message_server.sh` | Script de start do message server |
| `/opt/data/.hermes/platforms/whatsapp/bridge/bridge.js` | Bridge Baileys (NÃO edite — é wipeado em rebuild) |

**IMPORTANTE:** `bridge.js` está em `/opt/data/.hermes/` (persistente), NÃO em `/opt/hermes/scripts/` (efêmero). O bridge sobrevive a rebuilds do container porque foi instalado/copiado para o volume persistente.

## Onde as Variáveis são Lidas

### 1. `WHATSAPP_OWNER_NUMBER` (CRÍTICA)
**Onde configurar:** Portainer → Stack → Environment Variables

| Ambiente | Valor |
|---|---|
| Produção (Portainer) | `5586981612061` (setado na stack) |
| Docker-compose fallback | `${WHATSAPP_OWNABLE_NUMBER:-5586981612061}` |

**O que faz:** Número do dono (André). O plugin `whatsapp-manager` — gerenciado pelo dashboard do Hermes — usa essa variável para decidir se uma mensagem é do dono (comportamento admin) ou de um cliente (comportamento suporte).

**Importante:** Não é lida do `.env` — é definida diretamente nas env vars da stack no Portainer.

---

### 2. `HERMES_HOME`
**Onde configurar:** Portainer → Environment Variables da stack

| Padrão | Valor atual |
|---|---|
| `~/.hermes` | `/opt/data/.hermes` |

**O que faz:** Define onde o Hermes armazena configurações, plugins, banco SQLite e logs.

**Importante:** Quando setada, sobrepõe `Path.home() / ".hermes"`. O plugin discovery usa `get_hermes_home() / "plugins"`.

---

### 3. `WHATSAPP_HOME_CHANNEL`
**Onde configurar:** Portainer → Environment Variables

**O que faz:** Define o canal padrão pra onde mensagens são enviadas.

---

## Arquivos de Configuração

### Docker-compose (`/opt/data/workspace/hermes-whatsapp-mixed/docker-compose.yml`)
Template da stack. Variáveis SEM fallback hardcoded — o valor real vem só do Portainer:
```yaml
environment:
  - WHATSAPP_OWNER_NUMBER=${WHATSAPP_OWNER_NUMBER}
  - HERMES_HOME=${HERMES_HOME:-/opt/data/.hermes}
```

**Nunca coloque fallback com número real no docker-compose.** Tokens e credenciais também não devem aparecer no repo — use variáveis de ambiente externas.

### Plugin (`/opt/data/.hermes/plugins/whatsapp-manager/__init__.py`)
Lê variáveis com `os.getenv()`. Se `WHATSAPP_OWNER_NUMBER` vier vazia, o plugin retorna `None` prematuramente e **não injeta histórico**.
O arquivo do plugin é instalado/atualizado pelo dashboard do Hermes, não pelo `setup.sh`.

### `.env` (`/opt/data/.env`)
Arquivo local de desenvolvimento. **Não é usado em produção** — o Portainer define as variáveis diretamente na stack. O `env_file` não deve ser adicionado ao docker-compose de produção.

---

## Caminhos Persistentes vs Efêmeros

### Persistentes (sobrevivem a restart)
- `/opt/data/.hermes/` — configs, plugins, banco SQLite, logs
- `/opt/data/workspace/` — projetos e templates
- `/opt/data/scripts/` — scripts auxiliares
- `/opt/data/files/` — arquivos

### Efêmeros (wipados em restart)
- `/opt/hermes/` — código fonte do Hermes (sobrescrito em rebuild)
- `/tmp`, `/root`, `/home/hermes`, `/usr/local/bin`

**Cuidado:** Scripts em `/opt/hermes/scripts/` são apagados em rebuild. Sempre salve scripts em `/opt/data/scripts/`.

---

## Logs

- Gateway: `/opt/data/.hermes/logs/gateway.log`
- Agent: `/opt/data/.hermes/logs/agent.log`

**Nota:** O gateway não recarrega plugins em runtime — alterações em plugins só fazem efeito após restart da stack.

---

## Banco de Dados

- Arquivo: `/opt/data/.hermes/whatsapp_messages.db` (SQLite)
- Tabelas: `messages`, `chats`
- Servidor de histórico: `http://127.0.0.1:18732/chat/{chat_id}/messages`
- **Importante:** `chat_id` usa formato LID (`XXXXXXXXXXX@lid`), NÃO número de telefone. Exemplo: `164291240063173@lid`.
- O servidor de histórico NÃO tem endpoint `/health` — retorna 404.

> Para fluxo completo de injeção de contexto e histórico, ver `hermes-architecture`.

## Startup Após Restart do Container

O servidor de mensagem e o bridge WhatsApp NÃO são supervisionados pelo s6 — precisam ser iniciados manualmente após restart:

**Script de startup (já existe):**
```sh
bash /opt/data/start_whatsapp_message_server.sh
```
Esse script inicia o `whatsapp_message_server.py` na porta 18732 em background, se ainda não estiver rodando.

**Verificação pós-inicio:**
```sh
# Message server — NÃO tem /health, testa o endpoint real:
curl -s "http://127.0.0.1:18732/chat/5586981612061/messages?limit=3"

# Bridge WhatsApp:
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/

# Processos ativos:
ps aux | grep -E "(bridge|whatsapp_message)" | grep -v grep
```

## Verificação Rápida

```bash
# Processos ativos:
ps aux | grep -E "(bridge|whatsapp_message)" | grep -v grep

# Message server — NÃO tem /health, testa endpoint real:
curl -s "http://127.0.0.1:18732/chat/5586981612061/messages?limit=3"

# Bridge WhatsApp:
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/

# Database:
sqlite3 /opt/data/.hermes/whatsapp_messages.db \
  "SELECT COUNT(*) as total, COUNT(DISTINCT chat_id) as chats FROM messages"

# Listar chats (formato LID):
sqlite3 /opt/data/.hermes/whatsapp_messages.db \
  "SELECT chat_id, COUNT(*) as cnt FROM messages GROUP BY chat_id ORDER BY cnt DESC"
```

## Verificar se o Contexto está sendo Injetado

O fluxo de injeção de contexto:
1. `pre_gateway_dispatch` busca histórico via GET `/chat/{chat_id}/messages?limit=50`
2. Se houver histórico, reescreve: `{history}\n\n[ Nova mensagem do cliente ]\n{texto}`
3. LLM recebe a mensagem já com contexto

**Teste direto (sem WhatsApp):**
```python
# Simular injeção de mensagens de teste no DB
python3 -c "
import sqlite3, time
c = sqlite3.connect('/opt/data/.hermes/whatsapp_messages.db')
c.execute('''INSERT OR IGNORE INTO messages
  (chat_id, sender_id, message_id, body, timestamp, from_me, sender_name, message_type)
  VALUES (?,?,?,?,?,?,?,?)''',
  ('164291240063173@lid', '558681612061:60@s.whatsapp.net', 'msg_test_001',
   'Oi, vocês fazem sites?', int(time.time())-300, 0, 'Cliente Teste', 'text'))
c.commit()
print('OK')
"

# Ver histórico formatado:
python3 -c "
import sys; sys.path.insert(0, '/opt/data/.hermes/scripts')
from whatsapp_message_history import get_chat_history, format_history_for_context
msgs = get_chat_history('164291240063173@lid', limit=5)
print(format_history_for_context(msgs, '558681612061'))
"
```

**Teste real via WhatsApp:** Enviar mensagem de um contato que NÃO seja o número do André. O bot deve responder com contexto da conversa anterior.

## Bug Comum

**Sintoma:** Bot responde sem contexto histórico (não sabe o que foi dito antes).

**Causas possíveis:**
1. `WHATSAPP_OWNER_NUMBER` não setada → plugin retorna `None` → histórico não injetado
2. `chat_id` errado na query — o endpoint usa formato LID (`164291240063173@lid`), não número
3. Message server não está rodando (porta 18732)
4. **Gateway não recarrega plugins em runtime** — alterações em plugins só fazem efeito após restart da stack

**Fluxo de debug:**
1. `printenv | grep WHATSAPP` — verificar variável
2. `ps aux | grep whatsapp_message` — server rodando?
3. `curl "http://127.0.0.1:18732/chat/<LID>/messages?limit=3"` — histórico retorna?
4. `sqlite3 /opt/data/.hermes/whatsapp_messages.db "SELECT COUNT(*) FROM messages"` — DB tem dados?
5. Se mudou plugin → restart stack no Portainer

## GitHub Repo

O código está em: https://github.com/empreendedorserial/hermes-whatsapp-bot

**⚠️ Limitação de Visão (MiniMax) — Fix Aplicado (2 partes)**

**Problema:** MiniMax-M2.7 é text-only (`input=['text'], attachment=False`). O pipeline de visão tentava usar o main provider primeiro e retornava um client mesmo sem capacidade de visão.

**Solução em 2 etapas em `/opt/hermes/agent/auxiliary_client.py`:**

1. Adicionar `"minimax"` a `_PROVIDERS_WITHOUT_VISION` (linha ~303) — pula o main provider diretamente:
```python
_PROVIDERS_WITHOUT_VISION: frozenset = frozenset({
    "kimi-coding",
    "kimi-coding-cn",
    "minimax",  # ← ADD THIS
})
```

2. Adicionar `"gemini"` a `_VISION_AUTO_PROVIDER_ORDER` (linha ~3389) E adicionar handler em `_resolve_strict_vision_backend` (linha ~3420):
```python
# _VISION_AUTO_PROVIDER_ORDER:
_VISION_AUTO_PROVIDER_ORDER = (
    "openrouter",
    "gemini",  # ← ADD THIS
    "nous",
)

# _resolve_strict_vision_backend (dentro da função, antes do return None):
if provider == "gemini":
    return resolve_provider_client("gemini", model, is_vision=True)
```

Após o fix: **minimax → openrouter → gemini** (via `google/gemini-3-flash-preview`). A API key do Gemini (`GOOGLE_API_KEY`) já está em `credential_pool.gemini`.

**⚠️ Patches de Visão no Caminho Efêmero**

`/opt/hermes/agent/auxiliary_client.py` é efêmero — todo rebuild sobrescreve. Patches aplicados previamente (minimax em `_PROVIDERS_WITHOUT_VISION`, gemini em `_VISION_AUTO_PROVIDER_ORDER`) precisam ser re-aplicados após rebuild manual via Portainer.

**Se o gateway travar ao restart, NÃO reinicie** — verificar se Portainer congelou.

> Ver `hermes-architecture` para solução completa de visão (mini-max → gemini fallback).

### Checklist Pós-Restart Completo

```bash
# 0. INICIAR MESSAGE SERVER PRIMEIRO (não sobreviv ao restart)
bash /opt/data/start_whatsapp_message_server.sh

# 1. Processos ativos?
ps aux | grep -E "(bridge|whatsapp_message)" | grep -v grep

# 2. Message server respondendo?
curl -s "http://127.0.0.1:18732/chat/5586981612061/messages?limit=2"

# 3. Bridge online?
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/

# 4. VERIFICAR PATCHES DE VISÃO (p符didos em todo restart)
grep '"minimax"' /opt/hermes/agent/auxiliary_client.py | grep "_PROVIDERS_WITHOUT_VISION" || echo "PATCH MISSING: minimax not in _PROVIDERS_WITHOUT_VISION"
grep '"gemini"' /opt/hermes/agent/auxiliary_client.py | grep "_VISION_AUTO_PROVIDER_ORDER" || echo "PATCH MISSING: gemini not in _VISION_AUTO_PROVIDER_ORDER"
# Se missing → avisar usuário que precisa restartar pelo Portainer para re-aplicar patches

# 5. Imagens (testar enviar imagem no WhatsApp)
grep "não consegui visualizar" /opt/data/.hermes/logs/gateway.log | tail -3

# 6. Áudio: última transcrição bem-sucedida
grep "Transcribed.*via OpenAI API" /opt/data/.hermes/logs/agent.log | tail -3

# 7. STT funcionando? (teste direto)
grep "STT provider.*configured but unavailable" /opt/data/.hermes/logs/agent.log | tail -3
```

## Verificação pós-rebuild:
```bash
grep '"minimax"' /opt/hermes/agent/auxiliary_client.py | grep "_PROVIDERS_WITHOUT_VISION"
grep '"gemini"' /opt/hermes/agent/auxiliary_client.py | grep "_VISION_AUTO_PROVIDER_ORDER"
# Testar: enviar imagem no WhatsApp → bot deve descrever corretamente
```

## ⚠️ Áudio / Transcrição de Voz (STT) e Imagens

O plugin `whatsapp-manager` agora transcreve áudios e descreve imagens de forma **nativa e integrada** usando o **Google Gemini API** (`gemini-3.5-flash`), sem necessidade de chaves extras ou configurações adicionais de STT no core.

### Como funciona:
1. **Áudio**: Quando uma mensagem de voz (`ptt` ou `audio`) chega, o plugin codifica o arquivo temporário em base64, envia para a API do Gemini pedindo a transcrição literal, atualiza o evento em tempo real no gateway para `[Áudio: "transcrição..."]` e atualiza a mensagem no banco de dados SQLite `whatsapp_messages.db`.
2. **Imagens**: Imagens recebidas são processadas de forma análoga. O plugin envia a imagem para o Gemini para gerar uma descrição em português, atualizando o evento e o banco com `[Imagem: descrição...]`.
3. **Privacidade e Descarte**: Os arquivos físicos de áudio/imagem baixados pelo bridge são **excluídos imediatamente** após a conversão em base64 na memória, garantindo que o servidor não acumule mídias pesadas.

### Failsafe do Core (STT Tradicional):
Caso queira usar a transcrição nativa antiga do core via `run.py` para outros fluxos:
- **Providers clássicos:** `groq` (grátis), `openai` (pago), `local`, `mistral`, `xai`.
- **Configuração:** Adicionar `GROQ_API_KEY` ao `credential_pool` em `auth.json` e mudar `stt.provider: groq` em `config.yaml`.

---
- `.hermes/scripts/whatsapp_message_server.py`
- `.hermes/scripts/whatsapp_message_history.py`
- `.hermes/plugins/whatsapp-manager/__init__.py` (dashboard-managed)
- `.hermes/plugins/whatsapp-manager/plugin.yaml` (dashboard-managed)
- `scripts/start_whatsapp_message_server.sh`
- `README.md`

**Não versionar:** `whatsapp_messages.db`, `*.log`, `*.pid`, `bridge.log`
