# Hermes WhatsApp Plugin

Plugin **`whatsapp-manager`** para o [Hermes Agent v2026](https://github.com/nousresearch/hermes). Transforma o WhatsApp em um assistente pessoal inteligente no **SelfChat** (para o dono) e um atendente autônomo e seguro para clientes — tudo no mesmo número, com isolamento total de permissões e inteligência contextual.

> **Licença:** [BUSL-1.1](LICENSE) — uso livre para desenvolvimento e testes. Converte para MIT em 2031-06-25.

---

## 🚀 Destaques da Versão v2026

- **Arquitetura de Container Único (Single-Container):** Desde o Hermes Agent v0.19 ("Quicksilver"), o core ganhou uma plataforma WhatsApp nativa (`hermes_plugins.whatsapp_platform`) que descobre, sobe e monitora o processo Node.js da ponte automaticamente — em vez deste plugin gerenciar seu próprio subprocesso. O `bridge.js` deste repositório continua sendo o código que roda; o Hermes só assumiu o ciclo de vida do processo (spawn, pidfile, restart em crash), eliminando o container duplicado e o erro de desconexão `440 conflict / replaced`.
- **Roteamento Nativo por Perfis (`default` vs `whatsapp`):**
  - **`SelfChat` (Perfil: `default`):** Acesso à persona executiva (`SOUL.md`), histórico completo, comandos de controle e **todas as ferramentas ativas** (código, terminal, busca web, mídias).
  - **Clientes/Contatos (Perfil: `whatsapp`):** Persona de suporte (`SOUL_WHATSAPP.md` + `support_rules.md`), respostas baseadas nas regras de negócio e **todas as ferramentas desativadas por padrão (`toolsets: []`)** com firewall de execução no backend.
- **Silêncio de Avisos Brutais:** Ocultação automática de mensagens do sistema (como aviso de reset de 24h e metadados `◆ Model: ...`).

---

## 🛠️ O que faz

### Para o Dono (SelfChat)
- Assistente pessoal executivo com acesso ao histórico completo de todas as conversas
- Consultas cruzadas em linguagem natural: *"o que a Isabel falou sobre o contrato?"*
- Atualização de contatos em linguagem natural: *"a Isabel é minha filha, apelido Bebel"*
- Comandos de controle do bot: `stop_bot` (pausar), `start_bot` (retomar), `sincronizar contatos`, `quais comandos`

### Para Clientes e Contatos
- Atendimento autônomo guiado por `support_rules.md` (produtos, preços, FAQs)
- Tom personalizado por contato via `personal_contacts.json`
- Transcrição automática de áudios e descrição de imagens via Gemini
- Silêncio automático de 10 minutos quando o dono lê ou responde manualmente

### Inteligência de Contatos
- Classificação automática: `Cliente | Amigo | AmigoProximo | Parente | Filho | Vendedor`
- Campo `notes` injetado como **instrução obrigatória** no prompt (o LLM obedece)
- Resumo cumulativo por período (`full_summary`) comprimido a cada sync
- Sync automático a cada 24h com repositório privado do GitHub — contatos e personas versionados

---

## 📐 Arquitetura do Container

```
┌──────────────────────────────────────────────────────────────────┐
│  Container Único: hermes (nousresearch/hermes-agent)            │
│  ├─ Hermes Gateway (Porta 9119 — Dashboard/REST API)             │
│  ├─ hermes_plugins.whatsapp_platform (NATIVO, core >= v0.19)     │
│  │    └─ descobre, sobe e monitora o processo Node abaixo        │
│  ├─ Microprocesso Baileys Node.js (bridge.js deste repo, :3000)  │
│  ├─ Plugin whatsapp-manager (Python Hooks — regras de negócio)   │
│  └─ Isolation Profiles:                                          │
│     ├─ /profiles/default/   → Dono (Full Tools + SOUL)           │
│     └─ /profiles/whatsapp/  → Clientes (No Tools + Prompt)       │
└──────────────────────────────────────────────────────────────────┘

Quem faz o quê:
  - whatsapp-manager (este repo) → instala o bridge.js no volume, registra
    os hooks pre_gateway_dispatch/pre_llm_call/post_llm_call/pre_tool_call
    (toda a lógica de negócio: classificação de contato, personas, sync).
  - hermes_plugins.whatsapp_platform (core do Hermes) → dono do ciclo de
    vida do processo Node: spawn, pidfile com detecção de PID reciclado,
    restart automático em crash, e o parsing de mensagens recebidas.
  - O plugin NÃO spawna mais o bridge.js diretamente — só o entrega no
    caminho convencional para o core encontrar e gerenciar.

Volume Compartilhado: /opt/data
  ├─ .hermes/plugins/whatsapp-manager/   → Código do plugin
  ├─ .hermes/platforms/whatsapp/bridge/  → bridge.js (gerenciado pelo core)
  ├─ .hermes/platforms/whatsapp/session/ → Sessão Baileys (creds, chaves)
  ├─ .hermes/profiles/whatsapp/          → Config e SOUL de clientes
  ├─ .hermes/profiles/default/           → Config e SOUL do dono
  ├─ .hermes/whatsapp_messages.db        → Histórico raw (bridge)
  ├─ .hermes/state.db                    → Sessões e contexto
  ├─ personal_contacts.json              → Perfis dos contatos
  ├─ support_rules.md                    → Base de conhecimento (clientes)
  └─ SOUL_WHATSAPP.md                    → Persona e estilo de escrita
```

> Detalhe de compatibilidade: o Hermes Agent v0.19+ também ganhou uma plataforma WhatsApp **totalmente nativa** (`plugins/platforms/whatsapp/` no core), com endpoints próprios de polls (`/send-poll`) e localização (`/send-location`). Neste projeto, o core detecta e reaproveita o `bridge.js` deste repo em vez de subir a implementação nativa — este `bridge.js` já implementa os dois endpoints (`POST /send-poll`, `POST /send-location`), com os métodos equivalentes `send_poll()`/`send_location()` expostos em `adapter.py`.

---

## 📁 Estrutura do Repositório

```
├── whatsapp_manager.py          # Plugin principal (Hooks Python)
├── adapter.py                   # Adaptador de plataforma nativo (WhatsAppPlatformAdapter)
├── bridge.js                    # Bridge WhatsApp (Node.js + Baileys)
├── plugin.yaml                  # Manifesto do plugin
├── deploy/
│   ├── docker-compose.yml       # Swarm / Portainer (Single container + setup auto)
│   ├── docker-compose.easypanel.yml  # Easypanel (Single container + setup auto)
│   ├── setup.sh                 # Setup inicial de 1 clique
│   ├── SOUL.md                  # Persona base do dono (Engenheiro/Assistente)
│   ├── SOUL_WHATSAPP.md         # Persona de atendimento aos clientes
│   ├── support_rules.md         # Regras de suporte e FAQs (exemplo)
│   └── personal_contacts.json.example
├── tests/
│   └── plugin_test.py           # 265 testes unitários (100% passing)
└── validate_dedup.py            # Validação de dedup no container
```

---

## ⚡ Instalação e Deploy

### Pré-requisitos

- Hermes Agent rodando no **Portainer** ou **Easypanel**
- Domínio configurado apontando para o servidor
- [Google AI Studio](https://aistudio.google.com) — chave da API Gemini (`GOOGLE_API_KEY`)
- Repositório privado no GitHub para versionamento de contatos

---

### Deploy via Portainer (Swarm)

1. No Portainer → **Stacks** → **Add stack**.
2. Cole o conteúdo de [`deploy/docker-compose.yml`](deploy/docker-compose.yml).
3. Preencha as variáveis de ambiente essenciais:
   - `GOOGLE_API_KEY`: Chave da API Gemini
   - `WHATSAPP_OWNER_NUMBER`: Seu número sem `+` (ex: `5511999999999`)
   - `WHATSAPP_OWNER_NAME`: Seu nome (ex: `André`)
   - `CONFIG_GITHUB_TOKEN`: PAT do GitHub para sincronização dos contatos
4. Clique em **Deploy the stack**. O container irá subir, aplicar as configurações de segurança, e iniciar a bridge interna.

---

### Deploy via Easypanel

1. No Easypanel → **New Service** → **Compose**.
2. Cole o conteúdo de [`deploy/docker-compose.easypanel.yml`](deploy/docker-compose.easypanel.yml).
3. Na aba *Environment*, adicione as variáveis e certifique-se de marcar **"Criar arquivo .env"**.
4. Clique em **Deploy**.

---

## 📲 Conectar o WhatsApp (QR Code)

Após subir o container, acesse os endpoints de pareamento pelo seu navegador:

| URL | Descrição |
|---|---|
| `https://hermes.seu-dominio.com/whatsapp/qr` | Tela de QR Code HTML interativa |
| `https://hermes.seu-dominio.com/whatsapp/qr?format=png` | Imagem direta em PNG |
| `https://hermes.seu-dominio.com/whatsapp/status` | Status JSON da conexão |

No seu celular: **WhatsApp → Aparelhos Conectados → Conectar um aparelho** → Escaneie o QR Code.

---

## 💬 Comandos no WhatsApp (SelfChat)

Envie mensagens para si mesmo no WhatsApp. Todos os comandos de controle funcionam **exclusivamente para o dono**:

| Comando | Descrição |
|---|---|
| `quais comandos` / `ajuda` | Exibe a lista completa de comandos e status do bot |
| `stop_bot` | Pausa o atendimento automático a clientes |
| `start_bot` | Reativa o atendimento automático a clientes |
| `sincronizar contatos` | Força a sincronização de contatos com o GitHub em background |
| `update contact <nome> campo=valor` | Atualiza dados de um contato (ex: `update contact Bebel relationship=Filho`) |

---

## 🔒 Segurança de Ferramentas por Perfil

```yaml
# Perfil "whatsapp" (/opt/data/.hermes/profiles/whatsapp/config.yaml)
agent:
  tool_use_enforcement: disabled

toolsets: []         # ❌ Nenhuma ferramenta habilitada para clientes
disabled_toolsets:   # ❌ Todas as 25 famílias de ferramentas desativadas
  - file_operations
  - code_execution
  - vision
  - image_generation
  - web_search
  - terminal
  - computer_use

tools: []
skills:
  enabled: false
```

- **Clientes:** Se uma mensagem de cliente tentar forçar a execução de ferramentas, o hook `pre_tool_call` intercepta e aborta imediatamente a chamada no backend.
- **Dono (SelfChat):** Pode solicitar qualquer execução de código, leitura de arquivos ou buscas normalmente.

---

## 🧪 Testes Automatizados

O projeto possui cobertura completa de testes unitários:

```bash
# Executar a suíte de testes (265 testes unitários)
python3 -m unittest tests/plugin_test.py
```

---

*Desenvolvido e mantido por [André Alencar](https://aalencar.com.br) / Empreendedor Serial.*
