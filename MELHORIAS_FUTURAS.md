# Melhorias Futuras — hermes-whatsapp-mixed

Documento gerado em 2026-06-19 após análise completa do código.

---

## 🔴 Crítico (segurança e integridade de dados)

### 1. Path traversal em `/send-media` — `bridge.js`

**Problema:** O endpoint aceita qualquer `filePath` sem validar se está dentro do diretório permitido. Um cliente pode passar `"../../.env"` e ler arquivos arbitrários do servidor.

**Fix:**
```javascript
const CACHE_DIR = path.resolve('/tmp/whatsapp-cache');
const safe = path.resolve(CACHE_DIR, filePath);
if (!safe.startsWith(CACHE_DIR + path.sep)) {
  return res.status(400).json({ error: 'Invalid file path' });
}
const data = fs.readFileSync(safe);
```

---

### 2. `client_secret` salvo em disco — `google_api.py` linha ~126

**Problema:** `google_token.json` persiste `client_secret`. Junto com o `refresh_token`, dá acesso total à conta Gmail se o arquivo vazar.

**Fix:** Remover `client_secret` do JSON salvo; reler do env na inicialização:
```python
# Salvar apenas o necessário
json.dump({
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri": creds.token_uri,
    "scopes": list(creds.scopes or []),
}, f, indent=2)

# Ao reler, injetar client_id/secret do env
creds = Credentials(
    token=data.get("token"),
    refresh_token=data.get("refresh_token"),
    token_uri=data.get("token_uri"),
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scopes=data.get("scopes"),
)
```

---

### 3. Race condition em dicts globais — `whatsapp_manager.py`

**Problema:** `_sender_to_chat` e `_lid_to_phone` são lidos e escritos por múltiplas threads sem locks, podendo corromper estado silenciosamente.

**Fix:**
```python
import threading

_sender_to_chat: dict[str, str] = {}
_sender_to_chat_lock = threading.Lock()

_lid_to_phone: dict[str, str] = {}
_lid_to_phone_lock = threading.Lock()

# Em todos os acessos:
with _sender_to_chat_lock:
    _sender_to_chat[sender_id] = chat_id
```

---

## 🟠 Alto (estabilidade e segurança)

### 4. Memory leak em `silencedChats` — `bridge.js`

**Problema:** Chats silenciados nunca são removidos; objeto cresce indefinidamente.

**Fix:** Limpeza periódica:
```javascript
setInterval(() => {
  const now = Date.now();
  for (const [chatId, expiresAt] of Object.entries(silencedChats)) {
    if (now > expiresAt) delete silencedChats[chatId];
  }
}, 60_000); // A cada 1 minuto
```

---

### 5. Memory leak em `contactNameCache` — `bridge.js`

**Problema:** Map sem limite de entradas; com milhares de contatos pode causar OOM.

**Fix:** Limitar entradas e limpar expiradas:
```javascript
const MAX_CACHE_SIZE = 500;
// Ao inserir no cache, verificar tamanho:
if (contactNameCache.size >= MAX_CACHE_SIZE) {
  const firstKey = contactNameCache.keys().next().value;
  contactNameCache.delete(firstKey);
}
```

---

### 6. SQLite connection leak — `whatsapp_manager.py` linhas ~1804-1862

**Problema:** `conn = sqlite3.connect()` sem `try/finally`; exceções deixam conexões abertas.

**Fix:** Usar context manager:
```python
# Antes (problemático):
conn = sqlite3.connect(str(bridge_db_path))
cursor = conn.cursor()
# ... código que pode lançar exceção ...
conn.close()

# Depois (correto):
with sqlite3.connect(str(bridge_db_path)) as conn:
    cursor = conn.cursor()
    # conn fechada automaticamente ao sair do bloco
```

---

### 7. API keys expostas em logs — `whatsapp_manager.py` linhas ~307, ~689

**Problema:** URLs com `?key={google_key}` podem aparecer em stack traces e logs.

**Fix:** Nunca incluir a key na URL logada:
```python
url = f"https://generativelanguage.googleapis.com/v1beta/models/{media_model}:generateContent"
headers = {"x-goog-api-key": google_key}
# Logar apenas a URL base, sem key:
logger.debug(f"Chamando Gemini: {url}")
```

---

### 8. JID cleanup incorreto com device suffix — `allowlist.js` linha ~17

**Problema:** `"123@s.whatsapp.net:2"` resulta em `cleanSender = "123:2"` (sufixo preservado), falhando no match.

**Fix:** Remover `:device` antes do `@`:
```javascript
// Antes:
const cleanSender = senderId.replace(/@.*/, '').replace(/:.*/, '');

// Depois (ordem correta):
const cleanSender = senderId.replace(/:.*@/, '@').replace(/@.*/, '');
```

---

### 9. Espaços em `WHATSAPP_ALLOWED_USERS` — `allowlist.js` linha ~8

**Problema:** `"client123 , client456"` preserva espaços → match falha silenciosamente.

**Fix:**
```javascript
const allowedUsersSet = new Set(
  raw.split(',').map(u => u.trim()).filter(Boolean)
);
```

---

### 10. Permissões do `google_token.json` — `google_api.py`

**Problema:** Arquivo com `refresh_token` criado sem permissões restritivas.

**Fix:**
```python
import os
# Após salvar o arquivo:
os.chmod(TOKEN_PATH, 0o600)
```

---

## 🟡 Médio (manutenibilidade)

### 11. Duplicação 5x de `manual_relationship` migration — `whatsapp_manager.py`

**Onde:** linhas ~946, ~979, ~1109, ~1131, ~1925

**Fix:** Extrair para helper:
```python
def _migrate_manual_relationship(existing_data: dict) -> str | None:
    man_rel = existing_data.get("manual_relationship")
    if not man_rel and existing_data.get("relationship") in [
        "Vendedor", "Amigo", "AmigoProximo", "Parente", "Filho"
    ]:
        man_rel = existing_data.get("relationship")
    return man_rel
```

---

### 12. Caminhos hardcoded espalhados — `whatsapp_manager.py`

**Problema:** `/opt/data/...` aparece em ~15 lugares; mudança de estrutura quebra tudo.

**Fix:** Centralizar no topo do arquivo:
```python
_DATA_DIR = Path(os.getenv("HERMES_DATA_DIR", "/opt/data"))
_CONTACTS_FILE = _DATA_DIR / "personal_contacts.json"
_SOUL_FILE = _DATA_DIR / "SOUL_WHATSAPP.md"
_HERMES_HOME = _DATA_DIR / ".hermes"
```

---

### 13. `sessionDir` não utilizado — `allowlist.js` linha ~15

**Problema:** Parâmetro aceito mas nunca usado — confunde quem lê e pode criar falsa sensação de validação de path.

**Fix:** Remover parâmetro:
```javascript
// Antes:
export function matchesAllowedUser(senderId, allowedUsersSet, sessionDir)

// Depois:
export function matchesAllowedUser(senderId, allowedUsersSet)
```

---

### 14. Thread race em `_persist_transcription_to_db()` — `whatsapp_manager.py` linhas ~357-371

**Problema:** `db_path` capturado por closure pode sofrer mudança entre spawning e execução da thread.

**Fix:** Passar como parâmetro explícito:
```python
def _bg_update(path: str, msg_id: str, body: str):
    for delay in [1, 3, 5]:
        time.sleep(delay)
        r = _update_db_message(path, msg_id, body)
        if r:
            break

threading.Thread(target=_bg_update, args=(db_path, msg_id, new_body), daemon=True).start()
```

---

## 🔵 Cobertura de Testes

### 15. `google_api.py` — cobertura zero

Criar `tests/test_google_api.py` com:
- Token válido → retorna service sem erro
- Token expirado → renovação bem-sucedida
- Arquivo ausente → RuntimeError claro
- Arquivo corrompido → tratamento gracioso
- Extração de corpo `text/plain` vs `text/html`
- Extração multipart aninhado
- `client_secret` **não** aparece no arquivo salvo

### 16. `allowlist.js` — cobertura zero (isolada)

Criar `tests/allowlist.test.js` com:
- Wildcard `*` permite qualquer sender
- Número com device suffix `":2"` faz match corretamente
- Espaços em volta do número são ignorados
- Lista vazia bloqueia tudo
- JID com domínio `@g.us` (grupos) é tratado

---

## Priorização Sugerida

| # | Item | Esforço | Risco se não corrigir |
|---|------|---------|----------------------|
| 1 | Path traversal `/send-media` | Baixo | 🔴 Exploração trivial |
| 2 | `client_secret` em disco | Baixo | 🔴 Comprometimento de conta Gmail |
| 3 | Race condition dicts globais | Médio | 🔴 Corrupção de estado em produção |
| 4 | Memory leak `silencedChats` | Baixo | 🟠 OOM após dias de execução |
| 5 | Memory leak `contactNameCache` | Baixo | 🟠 OOM com muitos contatos |
| 6 | SQLite connection leak | Baixo | 🟠 Bloqueios de banco |
| 7 | API keys em logs | Baixo | 🟠 Vazamento de credenciais |
| 8 | JID cleanup com device suffix | Baixo | 🟠 Usuários no allowlist bloqueados |
| 9 | Espaços em `ALLOWED_USERS` | Baixo | 🟠 Match silencioso falha |
| 10 | Permissões `google_token.json` | Baixo | 🟡 Arquivo legível por outros processos |
| 11 | Duplicação `manual_relationship` | Médio | 🟡 Bug introduzido ao manter apenas parte dos lugares |
| 12 | Caminhos hardcoded | Médio | 🟡 Deploy em path diferente quebra tudo |
| 13 | `sessionDir` não usado | Baixo | 🟢 Confusão de leitura |
| 14 | Thread race `_persist_transcription` | Baixo | 🟡 Falha silenciosa de persistência |
| 15-16 | Testes `google_api` e `allowlist` | Alto | 🟡 Regressões sem detecção |
