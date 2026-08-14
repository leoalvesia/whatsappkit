# 📋 Changelog & Sessão de Debug — `whatsapp-manager`

Documentação consolidada de todas as correções, novos recursos e incidentes de segurança do plugin `whatsapp-manager` durante a sessão de 11/06/2026.

---

## 🎯 Resumo Executivo

| # | Tipo | Descrição | Commit |
|---|---|---|---|
| 1 | Bug | Truncamento de JSON na classificação Gemini (maxOutputTokens) | `abb6f15` |
| 2 | Bug | Sync lia só 15 contatos de `whatsapp_messages.db` ignorando 28 reais do `state.db.sessions` | `ac3ebd1` |
| 3 | Feature | Resolução de nome de contato via Baileys (`/contact/:jid`) | `3189476` |
| 4 | Security | Chave Gemini acidentalmente documentada no CHANGELOG → redatada + force-push | pós-`3189476` |

**Resultado final:** sync passou de 15 para 28 contatos WhatsApp únicos, com nomes reais resolvidos via Baileys.

---

## 🐛 Bug #1 — Truncamento de JSON na Classificação Gemini

### Sintoma
```
[whatsapp-manager] Falha ao classificar via Gemini: JSON incompleto ou malformado no texto: {
  "relationship": "Amigo",
  "tone": "informal e amigável",
  "nickname": null
[whatsapp-manager] Resultado da sincronização no boot: Sucesso! Mapeados e mesclados 15 contatos localmente.
- 11 contatos classificados via IA.
- 4 contatos curtos configurados com valores padrão.
```

### Diagnóstico

Gemini retornava `finishReason: MAX_TOKENS` e cortava a resposta em ~80 chars / 29 tokens de saída.

- **Modelo**: `gemini-3.5-flash` (confirmado em [ai.google.dev/gemini-api/docs/models/gemini-3.5-flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash))
- **Limite do modelo**: 65.536 tokens de saída
- **Limite configurado no plugin**: `maxOutputTokens: 1024` ← gargalo

### Teste de Validação

`tests/test_gemini_classification.py` faz a mesma chamada com 1024 e 4096:

| `maxOutputTokens` | `finishReason` | Tokens saída | JSON válido? |
|---|---|---|---|
| 1024 (original) | `MAX_TOKENS` | 29 | ❌ |
| 4096 (fix) | `STOP` | 192 | ✅ (10/11 campos) |

### Correção

**Arquivo:** `whatsapp_manager.py:280`

```diff
- "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 1024}
+ "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 4096}
```

---

## 🐛 Bug #2 — Sync lia apenas 15 contatos, ignorando 28 reais

### Sintoma

Dashboard `/sessions` mostrava 177 conversas (28 WhatsApp únicas + 84 Telegram + 13 Cron + 7 TUI), mas sync reportava apenas 15 contatos classificados.

### Investigação

#### DBs encontrados em `/opt/data/.hermes/`

| DB | Tamanho | Conteúdo |
|---|---|---|
| `state.db` | 143 MB | Sessões + mensagens do gateway (177 sessões, 28 user_ids WhatsApp únicos) |
| `whatsapp_messages.db` | 77 KB | Log local da bridge (178 mensagens, 15 contatos únicos) |
| `whatsapp_message_history.db` | 0 bytes | Nunca populado |
| `kanban.db`, `response_store.db` | pequenos | Sem tabela `messages` |

#### Distribuição em `state.db.sessions`

```
cron       13
telegram   84
tui         7
whatsapp   28 user_ids únicos (73 sessões, conversas recorrentes)
```

#### Causa raiz

O plugin lia apenas de `whatsapp_messages.db` (log da bridge Baileys), que tem um subconjunto truncado. O `state.db.sessions WHERE source='whatsapp'` é o **DB autoritativo** do gateway e tem TODOS os contatos processados.

### Correção

**Arquivo:** `whatsapp_manager.py:305-507` + `:1531-1583`

Substituir leitura única por **sistema de 3 fontes**:

```python
# 2a. Fonte primária: state.db.sessions WHERE source='whatsapp'
state_cursor.execute("""
    SELECT user_id, MAX(started_at) as last_ts, COUNT(*) as session_count
    FROM sessions
    WHERE source = 'whatsapp' AND user_id IS NOT NULL
    GROUP BY user_id
    ORDER BY last_ts DESC
""")

# 2b. Fonte complementar: whatsapp_messages.db (sender_name + histórico)
bridge_cursor.execute("""
    SELECT chat_id, MAX(sender_name) as name, COUNT(*), MIN(timestamp), MAX(timestamp)
    FROM messages
    WHERE chat_id NOT LIKE '%@g.us%' AND chat_id IS NOT NULL
    GROUP BY chat_id
""")

# 2c. Fallback para state.db.messages (quando bridge não tem histórico)
state_cursor.execute("""
    SELECT m.role, m.content FROM messages m
    JOIN sessions s ON m.session_id = s.id
    WHERE s.user_id = ? AND s.source = 'whatsapp' AND m.content IS NOT NULL
    ORDER BY m.timestamp DESC LIMIT 15
""")
```

### Mudanças adicionais

- `max_classifications` 40 → 100 (env `WHATSAPP_SYNC_MAX_CLASSIFICATIONS`)
- Logs informativos mostrando quantos contatos em cada DB
- Mesma correção aplicada no live sync (linha 1531) que classifica em tempo real
- Testes atualizados para refletir novo fluxo de 3 queries

### Resultado

```
[whatsapp-manager] sync: 28 contatos WhatsApp em state.db.sessions
[whatsapp-manager] sync: 15 contatos em whatsapp_messages.db
[whatsapp-manager] sync: 28 contatos unicos para processar
```

Subiu de 15 → 28 contatos (+87%).

---

## ✨ Feature #3 — Resolução de Nome de Contato via Baileys

### Problema

Contatos sem `sender_name` no log da bridge apareciam como `"Contato {phone}"` (ex: `"Contato 558694279071"`), dificultando busca e ajustes manuais.

### Solução

#### Bridge (`bridge.js`)

Novo endpoint `GET /contact/:jid`:

```javascript
const contactNameCache = new Map();
const CONTACT_CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24h

async function resolveContactName(jid) {
  // 1) sock.contacts (carregado no boot via Baileys push notifications)
  if (sock.contacts && typeof sock.contacts === 'object') {
    const stored = sock.contacts[jid] || sock.contacts[cleanJid + '@s.whatsapp.net'] || sock.contacts[cleanJid + '@lid'];
    if (stored) {
      return stored.name || stored.verifiedName || stored.pushName || stored.notify;
    }
  }
  // 2) Fallback: onWhatsApp existence check
  ...
}

app.get('/contact/:jid', async (req, res) => {
  // ... chama resolveContactName e cacheia
});
```

#### Plugin (`whatsapp_manager.py`)

```python
def _resolve_contact_name_from_bridge(jid: str) -> str | None:
    """Consulta o Baileys via bridge para obter o pushName."""
    try:
        url = f"{BRIDGE_URL}/contact/{urllib.parse.quote(jid, safe='')}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("name") or None
    except Exception as e:
        return None

def _best_contact_name(jid, bridge_name, db_name, phone):
    """Prioriza: pushName Baileys > log bridge > fallback 'Contato {phone}'"""
    ...
```

Sync chama automaticamente quando detecta nome genérico/ausente:

```python
if not name or (isinstance(name, str) and name.startswith("Contato ")):
    bridge_name = _resolve_contact_name_from_bridge(chat_id)
best_name, name_source = _best_contact_name(chat_id, bridge_name, name, phone)
if name_source == "bridge":
    print(f"[whatsapp-manager] Nome resolvido via Baileys para {chat_id}: {best_name}")
```

### Limitação

O Baileys só tem o pushName dos contatos **que já enviaram mensagem** (carregados via push). Contatos na agenda do celular que **nunca mandaram msg** continuam sem nome.

---

## 🔐 Incidente #4 — Chave Gemini Exposta no CHANGELOG

### O que aconteceu

Durante a documentação da sessão, escrevi a chave Gemini literalmente no `CHANGELOG_DEBUG.md` (linha 190) como exemplo de "chave exposta". O arquivo foi commitado em `2791324` e ficou público no GitHub com a chave em texto claro.

**Nota de redação:** o valor da chave (`AIzaSy...REDACTED`, suprimido desta documentação) estava em texto claro no commit `2791324` e foi removido via `filter-branch` + force-push.

### Por que foi grave

- A chave estava no **histórico público do GitHub**
- Qualquer pessoa com o link do repo ou GitHub Code Search podia ver
- Bots de scraping de chaves de API indexaram em minutos

### Correção aplicada

1. **Substituído a chave** por `AIzaSy[REDACTED]` no `CHANGELOG_DEBUG.md`
2. **`git filter-branch`** para reescrever todos os commits do histórico removendo a chave
3. **`git push --force`** para sincronizar GitHub
4. **Validação**: `git log --all -S "<string da chave vazada>"` retorna **0 commits** (chave removida de todo o histórico)
5. **Histórico público reescrito** — commits `957bb25..02a5adb` antigos (com chave) substituídos por `ac3ebd1..3189476` limpos

### Validação

```bash
# Buscar a chave vazada em todos os commits do histórico:
$ git log --all --oneline -S "<prefixo da chave vazada>"
(no output)  # chave removida de todos os commits

# Verificar arquivo por arquivo em cada commit:
$ for c in $(git log --all --format=%H | head -10); do
    git show "$c:CHANGELOG_DEBUG.md" 2>/dev/null | grep -q "<prefixo>" && echo "FALHOU"
  done
# (no output)  # chave não está em nenhum arquivo de nenhum commit
```

### Estado após limpeza

- Chave Gemini **regenerada** pelo autor no Google AI Studio
- Histórico do GitHub **reescrito sem a chave**
- Clones antigos do repo podem ter a chave em `git log` local, mas a chave é **inválida** (regenerada)
- GitHub pode ter **cache do commit antigo** em `view raw` por alguns minutos

### ⚠️ Outras chaves potencialmente expostas (NÃO commitadas)

Durante a sessão de debug, as seguintes chaves apareceram em outputs de terminal **mas não foram commitadas**:

- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`

Estas estão apenas no histórico da conversa (que é descartado após a sessão). **Recomendação:** regenerar todas como precaução, especialmente se você gravou/printou a conversa.

### 📚 Lição aprendida

> **Nunca escrever chaves de API em arquivos versionados, mesmo em notas de "segurança".**
>
> O correto seria referenciar o incidente sem mostrar o valor da chave (ex: "uma chave Gemini que começa com AIzaSy..." ou apenas "a chave Gemini usada nos testes"). O efeito prático de documentar vs vazar é o mesmo arquivo público.

---

## 🛠️ Scripts de Teste

### `tests/test_gemini_classification.py` (mantido)

Validador de regressão para a chamada ao Gemini. Roda com 1024 e 4096 tokens.

```bash
GOOGLE_API_KEY=xxx python3 tests/test_gemini_classification.py
```

**Output esperado:**
```
maxTokens= 1024: FALHOU finish=MAX_TOKENS tokens=  29 len=   80 chars (irrecuperável)
maxTokens= 4096: OK     finish=STOP       tokens= 192 len=  658 chars
```

### Scripts de diagnóstico (removidos antes do push)

- `tests/test_gemini_scaling.py` — comparou 1024/2048/4096/8192
- `tests/test_extractor.py` — testou casos extremos do `_extract_json_from_text`
- `tests/test_real_call.py` — simulou chamada real idêntica à produção

---

## 📚 Lições Aprendidas

1. **`maxOutputTokens` é o gargalo mais comum em classificação JSON via LLM.** Sempre validar com teste real que a resposta cabe no limite.

2. **O `/sessions` do dashboard Hermes lê de `state.db.sessions`, não do `whatsapp_messages.db`.** São duas fontes de verdade que precisam ser reconciliadas para sync completo.

3. **`sqlite3` CLI não está disponível no contêiner Hermes.** Usar `python3 -c "import sqlite3..."` para diagnóstico.

4. **Testes com `MagicMock` precisam ser atualizados quando o número de queries SQL muda.** Adicionar entradas no `fetchall.side_effect` para cada nova query.

5. **Mocks de teste não executam realmente o código de produção.** Erros reais só aparecem em produção — daí a importância de monitorar logs após cada deploy.

6. **`git filter-branch` + force-push é a forma correta de limpar segredos do histórico.** Mas requer cuidado: clones antigos precisarão de `git reset --hard origin/main`.

7. **Documentação de incidentes de segurança não deve conter os valores vazados.** Referenciar sem reproduzir.

---

## 🚀 Como Aplicar em Produção

1. **Pull do código novo:**
   ```bash
   # No painel Hermes → Plugins → whatsapp-manager → Pull/Atualizar
   ```

2. **Reiniciar contêiner (Stop → Start, não Restart):**
   ```bash
   # Portainer/Easypanel → hermes-agent → Stop → Start
   ```

3. **Verificar logs pós-restart:**
   ```
   [whatsapp-manager] sync: 28 contatos WhatsApp em state.db.sessions
   [whatsapp-manager] sync: 15 contatos em whatsapp_messages.db
   [whatsapp-manager] sync: 28 contatos unicos para processar
   [whatsapp-manager] Resultado da sincronização no boot: Sucesso! Mapeados e mesclados 28 contatos localmente.
   ```

4. **Verificar se nomes reais aparecem** (não `"Contato {phone}"`):
   ```bash
   cat /opt/data/personal_contacts.json | python3 -m json.tool | grep '"name"'
   ```

---

## 📂 Arquivos Modificados

| Arquivo | Mudança | Commit |
|---|---|---|
| `whatsapp_manager.py` | maxOutputTokens 1024→4096 | `abb6f15` |
| `whatsapp_manager.py` | Sync multi-DB (state.db) | `ac3ebd1` |
| `whatsapp_manager.py` | Resolução de nome via Baileys | `3189476` |
| `bridge.js` | Endpoint `/contact/:jid` + cache | `3189476` |
| `tests/plugin_test.py` | Mocks atualizados para 3 queries | `ac3ebd1` |
| `tests/test_gemini_classification.py` | Novo teste de regressão | `abb6f15` |
| `CHANGELOG_DEBUG.md` | Recriado (chave redatada) | este commit |

---

## 📅 Histórico de Commits desta Sessão

| Commit | Mensagem |
|---|---|
| `abb6f15` | fix: aumentar maxOutputTokens 1024->4096 na classificação Gemini |
| `ac3ebd1` | fix: sync de contatos agora le state.db.sessions (fonte autoritativa) |
| `3189476` | feat: resolver nome de contato via Baileys quando sender_name ausente |

**Commits substituídos pela limpeza de segurança:**
- `993cc5b` (anterior à sessão)
- `02a5adb`, `957bb25`, `19697af`, `f49149a`, `5fa765f`, `6a0aa36` (anteriores)
- `2791324` ← continha a chave exposta, foi reescrito via `filter-branch`

---

*Documento gerado em 11/06/2026.*
