# Plano de Implementação — Hermes WhatsApp Manager

**Data:** 2026-06-18 | **Atualizado:** 2026-06-22  
**Status:** Em andamento (Eixo A parcialmente implementado; Eixo B cancelado)  
**Escopo:** Performance

---

## Visão geral

Este documento consolida o eixo de performance identificado na análise técnica.

> **Nota:** O Eixo B (Integração Chatwoot) foi cancelado. Nenhuma das fases B1-B4 foi implementada.

---

## Eixo A — Performance

### Fase A1 — Cache de arquivos lidos em toda mensagem
**Prioridade:** Crítica | **Esforço estimado:** 2-3h

Resolve P1 e P2 do relatório. São os quick wins de maior impacto — eliminam I/O de disco em todo ciclo de mensagem.

**Arquivos afetados:** `whatsapp_manager.py`

**Tarefas:**

**A1.1 — Cache de `personal_contacts.json`**

Adicionar três variáveis de módulo:
```python
_contacts_cache: dict = {}
_contacts_cache_mtime: float = 0.0
_contacts_cache_lock = threading.Lock()
```

Refatorar `_load_personal_contacts()` para:
1. Checar `os.path.getmtime(pc_file)` vs `_contacts_cache_mtime`
2. Se mtime igual → retornar `_contacts_cache` sem abrir o arquivo
3. Se mtime diferente → ler, parsear, sanitizar, atualizar cache e mtime
4. Usar `_contacts_cache_lock` para thread-safety (sync periódico + live classification escrevem o arquivo em threads separadas)

Invalidar cache explicitamente ao final de qualquer função que grava `personal_contacts.json`:
- `_sync_contacts_from_db_internal()` → set `_contacts_cache_mtime = 0.0` após o `json.dump`
- live classification em `pre_llm_call` → idem

**A1.2 — Cache de arquivos de persona e regras**

Adicionar variáveis de módulo:
```python
_soul_cache: str = ""
_rules_cache: str = ""
_soul_rules_cache_ts: float = 0.0
_SOUL_CACHE_TTL: int = 3600  # 1 hora
```

Refatorar `_load_support_files()` para:
1. Se `time.time() - _soul_rules_cache_ts < _SOUL_CACHE_TTL` → retornar valores em cache
2. Caso contrário → ler do disco, atualizar cache e timestamp

Invalidar explicitamente ao final de `_pull_and_merge_configurations()`.

**Critério de conclusão:** `_load_personal_contacts()` e `_load_support_files()` não abrem arquivos em chamadas subsequentes dentro do TTL; testes unitários passam.

---

### Fase A2 — Mover live classification para background ✅ IMPLEMENTADO
**Prioridade:** Crítica | **Esforço estimado:** 3-4h

Resolve P3. Elimina a janela de 0-45s de delay visível para o usuário na primeira mensagem ou após cooldown expirar.

**Arquivos afetados:** `whatsapp_manager.py`

**Tarefas:**

**A2.1 — Extrair a lógica de live classification para função própria**

Criar `_live_classify_and_update(sender_id, chat_id, phone, name, chat_history, stats_info, personal_contacts, target_key)` que:
1. Chama `_classify_contact_via_llm()`
2. Monta o `new_data` dict
3. Grava em `personal_contacts.json`
4. Invalida `_contacts_cache_mtime`
5. Dispara `push_contacts_to_github_bg()` em thread daemon

**A2.2 — Substituir chamada síncrona por thread**

No bloco de live classification em `pre_llm_call`, onde atualmente está:
```python
classification = _classify_contact_via_llm(name, chat_history, stats_info)
# ... monta new_data ...
personal_contacts[target_key] = new_data
```

Substituir por:
```python
# Usar dados existentes (mesmo incompletos) para responder agora
# Disparar classificação em background para a próxima mensagem
threading.Thread(
    target=_live_classify_and_update,
    args=(sender_id, chat_id, phone, name, chat_history, stats_info, personal_contacts, target_key),
    daemon=True
).start()
```

**Atenção:** o `contact_info` usado logo abaixo para buildar o prompt deve ser o existente (pre-classificação), não o novo. Garantir que a thread não muta o dict antes do prompt ser construído (usar `contact_info` como cópia local antes de disparar a thread).

**Critério de conclusão:** mensagem de novo contato não apresenta delay de classificação; classificação ocorre em background e o JSON é atualizado antes da próxima mensagem do mesmo contato.

---

### Fase A3 — Remover log de debug síncrono do hot path
**Prioridade:** Crítica | **Esforço estimado:** 30min

Resolve P4. O `open(..., "a")` + `write()` na linha 2042 ocorre em toda mensagem.

**Tarefas:**

**A3.1 — Substituir por logging assíncrono**

Opção 1 (simples): substituir por `logger.debug(...)` — o handler já é assíncrono por padrão no Python logging.

Opção 2 (preservar arquivo separado): usar `logging.FileHandler` com `delay=True` e adicionar um `QueueHandler` na frente para não bloquear.

Opção 3 (remoção): se o debug log não é usado em produção, remover completamente o bloco.

**Critério de conclusão:** nenhum `open()` + `write()` síncrono no hot path de `pre_gateway_dispatch`.

---

### Fase A4 — Cache de status bot/chat com paralelização dos checks
**Prioridade:** Alta | **Esforço estimado:** 2-3h

Resolve P5. Dois HTTP calls (timeout=3s cada) para cada mensagem de cliente.

**Tarefas:**

**A4.1 — Cache de `bot_paused`**

Adicionar:
```python
_bot_paused_cache: bool = False
_bot_paused_cache_ts: float = 0.0
_BOT_PAUSED_CACHE_TTL: int = 5  # segundos
```

Em `_check_bot_paused()`:
- Se `time.time() - _bot_paused_cache_ts < _BOT_PAUSED_CACHE_TTL` → retornar `_bot_paused_cache`
- Caso contrário → fazer HTTP, atualizar cache e timestamp

**A4.2 — Cache de `chat_silenced` por chat_id**

Adicionar:
```python
_chat_silenced_cache: dict[str, tuple[bool, float]] = {}
_CHAT_SILENCED_CACHE_TTL: int = 10  # segundos
```

Em `_check_chat_silenced(chat_id)`:
- Checar `_chat_silenced_cache.get(chat_id)` → se dentro do TTL, retornar valor cacheado
- Caso contrário → HTTP, atualizar cache

**A4.3 — (Opcional) Paralelizar os dois checks**

Se os caches não forem suficientes, paralelizar com:
```python
with ThreadPoolExecutor(max_workers=2) as ex:
    f_paused = ex.submit(_check_bot_paused)
    f_silenced = ex.submit(_check_chat_silenced, chat_id)
    if f_paused.result() or f_silenced.result():
        return {"action": "skip", ...}
```

**Critério de conclusão:** em mensagens consecutivas do mesmo cliente, `_check_bot_paused()` não faz HTTP request por 5s; `_check_chat_silenced()` não faz HTTP por 10s.

---

### Fase A5 — Transcrição de mídia em background
**Prioridade:** Alta | **Esforço estimado:** 4-6h

Resolve P6. Transcrição de áudio/imagem bloqueia `pre_gateway_dispatch` por até 45s.

**Tarefas:**

**A5.1 — Retornar placeholder imediatamente**

Em `pre_gateway_dispatch`, ao detectar mídia:
1. Definir `event.text = "[Transcrevendo...]"` imediatamente
2. Disparar `_process_media_message()` em thread background
3. Quando a thread concluir, ela atualiza o banco e, opcionalmente, envia uma mensagem de follow-up com a transcrição

**A5.2 — Mecanismo de follow-up (opcional mas recomendado)**

A thread de transcrição, ao concluir, pode:
1. Chamar `BRIDGE_URL/send` com a transcrição como mensagem do sistema
2. Ou simplesmente salvar no banco para que a próxima mensagem do histórico inclua o conteúdo

**Complexidade:** esse ponto tem interação com o gateway que pode variar conforme a arquitetura do Hermes. Validar se o gateway aceita respostas assíncronas antes de implementar A5.2.

**Critério de conclusão:** mensagens com áudio não aumentam a latência de `pre_gateway_dispatch` além de 50ms.

---

### Fase A6 — Batch classification paralela no sync
**Prioridade:** Alta | **Esforço estimado:** 2-3h

Resolve P7. Classificação sequencial no boot pode levar dezenas de minutos.

**Tarefas:**

**A6.1 — Paralelizar `_classify_contact_via_llm()` no loop de sync**

Em `_sync_contacts_from_db_internal()`, substituir o loop serial por:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def _classify_one(chat_id, info):
    return chat_id, _classify_contact_via_llm(info["name"], info["history"], info["stats"])

with ThreadPoolExecutor(max_workers=5) as ex:
    futures = {ex.submit(_classify_one, cid, info): cid for cid, info in db_contacts.items()}
    for future in as_completed(futures):
        chat_id, classification = future.result()
        # ... merge logic ...
```

`max_workers=5` para não exceder rate limits das APIs LLM. Tornar configurável via env var `WHATSAPP_SYNC_LLM_WORKERS`.

**A6.2 — ~~Rodar sync do boot em thread separada~~** ✅ IMPLEMENTADO (diferente do previsto)

O sync do boot foi **removido completamente** — o plugin não faz sync automático na inicialização. Sync ocorre apenas via chat (`sync contacts`) ou no intervalo periódico (`WHATSAPP_SYNC_INTERVAL_HOURS`). A thread daemon `_run_sync_in_background` já está implementada para execuções sob demanda.

**Critério de conclusão:** sync de 50 contatos completa em menos de 2 minutos (vs. potenciais 37min anteriores).

---

### Fase A7 — Otimizações menores
**Prioridade:** Média | **Esforço estimado:** 1-2h

Resolve P8, P9, P10, P12.

**A7.1 — Cachear `id_column` do SQLite**

Em `_update_db_message()`, adicionar variável de módulo `_db_id_column: str | None = None`. Fazer o PRAGMA apenas uma vez.

**A7.2 — Paralelizar downloads em `_pull_and_merge_configurations()`**

```python
with ThreadPoolExecutor(max_workers=4) as ex:
    futures = {ex.submit(_download_file, url, path): path for path, url in bootstrap_files.items()}
```

**A7.3 — Mover `import sqlite3` para o topo do módulo**

Remover `import sqlite3` das funções `_update_db_message`, `_sync_contacts_from_db_internal` e mover para os imports do topo.

**A7.4 — Aumentar intervalo de polling de mtime para 300s**

No `_run_periodic_sync`, a verificação de mtime do `personal_contacts.json` pode ser feita a cada 300s ao invés de 60s. O arquivo só muda quando um contato é classificado — sem necessidade de verificar a cada minuto.

---

## ~~Eixo B — Integração Chatwoot~~ (CANCELADO)

> Nenhuma das fases abaixo foi implementada. Removido do roadmap.

### ~~Fase B1 — Infraestrutura e configuração~~
**Prioridade:** Alta | **Esforço estimado:** 1-2h

**Arquivos afetados:** `whatsapp_manager.py` (classe `PluginConfig`)

**Tarefas:**

**B1.1 — Adicionar propriedades ao `PluginConfig`**

```python
@property
def chatwoot_url(self) -> str:
    return os.getenv("CHATWOOT_URL", "").strip().rstrip("/")

@property
def chatwoot_api_token(self) -> str:
    return os.getenv("CHATWOOT_API_TOKEN", "").strip()

@property
def chatwoot_account_id(self) -> str:
    return os.getenv("CHATWOOT_ACCOUNT_ID", "").strip()

@property
def chatwoot_inbox_id(self) -> str:
    return os.getenv("CHATWOOT_INBOX_ID", "").strip()

@property
def chatwoot_export_enabled(self) -> bool:
    return os.getenv("CHATWOOT_EXPORT_ENABLED", "false").strip().lower() == "true"
```

**B1.2 — Validação de configuração no boot**

Em `register()`, adicionar verificação:
```python
if config.chatwoot_export_enabled:
    if not all([config.chatwoot_url, config.chatwoot_api_token,
                config.chatwoot_account_id, config.chatwoot_inbox_id]):
        logger.warning("CHATWOOT_EXPORT_ENABLED=true mas variáveis incompletas. Export desabilitado.")
```

**Critério de conclusão:** `PluginConfig` expõe 5 novas propriedades; warning no boot se configuração incompleta.

---

### Fase B2 — Cliente HTTP Chatwoot
**Prioridade:** Alta | **Esforço estimado:** 3-4h

**Tarefas:**

**B2.1 — `_chatwoot_request(method, path, payload)`**

Função base que monta a request com headers de autenticação e faz a chamada HTTP:
```python
def _chatwoot_request(method: str, path: str, payload: dict | None = None) -> dict | None:
    url = f"{config.chatwoot_url}/api/v1/accounts/{config.chatwoot_account_id}{path}"
    headers = {
        "api_access_token": config.chatwoot_api_token,
        "Content-Type": "application/json"
    }
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))
```

**B2.2 — `_chatwoot_find_or_create_contact(phone, name)`**

1. `GET /contacts/search?q={phone}&include_contacts=true` — busca por número
2. Se encontrar → retornar `contact_id`
3. Se não encontrar → `POST /contacts` com `{name, phone_number: "+{phone}"}`
4. Retornar `contact_id` ou `None` em caso de erro

**B2.3 — `_chatwoot_create_conversation(contact_id, meta)`**

`POST /conversations` com:
```json
{
  "contact_id": contact_id,
  "inbox_id": chatwoot_inbox_id,
  "additional_attributes": {
    "product": meta.get("product"),
    "frequency": meta.get("frequency"),
    "whatsapp_jid": meta.get("jid")
  }
}
```
Retorna `conversation_id`.

**B2.4 — `_chatwoot_add_private_note(conversation_id, text)`**

`POST /conversations/{id}/messages` com:
```json
{
  "content": text,
  "message_type": "outgoing",
  "private": true
}
```

**Critério de conclusão:** funções testáveis de forma isolada com mock HTTP; todas retornam `None` (sem exception) em caso de falha.

---

### Fase B3 — Orquestração e idempotência
**Prioridade:** Alta | **Esforço estimado:** 2-3h

**Tarefas:**

**B3.1 — `_export_lead_to_chatwoot(phone, jid, contact_info)`**

Função de orquestração que:
1. Verifica `config.chatwoot_export_enabled` — retorna imediatamente se falso
2. Verifica `contact_info.get("chatwoot_exported")` — retorna se já exportado
3. Normaliza phone com prefixo `+` para E.164
4. Chama `_chatwoot_find_or_create_contact(phone, name)`
5. Chama `_chatwoot_create_conversation(contact_id, meta)`
6. Monta nota privada com `summary`, `intent`, `frequency`, `tone`, `guidelines`
7. Chama `_chatwoot_add_private_note(conversation_id, note_text)`
8. Atualiza `contact_info` com:
   ```python
   contact_info["chatwoot_exported"] = True
   contact_info["chatwoot_conversation_id"] = conversation_id
   ```
9. Persiste `personal_contacts.json` e invalida cache

**B3.2 — Hook na live classification**

Ao final do bloco de live classification em `pre_llm_call`, após a classificação confirmar `relationship == "Cliente"`:

```python
if classification.get("relationship") == "Cliente" and not contact_info.get("chatwoot_exported"):
    threading.Thread(
        target=_export_lead_to_chatwoot,
        args=(phone, chat_id, new_data),
        daemon=True
    ).start()
```

**B3.3 — Preservação do campo `chatwoot_*` no merge**

Em `_sync_contacts_from_db_internal()` e `_pull_and_merge_configurations()`, garantir que o merge nunca sobrescreva:
- `chatwoot_exported`
- `chatwoot_conversation_id`

Adicionar nos blocos de merge:
```python
for field in ["chatwoot_exported", "chatwoot_conversation_id"]:
    if existing_data.get(field):
        new_entry[field] = existing_data[field]
```

**Critério de conclusão:** um contato classificado como "Cliente" gera exatamente uma conversa no Chatwoot, mesmo após re-classificações ou sync.

---

### Fase B4 — Export batch histórico (opcional)
**Prioridade:** Baixa | **Esforço estimado:** 2h

**Tarefa:** adicionar um comando de owner no WhatsApp (`export leads chatwoot`) que percorre `personal_contacts.json`, filtra `relationship == "Cliente"` e `chatwoot_exported != True`, e chama `_export_lead_to_chatwoot()` para cada um, com delay de 500ms entre chamadas para respeitar rate limits.

**Critério de conclusão:** comando disponível apenas para o dono; exporta todos os leads históricos sem duplicatas.

---

## Dependências entre fases

```
A1 ──────────────────────────────────────────────── A2 (✅ implementado)
A1 ──────────────────────────────────────────────── A6
A3 (independente)
A4 (independente)
A5 (independente)
A7 (independente, pode ser feito a qualquer momento)
```

---

## Sequência sugerida de implementação

| Sprint | Fases | Justificativa |
|---|---|---|
| 1 | A1, ~~A2~~, A3 | A2 já implementado; A1 e A3 eliminam I/O síncrono |
| 2 | A4, A6 | Elimina HTTP desnecessário |
| 3 | A5 | Mídia em background (maior complexidade) |
| 4 | A7 | Otimizações menores |

---

## Riscos da implementação

| Risco | Fase | Mitigação |
|---|---|---|
| Cache de `personal_contacts` fica stale se arquivo for editado externamente | A1 | Usar mtime como chave de invalidação; é suficiente para o padrão de uso |
| Live classification em background pode usar dados desatualizados como base | A2 | Aceito: a resposta imediata usa dados existentes; próxima mensagem já tem classificação nova |
| Thread race condition: duas threads tentam gravar `personal_contacts.json` ao mesmo tempo | A2, B3 | Usar `threading.Lock()` em torno do `json.dump` |
| `ThreadPoolExecutor` no sync sobrecarrega API LLM | A6 | `max_workers=5` + env var configurável; implementar retry com backoff exponencial |

---

## Novos env vars (resumo)

| Variável | Default | Fase |
|---|---|---|
| `WHATSAPP_SYNC_LLM_WORKERS` | `5` | A6 |

---

## Critério global de conclusão

- Latência de `pre_llm_call` para contatos já conhecidos: < 50ms (sem I/O de disco ou HTTP)
- Primeira mensagem de contato novo: sem delay extra visível (classificação em background) ✅
- Boot do plugin: completo em < 5s (sem sync no boot) ✅
- Cobertura de testes: novas funções com mocks para HTTP e I/O de disco
