# Oportunidades de Refactoring e Ganho de Performance

> Gerado em: 2026-06-18
> Metodologia: análise estática dos arquivos com mais de 500 linhas.

---

## Sumário Executivo

| Arquivo | Linhas | Prioridade | Impacto |
|---|---|---|---|
| `whatsapp_manager.py` | 2.577 | 🔴 Crítico | Alto |
| `bridge.js` | 1.681 | 🟠 Alto | Alto |
| `tests/plugin_test.py` | 1.405 | 🟡 Médio | Médio |
| `deploy/scripts/support_agent.py` | 643 | 🟡 Médio | Médio |
| `tests/bridge.test.js` | 597 | 🟢 Baixo | Baixo |

---

## 1. `whatsapp_manager.py` — 2.577 linhas

### 1.1 Triplicação do cliente HTTP LLM (linhas 647–714)

**Problema:** `_classify_contact_via_llm` repete o mesmo padrão `urllib.request` três vezes para Gemini, OpenAI e OpenRouter. O código é ~70 linhas de copypaste com variação apenas na URL, headers e path do resultado.

```python
# Padrão repetido 3x:
req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
with urllib.request.urlopen(req, timeout=10) as resp:
    result = json.loads(resp.read().decode("utf-8"))
    text_content = result["candidates"][0]["content"]["parts"][0]["text"]  # varia por provider
```

**Refactoring sugerido:** extrair `_call_llm_provider(url, headers, payload, extract_fn)` e registrar os providers num dict:

```python
_LLM_PROVIDERS = {
    "gemini": {...},
    "openai": {...},
    "openrouter": {...},
}
```

**Ganho:** reduz `_classify_contact_via_llm` de ~145 para ~40 linhas, facilita adicionar novos providers.

---

### 1.2 Push para o GitHub duplicado em 3 lugares

**Problema:** A lógica de push `GET sha → PUT content` aparece em:
- `_sync_contacts_from_db_internal` (linha ~1180)
- Função inline `push_contacts_to_github_bg` definida dentro de `pre_llm_call` (linha 2419)
- `register()` durante bootstrap (linha ~1800)

Isso é ~120 linhas de código idêntico espalhadas em contextos diferentes, com pequenas variações na mensagem do commit.

**Refactoring sugerido:** extrair `_github_put_file(repo_user, repo_name, token, path, content, message)` como função de módulo.

**Ganho:** DRY, eliminação de bugs assimétricos (um lugar tem `timeout=5`, outro `timeout=10`).

---

### 1.3 `register()` é um monólito de 867 linhas (linhas 1710–2577)

**Problema:** A função `register(ctx)` faz 5 coisas completamente distintas:
1. Migra sessão antiga de path (linhas 1722–1740)
2. Copia `bridge.js` / `package.json` para volume (linhas 1742–1761)
3. Cria repositório privado no GitHub (linhas 1763–1870)
4. Registra skills bundled (linhas 1942–1958)
5. Define e registra os dois hooks principais (linhas 1960–2577)

Além disso, os hooks `pre_gateway_dispatch` e `pre_llm_call` são definidos **dentro** de `register()`, tornando-os impossíveis de testar diretamente.

**Refactoring sugerido:**

```python
def register(ctx):
    _bootstrap_session_paths()
    _copy_bridge_files()
    _setup_github_repo()
    _register_skills(ctx)
    ctx.register_hook("pre_gateway_dispatch", pre_gateway_dispatch)
    ctx.register_hook("pre_llm_call", pre_llm_call)

# Hooks como funções de módulo, testáveis diretamente:
def pre_gateway_dispatch(context):
    ...

def pre_llm_call(context):
    ...
```

**Ganho:** testabilidade direta dos hooks, funções com responsabilidade única, facilita onboarding de devs novos.

---

### 1.4 Limpeza de número de telefone duplicada 5+ vezes

**Problema:** O padrão abaixo aparece em pelo menos 5 lugares diferentes em `pre_gateway_dispatch` e `pre_llm_call`:

```python
"".join(c for c in sender_id.split("@")[0].split(":")[0] if c.isdigit())
```

**Refactoring sugerido:** função utilitária simples, já existente como `_normalize_brazilian_phone` mas não centralizada:

```python
def _clean_phone_digits(jid: str) -> str:
    return "".join(c for c in jid.split("@")[0].split(":")[0] if c.isdigit())
```

**Ganho:** sem risco de divergência entre as cópias.

---

### 1.5 Abertura de arquivo de debug a cada mensagem (linha 2042)

**Problema:** Em cada mensagem recebida, o código abre e escreve em `/opt/data/whatsapp_manager_debug.log` com `open(..., "a")`. Em alto volume de mensagens isso gera I/O desnecessário e contende o filesystem.

```python
# Executado a cada mensagem:
with open("/opt/data/whatsapp_manager_debug.log", "a", encoding="utf-8") as debug_f:
    debug_f.write(f"[{time.strftime(...)}] ...")
```

**Refactoring sugerido:** usar `logger.debug(...)` que já tem buffering via `logging` stdlib, ou mover para um `FileHandler` com `RotatingFileHandler` configurado na inicialização do módulo.

**Ganho:** elimina syscall de abertura de arquivo por mensagem; `logging` faz flush em batch.

---

### 1.6 `pre_llm_call` com 7 níveis de aninhamento (linhas 2195–2465)

**Problema:** O bloco de classificação em tempo real (live sync) dentro de `pre_llm_call` chega a 7 níveis de indentação. O trecho de 270 linhas (2195–2465) mistura consulta ao SQLite, chamada ao LLM e push ao GitHub, com tratamento de erros intercalado.

**Refactoring sugerido:** extrair `_classify_and_update_contact(sender_id, chat_id, contact_info, personal_contacts)` como função separada. Essa função já pode ser testada em isolamento.

**Ganho:** reduz profundidade de aninhamento de 7 para 3, facilita testes unitários do bloco de classificação.

---

### 1.7 Imports tardios (`import sqlite3`, `import threading`, etc.)

**Problema:** Módulos da stdlib são importados dentro de funções (`import sqlite3` na linha 734, `import threading` na linha 2461, `import shutil` na linha 1718). Isso não é necessário (não são dependências condicionais) e obscurece o grafo de dependências real do módulo.

**Refactoring sugerido:** mover todos para o topo do arquivo com os outros imports.

---

## 2. `bridge.js` — 1.681 linhas

### 2.1 `startSocket()` com 130 linhas e todos os handlers inline (linha 848)

**Problema:** `startSocket()` define inline os handlers de `messages.upsert`, `connection.update`, `contacts.update` e outros eventos do Baileys. Qualquer bug num handler exige ler 400+ linhas de contexto.

**Refactoring sugerido:** extrair cada handler como função nomeada no módulo:

```js
async function handleMessageUpsert(messages) { ... }
async function handleConnectionUpdate(update) { ... }
async function handleContactsUpdate(contacts) { ... }

async function startSocket() {
    const sock = makeWASocket(...);
    sock.ev.on("messages.upsert", handleMessageUpsert);
    sock.ev.on("connection.update", handleConnectionUpdate);
    // ...
}
```

**Ganho:** cada handler testável isoladamente, `startSocket` reduz para ~30 linhas.

---

### 2.2 Rotas Express sem organização (linha 978+)

**Problema:** Todas as ~25 rotas HTTP estão definidas sequencialmente na mesma função anônima sem agrupamento lógico. Rotas de diagnóstico, rotas de envio, rotas de status de contatos e rotas de administração estão misturadas.

**Refactoring sugerido:** usar `express.Router()` por domínio:

```js
const diagnosticsRouter = require('./routes/diagnostics');
const messagingRouter  = require('./routes/messaging');
const adminRouter      = require('./routes/admin');

app.use('/diagnostics', diagnosticsRouter);
app.use('/messaging',   messagingRouter);
app.use('/admin',       adminRouter);
```

Ou, sem separar arquivos, pelo menos usar `Router` inline para agrupar visualmente.

**Ganho:** navegação mais rápida, surface de teste menor por rota.

---

### 2.3 `runSelfDiagnostics()` faz 3 coisas (linha 1107)

**Problema:** A função (120 linhas) coleta métricas do processo, consulta o Baileys e formata a resposta JSON de diagnóstico tudo em um só lugar.

**Refactoring sugerido:** separar `_collectProcessMetrics()`, `_collectBaileysState()` e montar o payload no chamador.

---

### 2.4 Cache de diagnósticos sem invalidação condicional (linha 1105)

**Problema:** `CACHE_TTL_MS = 30000` (30s) é um TTL fixo. Uma reconexão do Baileys não invalida o cache — um cliente pode ver um estado desatualizado por até 30s após o connect.

**Refactoring sugerido:** invalidar o cache quando `connection.update` disparar com `{ connection: "open" }`.

**Ganho:** estado de diagnóstico sempre correto após reconexão.

---

### 2.5 Constantes de configuração misturadas com funções utilitárias (linhas 171–220)

**Problema:** As variáveis de configuração (`PORT`, `SESSION_DIR`, `WHATSAPP_DEBOUNCE_INITIAL_MS`, etc.) são intercaladas com definições de funções utilitárias (`loadEnv`, `addRecentLog`, `classifyAndCountError`). Dificulta entender o que é config vs. comportamento.

**Refactoring sugerido:** agrupar todas as constantes de config num bloco único após os imports, separando-as visualmente das funções.

---

## 3. `tests/plugin_test.py` — 1.405 linhas

### 3.1 Uma única classe de testes gigante

**Problema:** `TestWhatsAppManagerPlugin` concentra todos os ~60 métodos de teste. Testes de normalização de telefone, testes de classificação de contato, testes de media processing e testes de hooks convivem na mesma classe.

**Refactoring sugerido:** dividir em classes focadas:

```python
class TestPhoneNormalization(unittest.TestCase): ...     # ~8 testes
class TestContactClassification(unittest.IsolatedAsyncioTestCase): ... # ~15 testes
class TestBotPausing(unittest.IsolatedAsyncioTestCase): ...            # ~6 testes
class TestMediaProcessing(unittest.IsolatedAsyncioTestCase): ...       # ~10 testes
class TestHookPreGatewayDispatch(unittest.IsolatedAsyncioTestCase): ...
class TestHookPreLlmCall(unittest.IsolatedAsyncioTestCase): ...
```

**Ganho:** falhas isoladas são imediatamente visíveis; setup/teardown mais leve por classe.

---

### 3.2 Setup de mocks repetido em cada método

**Problema:** Vários testes reconfiguram `MagicMock` para `urllib.request.urlopen`, `json.loads`, `os.path.exists` etc. individualmente, duplicando ~15 linhas por teste.

**Refactoring sugerido:** extrair `_make_bridge_mock(paused=False)` e `_make_event_mock(sender, chat, text)` como helpers de módulo reutilizáveis.

---

## 4. `deploy/scripts/support_agent.py` — 643 linhas

### 4.1 `llm_chat_completion` com 120 linhas e ramificação de provider (linhas 92–213)

**Problema:** O mesmo problema do `whatsapp_manager.py` — lógica HTTP repetida para cada provider (MiniMax, OpenAI, Claude). A função tem 6 níveis de aninhamento no pior caso.

**Refactoring sugerido:** extrair `_http_post_json(url, headers, payload)` como helper e usar um dict de providers igual ao sugerido para `whatsapp_manager.py`.

---

### 4.2 `run_agent()` com 245 linhas (linhas 399–643)

**Problema:** A função principal mistura: busca de threads de email, aplicação de filtros, geração de draft via LLM e decisão de envio — tudo em sequência sem divisão clara de etapas.

**Refactoring sugerido:**

```python
def run_agent():
    threads     = fetch_candidate_threads(service)
    candidates  = filter_actionable_threads(threads)
    for thread in candidates:
        draft = generate_draft(service, thread)
        create_draft(service, thread, draft)
```

**Ganho:** cada etapa testável separadamente; falhas localizam-se na etapa correta.

---

### 4.3 Paths hardcoded (`/opt/data`, `/opt/data/.hermes`)

**Problema:** Strings de path absolutas aparecem em ~12 lugares diferentes no arquivo sem nenhuma constante central. Uma mudança de layout de deploy exige editar manualmente ~12 linhas.

**Refactoring sugerido:**

```python
PERSISTENT_DATA_DIR = os.environ.get("HERMES_DATA_DIR", "/opt/data")
HERMES_HOME         = os.path.join(PERSISTENT_DATA_DIR, ".hermes")
```

`PERSISTENT_DATA_DIR` já existe mas `HERMES_HOME` é redefinido localmente em algumas funções.

---

## 5. `tests/bridge.test.js` — 597 linhas

### 5.1 Setup duplicado nos blocos `describe`

**Problema:** Vários blocos `describe` repetem a inicialização do servidor Express e o mock do socket Baileys. O padrão `beforeEach` / `afterEach` não é usado de forma consistente.

**Refactoring sugerido:** extrair `createTestApp()` e `createMockSocket()` como helpers de módulo e usá-los em todos os `beforeEach`.

**Ganho:** testes mais curtos, setup com uma linha, menos chance de estado vazando entre testes.

---

## Priorização Recomendada

| # | Ação | Esforço | Impacto |
|---|---|---|---|
| 1 | Extrair hooks de `register()` para funções de módulo | Médio | Testabilidade |
| 2 | Centralizar cliente HTTP LLM em helper reutilizável | Médio | Manutenção |
| 3 | Centralizar push GitHub em `_github_put_file` | Baixo | DRY / consistência |
| 4 | Substituir `open(debug.log)` por `logger.debug` | Baixo | Performance I/O |
| 5 | Extrair `_classify_and_update_contact` de `pre_llm_call` | Alto | Legibilidade |
| 6 | Dividir `TestWhatsAppManagerPlugin` em classes focadas | Médio | Manutenção de testes |
| 7 | Extrair handlers de eventos de `startSocket()` | Médio | Legibilidade |
| 8 | Centralizar paths em constantes em `support_agent.py` | Baixo | Manutenção |
