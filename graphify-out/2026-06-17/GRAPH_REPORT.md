# Graph Report - hermes-whatsapp-mixed  (2026-06-16)

## Corpus Check
- 40 files · ~66,744 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 835 nodes · 890 edges · 91 communities (38 shown, 53 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 24 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `963394ba`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Bridge Core (Main)|Bridge Core (Main)]]
- [[_COMMUNITY_Bridge Artifacts (deploydocs)|Bridge Artifacts (deploy/docs)]]
- [[_COMMUNITY_Bridge Artifacts (docs)|Bridge Artifacts (docs)]]
- [[_COMMUNITY_WhatsApp Manager Core|WhatsApp Manager Core]]
- [[_COMMUNITY_Google API Module|Google API Module]]
- [[_COMMUNITY_Message Routing & Control|Message Routing & Control]]
- [[_COMMUNITY_Deployment Infrastructure|Deployment Infrastructure]]
- [[_COMMUNITY_Plugin Integration Tests|Plugin Integration Tests]]
- [[_COMMUNITY_Gmail & OAuth Integration|Gmail & OAuth Integration]]
- [[_COMMUNITY_Bridge Dependencies (deploy)|Bridge Dependencies (deploy)]]
- [[_COMMUNITY_Bridge Dependencies (docs)|Bridge Dependencies (docs)]]
- [[_COMMUNITY_Package Dependencies|Package Dependencies]]
- [[_COMMUNITY_Gemini Classification Pipeline|Gemini Classification Pipeline]]
- [[_COMMUNITY_Message Debounce & Routing|Message Debounce & Routing]]
- [[_COMMUNITY_Bridge Artifacts (deploydocs alt)|Bridge Artifacts (deploy/docs alt)]]
- [[_COMMUNITY_Bridge Artifacts (docs alt)|Bridge Artifacts (docs alt)]]
- [[_COMMUNITY_Deploy Setup Scripts|Deploy Setup Scripts]]
- [[_COMMUNITY_Gemini Rules & Settings|Gemini Rules & Settings]]
- [[_COMMUNITY_Allowlist & Phone Filter|Allowlist & Phone Filter]]
- [[_COMMUNITY_WhatsApp Logs Diagnostics|WhatsApp Logs Diagnostics]]
- [[_COMMUNITY_Custom Model Classification|Custom Model Classification]]
- [[_COMMUNITY_Phone Resolution (LID)|Phone Resolution (LID)]]
- [[_COMMUNITY_JID Phone Resolution|JID Phone Resolution]]
- [[_COMMUNITY_Unknown LID Passthrough|Unknown LID Passthrough]]
- [[_COMMUNITY_Owner Message Skip Logic|Owner Message Skip Logic]]
- [[_COMMUNITY_Silenced Chat Skip Logic|Silenced Chat Skip Logic]]
- [[_COMMUNITY_Bot Pause LID Cache|Bot Pause LID Cache]]
- [[_COMMUNITY_Custom Provider Env Vars|Custom Provider Env Vars]]
- [[_COMMUNITY_Media Info (Direct Attrs)|Media Info (Direct Attrs)]]
- [[_COMMUNITY_Media Info (Dict Payload)|Media Info (Dict Payload)]]
- [[_COMMUNITY_MIME Type Detection|MIME Type Detection]]
- [[_COMMUNITY_Audio Processing|Audio Processing]]
- [[_COMMUNITY_Audio Custom Model|Audio Custom Model]]
- [[_COMMUNITY_Image Multi-limit|Image Multi-limit]]
- [[_COMMUNITY_Custom Print Redirection|Custom Print Redirection]]
- [[_COMMUNITY_DB Message Update|DB Message Update]]
- [[_COMMUNITY_Plugin Self-Update Git|Plugin Self-Update Git]]
- [[_COMMUNITY_QR Code Endpoint|QR Code Endpoint]]
- [[_COMMUNITY_WhatsApp Status Endpoint|WhatsApp Status Endpoint]]
- [[_COMMUNITY_Debug Changelog|Debug Changelog]]
- [[_COMMUNITY_Design System|Design System]]
- [[_COMMUNITY_Graphify Rule|Graphify Rule]]
- [[_COMMUNITY_Graphify Workflow|Graphify Workflow]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]

## God Nodes (most connected - your core abstractions)
1. `TestWhatsAppManagerPlugin` - 62 edges
2. `PluginConfig` - 23 edges
3. `WhatsApp Bot — Sistema Completo` - 16 edges
4. `📚 FAQs e Resolução de Problemas Técnicos` - 16 edges
5. `🤖 Hermes Agent - Modo Misto Híbrido (WhatsApp + Gmail)` - 14 edges
6. `_sync_contacts_from_db_internal()` - 12 edges
7. `📋 Changelog & Sessão de Debug — `whatsapp-manager`` - 11 edges
8. `Arquitetura do Hermes Agent` - 11 edges
9. `onMessagesUpsert()` - 10 edges
10. `run_agent()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Gemini Key Test` --semantically_similar_to--> `OAuth2 Flow`  [INFERRED] [semantically similar]
  tests/test_gemini_key.py → google_api.py
- `Debounce Logic` --semantically_similar_to--> `Real-time Classification`  [INFERRED] [semantically similar]
  bridge.js → whatsapp_manager.py
- `WhatsApp Logs Diagnostics Skill (deploy)` --semantically_similar_to--> `WhatsApp Logs Diagnostics Skill`  [INFERRED] [semantically similar]
  deploy/skills/whatsapp-logs-diagnostics/SKILL.md → skills/whatsapp-logs-diagnostics/SKILL.md
- `BeforeTool Hook Command` --references--> `Graphify Integration Rules`  [INFERRED]
  .gemini/settings.json → GEMINI.md
- `onMessagesUpsert()` --calls--> `matchesAllowedUser()`  [INFERRED]
  deploy/docs/bridge-artifacts/bridge.js → allowlist.js

## Import Cycles
- 1-file cycle: `deploy/scripts/support_agent.py -> deploy/scripts/support_agent.py`

## Communities (91 total, 53 thin omitted)

### Community 0 - "Bridge Core (Main)"
Cohesion: 0.03
Nodes (33): _ACCEPTED_HOST_VALUES, activityCounters, ALLOWED_USERS, app, args, AUDIO_CACHE_DIR, BOT_STATE_FILE, CHUNK_DELAY_MS (+25 more)

### Community 1 - "Bridge Artifacts (deploy/docs)"
Cohesion: 0.04
Nodes (28): _ACCEPTED_HOST_VALUES, activityCounters, ALLOWED_USERS, app, args, AUDIO_CACHE_DIR, BOT_STATE_FILE, CHUNK_DELAY_MS (+20 more)

### Community 2 - "Bridge Artifacts (docs)"
Cohesion: 0.04
Nodes (28): _ACCEPTED_HOST_VALUES, activityCounters, ALLOWED_USERS, app, args, AUDIO_CACHE_DIR, BOT_STATE_FILE, CHUNK_DELAY_MS (+20 more)

### Community 3 - "WhatsApp Manager Core"
Cohesion: 0.10
Nodes (19): _build_owner_context(), _build_personal_prompt(), _build_support_prompt(), _check_chat_silenced(), _fetch_chat_history(), _load_support_files(), _normalize_brazilian_phone(), _push_personal_contacts_to_github() (+11 more)

### Community 4 - "Google API Module"
Cohesion: 0.10
Nodes (28): datetime, build_service(), _extract_body_from_part(), _extract_message_body(), _headers_dict(), Salva as credenciais atualizadas em TOKEN_PATH., Recebe uma mensagem bruta da Gmail API e retorna um dicionário     de headers co, Extrai o corpo da mensagem da Gmail API, suportando:       - Mensagens simples ( (+20 more)

### Community 5 - "Message Routing & Control"
Cohesion: 0.10
Nodes (19): Allowlist, Contact Filter, Conversation Silence, Debounce Logic, Gemini Model Router, Message Router, Global Pause, Personal Contact Routing (+11 more)

### Community 6 - "Deployment Infrastructure"
Cohesion: 0.06
Nodes (38): Email Support Persona, Hermes Persona (SOUL), WhatsApp Support Persona, 10. Configuração de Integrações e Pagamentos, 11. Instalações Múltiplas do Dealer, 12. Pagamento de Parcerias e Colaborações, 13. Problemas Técnicos em Plataformas de Parceria, 14. Problemas de Acesso ao Chatkanban (+30 more)

### Community 8 - "Gmail & OAuth Integration"
Cohesion: 0.06
Nodes (33): Gmail Integration, Google API Module, OAuth2 Flow, Autorização Google OAuth2 (Gmail), Configuração no Google Cloud Console, Notas Importantes, O que o agente deve fazer, Passo 1 — Verificar se o token já existe (+25 more)

### Community 9 - "Bridge Dependencies (deploy)"
Cohesion: 0.18
Nodes (10): dependencies, express, @hapi/boom, pino, qrcode, qrcode-terminal, @whiskeysockets/baileys, scripts (+2 more)

### Community 10 - "Bridge Dependencies (docs)"
Cohesion: 0.18
Nodes (10): dependencies, express, @hapi/boom, pino, qrcode, qrcode-terminal, @whiskeysockets/baileys, scripts (+2 more)

### Community 11 - "Package Dependencies"
Cohesion: 0.18
Nodes (10): dependencies, express, @hapi/boom, pino, qrcode, qrcode-terminal, @whiskeysockets/baileys, scripts (+2 more)

### Community 12 - "Gemini Classification Pipeline"
Cohesion: 0.29
Nodes (9): analyze(), balance_braces(), call_gemini(), main(), Teste local do Gemini gemini-3.5-flash para diagnosticar truncamento de JSON.  U, Fecha chaves faltantes (mesma lógica proposta para _extract_json_from_text)., Tenta parsear fechando chaves faltantes., Extrai finishReason, tamanho e tenta parsear o JSON. (+1 more)

### Community 13 - "Message Debounce & Routing"
Cohesion: 0.22
Nodes (9): calcDebounceDelay(), flushDebounceBuffer(), getContextInfo(), getMessageContent(), normalizeWhatsAppId(), onMessagesUpsert(), saveBotState(), sendWithTimeout() (+1 more)

### Community 14 - "Bridge Artifacts (deploy/docs alt)"
Cohesion: 0.29
Nodes (7): getContextInfo(), getMessageContent(), normalizeWhatsAppId(), onMessagesUpsert(), saveBotState(), sendWithTimeout(), trackSentMessageId()

### Community 15 - "Bridge Artifacts (docs alt)"
Cohesion: 0.29
Nodes (7): getContextInfo(), getMessageContent(), normalizeWhatsAppId(), onMessagesUpsert(), saveBotState(), sendWithTimeout(), trackSentMessageId()

### Community 16 - "Deploy Setup Scripts"
Cohesion: 0.80
Nodes (4): commit_file_to_github(), download_file(), safe_download(), setup.sh script

### Community 17 - "Gemini Rules & Settings"
Cohesion: 0.50
Nodes (4): Graphify Integration Rules, Gemini Developer Rules, BeforeTool Hook Command, Gemini Tool Hooks

### Community 45 - "Community 45"
Cohesion: 0.05
Nodes (41): 1. Garantir as Credenciais do Google na Stack, 1. Pausa Global (`stop_bot` / `start_bot`), 1. Sincronização Periódica e Inteligente (GitHub ➔ Servidor), 2. Auto-Update de Código com Reinício Automático, 2. Pedir o Link ao Bot (No Console do Hermes ou no Telegram), 2. Silenciamento Temporário Automático (10 minutos), 3. Classificação Dinâmica e Blindagem de Contatos, 3. Entregar o Link de Retorno ao Bot (+33 more)

### Community 46 - "Community 46"
Cohesion: 0.05
Nodes (38): Deploy Guide, 1. WhatsApp, 2. E-mail (Gmail API / Google Workspace), 3. LLM (MiniMax), Arquitetura do Hermes Agent, Arquivos de Configuração e Persona, Backup Failsafe do Core (STT Tradicional):, Como funciona: (+30 more)

### Community 47 - "Community 47"
Cohesion: 0.05
Nodes (37): 📂 Arquivos Modificados, Bridge (`bridge.js`), 🐛 Bug #1 — Truncamento de JSON na Classificação Gemini, 🐛 Bug #2 — Sync lia apenas 15 contatos, ignorando 28 reais, Causa raiz, 📋 Changelog & Sessão de Debug — `whatsapp-manager`, 🚀 Como Aplicar em Produção, Correção (+29 more)

### Community 48 - "Community 48"
Cohesion: 0.06
Nodes (35): Docker Compose, Docker Compose EasyPanel, EasyPanel Config, 🕹️ Comandos de Controle (WhatsApp), 📋 Guia Passo a Passo - Configuração do Hermes Agent (Modo Misto), 🔒 Opção A: Sincronização Segura com Repositório Privado (Para Contatos Pessoais e Configurações Privadas), 🎨 PASSO 1: Fazer um Fork e Customizar no seu GitHub, 🛠️ PASSO 2: Subir a Stack e Chaves no Portainer (+27 more)

### Community 49 - "Community 49"
Cohesion: 0.07
Nodes (27): 1. `WHATSAPP_OWNER_NUMBER` (CRÍTICA), 2. `HERMES_HOME`, 3. `WHATSAPP_HOME_CHANNEL`, Arquitetura, Arquivos de Configuração, Arquivos Principais, Banco de Dados, Bug Comum (+19 more)

### Community 50 - "Community 50"
Cohesion: 0.14
Nodes (13): 🚫 Diretrizes de Abordagem e Identificação (CRÍTICO), 🚫 Diretrizes de Decisões e Compromissos (CRÍTICO), 🚫 Diretrizes de Segurança e Restrições Rígidas, Exemplo 1:, Exemplo 2:, Exemplo 3:, Exemplo 4:, Exemplo 5: Cliente pergunta se é um bot (+5 more)

### Community 51 - "Community 51"
Cohesion: 0.15
Nodes (12): 🕹️ Comandos e Silenciamento Inteligente, 🚀 Como Atualizar / Fazer Deploy do Plugin, 🐋 Como Fazer Deploy da Stack, Como rodar os testes localmente:, ✨ Funcionalidades Principais, 🤖 Hermes Agent - WhatsApp & Email Dual-Mode, ⚡ Instalação Rápida do Plugin, 📂 Nova Estrutura do Repositório (+4 more)

### Community 52 - "Community 52"
Cohesion: 0.18
Nodes (10): Exemplo 1: Conversa com o André (Admin - MODO A), Exemplo 2: Conversa com Cliente (Suporte WhatsApp - MODO B), Exemplo 3: Conversa com Cliente (Suporte WhatsApp - MODO B), Exemplo 4: Conversa com Cliente (Suporte WhatsApp - MODO B), Exemplo 5: Conversa com Cliente (Suporte WhatsApp - MODO B), 📝 EXEMPLOS PRÁTICOS DE DIÁLOGOS (FEW-SHOT), 👤 MODO A: Assistente Pessoal do André (Quando falar com André Alencar), 💼 MODO B: Chatbot de Suporte Comercial (Quando falar com Clientes) (+2 more)

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (4): _classify_contact_via_llm(), _extract_json_from_text(), Extrai o primeiro objeto JSON válido de um texto usando balanceamento de chaves., Classifica contatos usando a API do LLM (Gemini, OpenAI ou OpenRouter) com base

### Community 54 - "Community 54"
Cohesion: 0.25
Nodes (7): Diagnóstico e Logs do WhatsApp, Logs Físicos no Servidor, O que o agente deve fazer, Passo 1 — Obter o domínio do servidor, Passo 2 — Diagnóstico via Requisição Local (se executado pelo agente no terminal), Passo 3 — Apresentar as Instruções e URLs ao Usuário, Quando usar esta skill

### Community 55 - "Community 55"
Cohesion: 0.25
Nodes (7): 🕒 Atendimento Fora do Horário Comercial (Noite, Fins de Semana e Feriados), Exemplo 1: Dúvida sobre o curso de n8n, Exemplo 2: Cupom de desconto, 📝 EXEMPLOS DE RESPOSTAS POR E-MAIL (ESTILO FORMAL E ESTRUTURADO), 📧 Persona do Agente de Suporte e Vendas por E-mail (Gmail), 🚫 Restrições de Segurança e Privacidade, 🎭 Tom de Voz e Estilo de Conversa

### Community 56 - "Community 56"
Cohesion: 0.25
Nodes (7): Diagnóstico e Logs do WhatsApp, Logs Físicos no Servidor, O que o agente deve fazer, Passo 1 — Obter o domínio do servidor, Passo 2 — Diagnóstico via Requisição Local (se executado pelo agente no terminal), Passo 3 — Apresentar as Instruções e URLs ao Usuário, Quando usar esta skill

### Community 57 - "Community 57"
Cohesion: 0.25
Nodes (6): _best_contact_name(), Consulta o Baileys via bridge para obter o pushName/contact name de um JID., Resolve o melhor nome disponivel para um contato.      Ordem de prioridade:, Sincroniza contatos do SQLite local para personal_contacts.json e envia para o G, _resolve_contact_name_from_bridge(), _sync_contacts_from_db_internal()

### Community 58 - "Community 58"
Cohesion: 0.15
Nodes (8): WhatsApp Manager Plugin Package Entry Point., MockContext, Python unit tests for the whatsapp-manager plugin., _ensure_google_libs(), Instala as bibliotecas da Google API no venv do Hermes se ainda não estiverem di, Atualiza o código do plugin a partir do repositório Git. Retorna True se houve m, register(), _self_update_plugin_code()

### Community 59 - "Community 59"
Cohesion: 0.33
Nodes (6): _check_bot_paused(), _pull_and_merge_configurations(), Baixa as configurações do repositório privado do GitHub do cliente e faz merge c, Traduz JID do WhatsApp (seja LID ou formato padrão) para JID com telefone clássi, Verifica se o bot está pausado via endpoint do bridge e atualiza o mapa de LIDs., _resolve_phone_from_jid()

### Community 60 - "Community 60"
Cohesion: 0.33
Nodes (6): _get_media_info(), _get_mime_type(), _process_media_message(), Extrai informações de mídia de um objeto de evento de forma extremamente robusta, Retorna o tipo MIME adequado com base na extensão do arquivo., Processa mensagem de mídia (áudio ou imagem) usando a API do Gemini.          Re

### Community 61 - "Community 61"
Cohesion: 0.40
Nodes (4): 1. 🎛️ Pausa Global (Controlada na Ponte), 2. 🔇 Silenciamento Temporário (Conversas Específicas com Clientes), 📐 Arquitetura e Regras de Controle do Chatbot (WhatsApp), 🔄 Fluxo de Processamento (Resumo Técnico)

### Community 66 - "Community 66"
Cohesion: 0.50
Nodes (4): _persist_transcription_to_db(), Atualiza o corpo da mensagem no SQLite detectando dinamicamente a coluna de ID., Executa a persistência da transcrição/descrição tratando eventuais race conditio, _update_db_message()

### Community 70 - "Community 70"
Cohesion: 0.40
Nodes (4): _load_personal_contacts(), Carrega o arquivo personal_contacts.json e sanitiza cada entrada.      Retorna {, Evita que nomes possessivos/parentesco do André (como 'pai', 'mãe', etc.) sejam, _sanitize_classification_result()

## Knowledge Gaps
- **350 isolated node(s):** `recentLogs`, `errorCounters`, `activityCounters`, `args`, `PORT` (+345 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **53 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TestWhatsAppManagerPlugin` connect `Plugin Integration Tests` to `Custom Model Classification`, `Phone Resolution (LID)`, `JID Phone Resolution`, `Unknown LID Passthrough`, `Owner Message Skip Logic`, `Silenced Chat Skip Logic`, `Bot Pause LID Cache`, `Custom Provider Env Vars`, `Media Info (Direct Attrs)`, `Media Info (Dict Payload)`, `MIME Type Detection`, `Audio Processing`, `Audio Custom Model`, `Image Multi-limit`, `Custom Print Redirection`, `DB Message Update`, `Plugin Self-Update Git`, `Community 53`, `Community 57`, `Community 58`, `Community 62`, `Community 67`, `Community 68`, `Community 69`, `Community 70`, `Community 71`, `Community 72`, `Community 73`, `Community 74`, `Community 75`, `Community 76`, `Community 78`, `Community 79`, `Community 80`, `Community 81`, `Community 82`, `Community 83`, `Community 84`, `Community 85`, `Community 86`, `Community 87`, `Community 88`, `Community 89`, `Community 90`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `matchesAllowedUser()` connect `Allowlist & Phone Filter` to `Bridge Core (Main)`, `Message Debounce & Routing`, `Bridge Artifacts (deploy/docs alt)`, `Bridge Artifacts (docs alt)`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `onMessagesUpsert()` connect `Bridge Artifacts (deploy/docs alt)` to `Bridge Artifacts (deploy/docs)`, `Allowlist & Phone Filter`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **What connects `WhatsApp Manager Plugin Package Entry Point.`, `recentLogs`, `errorCounters` to the rest of the system?**
  _441 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Bridge Core (Main)` be split into smaller, more focused modules?**
  _Cohesion score 0.03278688524590164 - nodes in this community are weakly interconnected._
- **Should `Bridge Artifacts (deploy/docs)` be split into smaller, more focused modules?**
  _Cohesion score 0.03636363636363636 - nodes in this community are weakly interconnected._
- **Should `Bridge Artifacts (docs)` be split into smaller, more focused modules?**
  _Cohesion score 0.03636363636363636 - nodes in this community are weakly interconnected._