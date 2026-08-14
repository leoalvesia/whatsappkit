# Graph Report - hermes-whatsapp-mixed  (2026-07-22)

## Corpus Check
- 63 files · ~114,321 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1831 nodes · 2361 edges · 145 communities (95 shown, 50 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 40 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6a0ac1a3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Node.js WhatsApp Bridge
- Deploy Bridge Code Artifacts
- Bridge Documentation Artifacts
- Deploy Guidelines & Sync
- Deployment Configurations (Docker)
- Debug Changelog Analysis
- Hermes Architecture Guidelines
- Deploy Support & Integrations
- WhatsApp Bot Env Vars
- Google OAuth Authentication
- Base plugin tests & core logic
- Additional test suites & edge cases
- WhatsApp Manager Configurations
- Workspace Setup & Architecture Overview
- Test cases for user/bot interaction logic
- Deploy Readme and Soul Persona
- WhatsApp Manager execution tests
- Prompt building and context preparation
- Bot Paused & Silencing checks
- Deploy Soul WhatsApp specifications
- System README & deployment instructions
- _classify_contact_via_llm
- Contact management test cases
- Contact name resolution & sync
- Deploy Package Dependencies (Express)
- Deploy Soul Conversational Examples
- Bridge Node Package Dependencies
- Google API service builder
- Root Package Dependencies
- Gemini Classification unit tests
- Bridge debounce & delay logic
- Deploy Bridge debounce & delay
- Bridge Docs debounce & delay
- Base WhatsApp Manager Test Suite
- Deploy WhatsApp Logs & Diagnostics
- Deploy Soul Email specifications
- WhatsApp Logs & Diagnostics skill
- Contact list loading & configurations sync
- Deploy setup and GitHub integration scripts
- System Design and Pausing specifications
- Gemini agent settings and hooks
- Transcription database persistence
- WhatsApp Logs capabilities
- Gemini configuration assets
- Graphify rules metadata
- Deploy DB contacts synchronizer
- Bridge Jest testing suite
- Graphify workflows definition
- Debug session changelogs
- Design markdown layout
- Graphify rule details
- Contacts synchronization scripts
- Gemini classification test run
- Graphify workflow parameters
- 🟠 Alto (estabilidade e segurança)
- TestOwnerCommands
- Deploy do Plugin WhatsApp Manager
- Plano de Implementação — Hermes WhatsApp Manager
- Como instalar o Hermes WhatsApp no Easypanel (do zero ao bot funcionando)
- TestCollectAndreMessagesByRelationship
- TestDedupPersonalContacts
- TestExtractJsonFromText
- TestSanitizeSensitive
- TestProcessMediaMessage
- TestLiveClassifyContact
- TestFullSummaryFunctions
- TestPreToolCall
- TestSanitizeSensitive
- TestBuildLidPhoneMap
- startSocket
- google_api.py
- O que o agente deve fazer
- TestPendingContactUpdate
- test_utils_and_filters.py
- Research Sources — YouTube, Brave Search e Reddit
- _detect_contact_query
- onMessagesUpsert
- test_nl_update.py
- onMessagesUpsert
- _search_contact_by_name
- TestFetchCrossSessionHistory
- TestCheckChatSilenced
- _resolve_contact_name_from_bridge
- TestRunSyncInBackground
- _get_mime_type
- startSocket
- test_audio_transcription.py
- test_contact_search.py
- TestSanitizeClassificationResult
- TestResolvePhoneFromJid
- Diagnóstico e Logs do WhatsApp
- startSocket
- Diagnóstico e Logs do WhatsApp
- _extract_contact_name_via_llm
- TestShouldRunStyleLearning
- TestUpdateSoulWhatsappWithExamples
- TestSanitizeClassificationResult
- TestNormalizeBrazilianPhone
- test_empty_key_bug.py
- TestBestContactName
- _fetch_chat_history
- _push_personal_contacts_to_github
- TestDetectContactQuery
- TestNormalizeText
- post_llm_call
- Docker Compose
- graphify.md
- graphify.md
- capture_logs.sh
- diagnose_duplicates.sh
- watch_plugin.sh
- @whiskeysockets/baileys
- Chatwoot CRM
- Deploy Guide
- Andre Personal Assistant Mode
- Email Support Persona
- Email Support Mode
- EmpreendedorSerial Brand Identity
- Hermes Persona (SOUL)
- WhatsApp Support Persona
- Google Gemini API
- Gemini Developer Rules
- BeforeTool Hook Command
- Gemini Tool Hooks
- Google API Module
- OAuth2 Flow
- Auto-Update System
- GitHub Config Sync
- Multi-Profile System
- Customer Support Mode
- Gemini Key Test
- WhatsApp Env Vars Skill
- WhatsApp Logs Diagnostics Skill
- _push_personal_contacts_to_github
- _fetch_chat_history

## God Nodes (most connected - your core abstractions)
1. `BaseWhatsAppManagerTest` - 33 edges
2. `PluginConfig` - 24 edges
3. `_sync_contacts_from_db_internal()` - 24 edges
4. `pre_gateway_dispatch()` - 22 edges
5. `TestPostLlmCall` - 20 edges
6. `_normalize_brazilian_phone()` - 18 edges
7. `_normalize_text()` - 17 edges
8. `Como instalar o Hermes WhatsApp no Easypanel (do zero ao bot funcionando)` - 17 edges
9. `TestLLM` - 16 edges
10. `TestContactManagementAndSync` - 16 edges

## Surprising Connections (you probably didn't know these)
- `onMessagesUpsert()` --calls--> `matchesAllowedUser()`  [EXTRACTED]
  bridge.js → allowlist.js
- `load_contacts_cache()` --references--> `CONTACTS_CACHE_PATH`  [EXTRACTED]
  deploy/scripts/preview_soul.py → bridge.js
- `load_contacts_cache()` --references--> `CONTACTS_CACHE_PATH`  [EXTRACTED]
  deploy/scripts/test_style_learning.py → bridge.js
- `run_agent()` --calls--> `build_service()`  [EXTRACTED]
  deploy/scripts/support_agent.py → google_api.py
- `run_agent()` --calls--> `_extract_message_body()`  [EXTRACTED]
  deploy/scripts/support_agent.py → google_api.py

## Import Cycles
- None detected.

## Communities (145 total, 50 thin omitted)

### Community 0 - "Node.js WhatsApp Bridge"
Cohesion: 0.03
Nodes (36): _ACCEPTED_HOST_VALUES, activityCounters, adminRouter, ALLOWED_USERS, app, args, AUDIO_CACHE_DIR, BOT_STATE_FILE (+28 more)

### Community 1 - "Deploy Bridge Code Artifacts"
Cohesion: 0.03
Nodes (36): _ACCEPTED_HOST_VALUES, activityCounters, adminRouter, ALLOWED_USERS, app, args, AUDIO_CACHE_DIR, BOT_STATE_FILE (+28 more)

### Community 2 - "Bridge Documentation Artifacts"
Cohesion: 0.03
Nodes (36): _ACCEPTED_HOST_VALUES, activityCounters, adminRouter, ALLOWED_USERS, app, args, AUDIO_CACHE_DIR, BOT_STATE_FILE (+28 more)

### Community 3 - "Deploy Guidelines & Sync"
Cohesion: 0.05
Nodes (43): 1. Garantir as Credenciais do Google na Stack, 1. Pausa Global (`stop_bot` / `start_bot`), 1. Sincronização Periódica e Inteligente (GitHub ➔ Servidor), 2. Auto-Update de Código com Reinício Automático, 2. Pedir o Link ao Bot (No Console do Hermes ou no Telegram), 2. Silenciamento Temporário Automático (10 minutos), 3. Classificação Dinâmica e Blindagem de Contatos, 3. Entregar o Link de Retorno ao Bot (+35 more)

### Community 4 - "Deployment Configurations (Docker)"
Cohesion: 0.17
Nodes (11): 🕹️ Comandos de Controle (WhatsApp), 📋 Guia Passo a Passo - Configuração do Hermes Agent (Modo Misto), 🔒 Opção A: Sincronização Segura com Repositório Privado (Para Contatos Pessoais e Configurações Privadas), 🎨 PASSO 1: Fazer um Fork e Customizar no seu GitHub, 🛠️ PASSO 2: Subir a Stack e Chaves no Portainer, ⚡ PASSO 3: Rodar a Sincronização Automatizada (1 Clique), 📲 PASSO 4: Conectar o WhatsApp e Ativar, 🧪 PASSO 5: O Diagnóstico de Sucesso! (+3 more)

### Community 5 - "Debug Changelog Analysis"
Cohesion: 0.05
Nodes (37): 📂 Arquivos Modificados, Bridge (`bridge.js`), 🐛 Bug #1 — Truncamento de JSON na Classificação Gemini, 🐛 Bug #2 — Sync lia apenas 15 contatos, ignorando 28 reais, Causa raiz, 📋 Changelog & Sessão de Debug — `whatsapp-manager`, 🚀 Como Aplicar em Produção, Correção (+29 more)

### Community 7 - "Hermes Architecture Guidelines"
Cohesion: 0.05
Nodes (17): _resolve_chat_id com e sem mapeamento no _sender_to_chat., Após preencher _sender_to_chat com session_key, deve resolver., Lógica de split de mensagem em bolhas (sem I/O real)., Replica a lógica de split do _human_send., post_llm_call roteia corretamente owner vs contato., Contato não-owner deve chamar _human_send e retornar assistant_response vazio., Número de telefone deve ser redactado antes do _human_send., Prompts contêm as constraints de segurança corretas. (+9 more)

### Community 8 - "Deploy Support & Integrations"
Cohesion: 0.06
Nodes (30): 10. Configuração de Integrações e Pagamentos, 11. Instalações Múltiplas do Dealer, 12. Pagamento de Parcerias e Colaborações, 13. Problemas Técnicos em Plataformas de Parceria, 14. Problemas de Acesso ao Chatkanban, 15. Uso de APIs Diferentes no Agendamento V4 Chatwoot, 1. Api Connector, 1. Parcerias, Patrocínios e Anunciantes (Sponsorships) (+22 more)

### Community 9 - "WhatsApp Bot Env Vars"
Cohesion: 0.06
Nodes (17): _build_support_prompt retorna prompt de suporte/cliente., Verifica que o condicional de roteamento está correto no pre_llm_call.      Test, Prompt pessoal não usa whatsapp_soul (independente do SOUL_WHATSAPP.md)., Prompt de suporte não deve conter a persona do Amigo., Status ativo deve aparecer no prompt pessoal., Verifica o roteamento com os contatos reais do container., Contato 558699997003 (Suporte) deve ter relationship=Amigo., Não deve existir chaves com phone < 8 chars. (+9 more)

### Community 11 - "Base plugin tests & core logic"
Cohesion: 0.08
Nodes (12): LID presente no cache deve ser convertido para JID de telefone clássico., JIDs de telefone padrão devem passar sem alteração., LID não presente no cache deve ser retornado sem alteração de formato., Verifica que _resolve_phone_from_jid trata entrada vazia., Verifica que _resolve_phone_from_jid resolve LIDs mapeados., Verifica _resolve_chat_id com entrada no dicionário _sender_to_chat., Verifica _resolve_chat_id fazendo fallback por split., Verifica se _load_support_files carrega arquivos quando eles existem. (+4 more)

### Community 12 - "Additional test suites & edge cases"
Cohesion: 0.09
Nodes (12): Verifica processamento de áudio usando o modelo configurado em WHATSAPP_CLIENT_M, Verifica que o processamento de imagens se limita a no máximo 5 imagens por mens, Verifica que _process_media_message retorna None se GOOGLE_API_KEY estiver ausen, Verifica que _process_media_message retorna None se o evento não contiver mídia., Verifica que _process_media_message retorna None para tipos de mídia não suporta, Verifica que _process_media_message retorna None se o arquivo físico não existir, Verifica que pre_gateway_dispatch processa áudio, atualiza evento e persiste no, Verifica _get_media_info com atributos diretos no objeto. (+4 more)

### Community 14 - "Workspace Setup & Architecture Overview"
Cohesion: 0.10
Nodes (31): _classify_owner_intent(), _clear_owner_status(), _extract_update_fields_via_llm(), _find_contact_matches(), _generate_status_response(), _get_active_owner_status(), _get_media_info(), _human_send() (+23 more)

### Community 15 - "Test cases for user/bot interaction logic"
Cohesion: 0.11
Nodes (10): _check_bot_paused deve atualizar _lid_to_phone quando a resposta contiver lidToP, Verifica que WARNING+/ERROR vão para stderr e INFO vai para stdout via _WMLogHan, Verifica a atualização do banco SQLite com detecção dinâmica de colunas., Verifica _update_db_message com coluna de ID msg_id., Verifica _update_db_message com coluna de ID id., Verifica que _update_db_message retorna -1 quando não há nenhuma coluna de ID., Verifica que _update_db_message retorna -2 quando ocorre uma exceção., Verifica que _persist_transcription_to_db não cria thread se a inserção for imed (+2 more)

### Community 17 - "WhatsApp Manager execution tests"
Cohesion: 0.11
Nodes (6): Mensagem manual do dono para terceiro (chat_id != owner) deve retornar skip., Mensagem de cliente em chat silenciado deve retornar skip., Pre-dispatch deve honrar as variáveis WHATSAPP_OWNER_PROVIDER e WHATSAPP_CLIENT_, Verifica que perguntas sobre comandos retornam a mensagem de ajuda., Verifica que pre_gateway_dispatch intercepta o comando sync contacts do dono., TestMessageRoutingAndDispatch

### Community 18 - "Prompt building and context preparation"
Cohesion: 0.12
Nodes (19): _build_owner_context(), _build_personal_prompt(), _build_support_prompt(), _datetime_context_block(), _load_personal_contacts(), _load_support_files(), _owner_status_context_block(), pre_llm_call() (+11 more)

### Community 19 - "Bot Paused & Silencing checks"
Cohesion: 0.12
Nodes (18): _check_bot_paused(), _collect_andre_messages_by_relationship(), _fetch_all_bridge_contact_names(), _github_put_file(), Retorna o manual_relationship mais confiável para um contato.      Lê do existin, Sincroniza contatos do SQLite local para personal_contacts.json e envia para o G, Retorna True se há mensagens novas do André desde o último aprendizado., Coleta mensagens do André (from_me=1) agrupadas por relacionamento.      Retorna (+10 more)

### Community 20 - "Deploy Soul WhatsApp specifications"
Cohesion: 0.14
Nodes (13): 🚫 Diretrizes de Abordagem e Identificação (CRÍTICO), 🚫 Diretrizes de Decisões e Compromissos (CRÍTICO), 🚫 Diretrizes de Segurança e Restrições Rígidas, Exemplo 1:, Exemplo 2:, Exemplo 3:, Exemplo 4:, Exemplo 5: Cliente pergunta se é um bot (+5 more)

### Community 21 - "System README & deployment instructions"
Cohesion: 0.12
Nodes (16): 📐 Arquitetura do Container, 💬 Comandos no WhatsApp (SelfChat), 📲 Conectar o WhatsApp (QR Code), Deploy via Easypanel, Deploy via Portainer (Swarm), 🚀 Destaques da Versão v2026, 📁 Estrutura do Repositório, Hermes WhatsApp Plugin (+8 more)

### Community 22 - "_classify_contact_via_llm"
Cohesion: 0.25
Nodes (5): Verifica que o auto-updater do plugin usa git fetch/reset quando .git existe., Verifica que o classificador de contatos utiliza o modelo configurado no ambient, TestExternalServicesAndUpdates, _classify_contact_via_llm(), Classifica contatos usando a API do LLM (Gemini, OpenAI ou OpenRouter) com base

### Community 23 - "Contact management test cases"
Cohesion: 0.14
Nodes (4): Verifica se _build_owner_context inclui a diretriz e o histórico., Verifica se _build_personal_prompt constrói o prompt corretamente com campos opc, Verifica se _build_support_prompt inclui soul, regras e histórico., TestLLMContextAndPrompting

### Community 24 - "Contact name resolution & sync"
Cohesion: 0.29
Nodes (5): Testes para _best_contact_name., Nome que é só número não deve ser aceito como nome real., TestBestContactName, _best_contact_name(), Resolve o melhor nome disponivel para um contato.      Ordem de prioridade:

### Community 25 - "Deploy Package Dependencies (Express)"
Cohesion: 0.06
Nodes (22): _call_post(), _clear_state(), _make_post_llm_kwargs(), Número sul-africano +27 não vaza pela normalização brasileira., Número da Guiana Francesa +594 não vaza., Concorrência: somente uma thread envia, outras são suprimidas., Camada 2: turn-based dedup via _turn_key + _turn_sent., Duas sessions diferentes, mesmo turno — só uma passa. (+14 more)

### Community 26 - "Deploy Soul Conversational Examples"
Cohesion: 0.18
Nodes (10): Exemplo 1: Conversa com o André (Admin - MODO A), Exemplo 2: Conversa com Cliente (Suporte WhatsApp - MODO B), Exemplo 3: Conversa com Cliente (Suporte WhatsApp - MODO B), Exemplo 4: Conversa com Cliente (Suporte WhatsApp - MODO B), Exemplo 5: Conversa com Cliente (Suporte WhatsApp - MODO B), 📝 EXEMPLOS PRÁTICOS DE DIÁLOGOS (FEW-SHOT), 👤 MODO A: Assistente Pessoal do André (Quando falar com André Alencar), 💼 MODO B: Chatbot de Suporte Comercial (Quando falar com Clientes) (+2 more)

### Community 27 - "Bridge Node Package Dependencies"
Cohesion: 0.06
Nodes (22): Testes para o hook post_llm_call — filtragem, dedup de turno e typing., Contato recebe assistant_response filtrado., Owner sem EXEC no response: post_llm_call retorna None (Hermes envia normalmente, Tool results intermediários são suprimidos (espaço)., Afirmações de ação no sistema são substituídas por recusa., Números de telefone são redactados., Segundo post_llm_call para o mesmo turno é suprimido., Turno já enviado antes de um restart (chave carregada do disco) deve ser suprimi (+14 more)

### Community 28 - "Google API service builder"
Cohesion: 0.10
Nodes (28): datetime, get_minimax_credentials(), has_been_answered_by_us(), has_human_participated(), is_auto_reply(), is_out_of_hours(), is_promotional_or_system_email(), llm_chat_completion() (+20 more)

### Community 29 - "Root Package Dependencies"
Cohesion: 0.06
Nodes (31): dependencies, express, @hapi/boom, pino, qrcode, qrcode-terminal, @whiskeysockets/baileys, scripts (+23 more)

### Community 30 - "Gemini Classification unit tests"
Cohesion: 0.29
Nodes (9): analyze(), balance_braces(), call_gemini(), main(), Teste local do Gemini gemini-3.5-flash para diagnosticar truncamento de JSON.  U, Fecha chaves faltantes (mesma lógica proposta para _extract_json_from_text)., Tenta parsear fechando chaves faltantes., Extrai finishReason, tamanho e tenta parsear o JSON. (+1 more)

### Community 31 - "Bridge debounce & delay logic"
Cohesion: 0.17
Nodes (11): matchesAllowedUser(), parseAllowedUsers(), calcDebounceDelay(), flushDebounceBuffer(), getContextInfo(), getMessageContent(), normalizeWhatsAppId(), onMessagesUpsert() (+3 more)

### Community 32 - "Deploy Bridge debounce & delay"
Cohesion: 0.05
Nodes (18): _load_plugin(), Busca por nome Rosemery — pula se não estiver nos contatos., Busca por 'Suporte' não deve retornar o contato Rosemery., Número com espaços e hífens deve normalizar corretamente., Nome sem palavras em comum não deve retornar candidatos., _find_contact_matches deve retornar lista., Chamadas reais ao LLM — requer API key., Retorna contact_identifier ou contact_name (compatibilidade). (+10 more)

### Community 33 - "Bridge Docs debounce & delay"
Cohesion: 0.06
Nodes (32): 1. WhatsApp, 2. E-mail (Gmail API / Google Workspace), 3. LLM (MiniMax), Arquitetura do Hermes Agent, Arquivos de Configuração e Persona, Backup Failsafe do Core (STT Tradicional):, Como funciona:, Credenciais não aparecem no ambiente (+24 more)

### Community 34 - "Base WhatsApp Manager Test Suite"
Cohesion: 0.15
Nodes (9): BaseWhatsAppManagerTest, MockContext, Python unit tests for the whatsapp-manager plugin., Garante que atualização NL não sobrescreve tone/summary/guidelines., Garante que sync não substitui nome real por nome genérico 'Contato XXXX'., Testes para o hook pre_tool_call — bloqueio de tools para contatos., TestNLUpdateOwnerFieldsRestriction, TestPreToolCall (+1 more)

### Community 35 - "Deploy WhatsApp Logs & Diagnostics"
Cohesion: 0.08
Nodes (16): Testes para _update_contact_fields — busca em cascata por níveis 1-6., Nível 5: contato sem nome no JSON mas com sender_name no DB., Nível 6: bridge /contacts/search retorna resultado., Nível 1: busca por número de telefone., Testes para os passos 1–6 de _update_contact_fields., Passo 1: match exato por número de telefone., Passo 2: match exato de name., Passo 3: match por nickname. (+8 more)

### Community 36 - "Deploy Soul Email specifications"
Cohesion: 0.25
Nodes (7): 🕒 Atendimento Fora do Horário Comercial (Noite, Fins de Semana e Feriados), Exemplo 1: Dúvida sobre o curso de n8n, Exemplo 2: Cupom de desconto, 📝 EXEMPLOS DE RESPOSTAS POR E-MAIL (ESTILO FORMAL E ESTRUTURADO), 📧 Persona do Agente de Suporte e Vendas por E-mail (Gmail), 🚫 Restrições de Segurança e Privacidade, 🎭 Tom de Voz e Estilo de Conversa

### Community 37 - "WhatsApp Logs & Diagnostics skill"
Cohesion: 0.07
Nodes (27): 1. `WHATSAPP_OWNER_NUMBER` (CRÍTICA), 2. `HERMES_HOME`, 3. `WHATSAPP_HOME_CHANNEL`, Arquitetura, Arquivos de Configuração, Arquivos Principais, Banco de Dados, Bug Comum (+19 more)

### Community 38 - "Contact list loading & configurations sync"
Cohesion: 0.08
Nodes (20): Testes de regressão para bugs conhecidos no style learning., contact_name nunca deve ser 'André Alencar' — evita mostrar dono como destinatár, Nomes como 'Contato 558699997003' devem ser descartados como placeholder., Mensagens com saldo bancário devem ser bloqueadas., Mensagens normais não devem ser bloqueadas., CPF deve ser bloqueado., Senhas devem ser bloqueadas., _build_style_section_directly deve usar formato 'Nome: msg / André: resp'. (+12 more)

### Community 39 - "Deploy setup and GitHub integration scripts"
Cohesion: 0.80
Nodes (4): commit_file_to_github(), download_file(), safe_download(), setup.sh script

### Community 40 - "System Design and Pausing specifications"
Cohesion: 0.22
Nodes (8): 1. 🎛️ Pausa Global (Controlada na Ponte), 2. 🔇 Silenciamento Temporário (Conversas Específicas com Clientes), 3. 🔍 Detecção Cross-Session (Self-Chat), 4. 📇 Atualização de Contatos em Linguagem Natural, 5. 📊 Resumo Cumulativo (`full_summary`), 6. ⚡ Sync Não-Bloqueante, 📐 Arquitetura e Regras de Controle do Chatbot (WhatsApp), 🔄 Fluxo de Processamento (Resumo Técnico)

### Community 42 - "Transcription database persistence"
Cohesion: 0.07
Nodes (26): 1.1 Triplicação do cliente HTTP LLM (linhas 647–714), 1.2 Push para o GitHub duplicado em 3 lugares, 1.3 `register()` é um monólito de 867 linhas (linhas 1710–2577), 1.4 Limpeza de número de telefone duplicada 5+ vezes, 1.5 Abertura de arquivo de debug a cada mensagem (linha 2042), 1.6 `pre_llm_call` com 7 níveis de aninhamento (linhas 2195–2465), 1.7 Imports tardios (`import sqlite3`, `import threading`, etc.), 1. `whatsapp_manager.py` — 2.577 linhas (+18 more)

### Community 46 - "Graphify rules metadata"
Cohesion: 0.14
Nodes (24): CONTACTS_CACHE_PATH, build_lid_phone_map(), build_lookups(), load_contacts_cache(), log(), lookup_contact(), main(), norm_phone() (+16 more)

### Community 47 - "Deploy DB contacts synchronizer"
Cohesion: 0.12
Nodes (13): Testa a geração do SOUL_WHATSAPP.md com padrões do LLM + exemplos do Python., Cria lista de dicts com pares (contact_msg, andre_msg). None = sem contexto., Diálogo com contexto deve ter dois bullets separados, não indentado., Deve haver linha em branco entre pares de diálogo., O nome do contato deve aparecer como label no bullet., Nome do dono nunca deve aparecer como label do contato., Mensagem sem contexto deve ter só bullet do André., O sentinel ## EXEMPLOS REAIS DE ESCRITA deve estar no output. (+5 more)

### Community 50 - "Graphify workflows definition"
Cohesion: 0.11
Nodes (16): Testes para _normalize_brazilian_phone e _normalize_text., Número com 9 extra deve ser normalizado para 8 dígitos locais., Número sem 9 extra não deve ser alterado., Deve ignorar espaços, parênteses, hifens., Número não-brasileiro não deve ser alterado., Deve remover acentos e converter para minúsculas., TestNormalizeAndTextUtils, _dedup_personal_contacts() (+8 more)

### Community 57 - "🟠 Alto (estabilidade e segurança)"
Cohesion: 0.09
Nodes (22): 10. Permissões do `google_token.json` — `google_api.py`, 11. Duplicação 5x de `manual_relationship` migration — `whatsapp_manager.py`, 12. Caminhos hardcoded espalhados — `whatsapp_manager.py`, 13. `sessionDir` não utilizado — `allowlist.js` linha ~15, 14. Thread race em `_persist_transcription_to_db()` — `whatsapp_manager.py` linhas ~357-371, 15. `google_api.py` — cobertura zero, 16. `allowlist.js` — cobertura zero (isolada), 1. Path traversal em `/send-media` — `bridge.js` (+14 more)

### Community 58 - "TestOwnerCommands"
Cohesion: 0.07
Nodes (17): Testes para _check_chat_silenced., Segunda chamada dentro do TTL não deve fazer HTTP., Testes para comandos do owner em pre_gateway_dispatch., update contact Isabel relationship=Filha' executa e retorna skip., update contact Isabel' sem campos avisa o owner., update contact Isabel' sem campo=valor avisa o owner., NL update com contato encontrado retorna skip., Owner informa status: _save_owner_status é chamado e retorna skip. (+9 more)

### Community 59 - "Deploy do Plugin WhatsApp Manager"
Cohesion: 0.10
Nodes (20): 1.1 Verificar o que mudou, 1.2 Adicionar e commitar, 1.3 Push para o GitHub, 2.1 Acessar o Dashboard do Hermes, 2.2 Atualizar o plugin, Conferir logs do plugin, Conferir se o container subiu, Deploy do Plugin WhatsApp Manager (+12 more)

### Community 60 - "Plano de Implementação — Hermes WhatsApp Manager"
Cohesion: 0.10
Nodes (20): Critério global de conclusão, Dependências entre fases, Eixo A — Performance, ~~Eixo B — Integração Chatwoot~~ (CANCELADO), Fase A1 — Cache de arquivos lidos em toda mensagem, Fase A2 — Mover live classification para background ✅ IMPLEMENTADO, Fase A3 — Remover log de debug síncrono do hot path, Fase A4 — Cache de status bot/chat com paralelização dos checks (+12 more)

### Community 61 - "Como instalar o Hermes WhatsApp no Easypanel (do zero ao bot funcionando)"
Cohesion: 0.10
Nodes (19): Atualizar o plugin após mudanças, Comandos disponíveis no WhatsApp, Como instalar o Hermes WhatsApp no Easypanel (do zero ao bot funcionando), Estrutura dos arquivos de configuração, O que é o Hermes WhatsApp?, Passo 1 — Criar o serviço no Easypanel, Passo 2 — Configurar as variáveis de ambiente, Passo 3 — Configurar os domínios (+11 more)

### Community 62 - "TestCollectAndreMessagesByRelationship"
Cohesion: 0.17
Nodes (9): Testa coleta de mensagens do André agrupadas por relacionamento., contact_msgs_by_chat: dict {chat_id: [(body, timestamp), ...]}           mensage, Retorna um side_effect para patch('whatsapp_manager.Path') que distingue bridge_, Regressão: mensagem do contato chegando DEPOIS de André deve ser pareada (André, Regressão: a mesma mensagem do contato não deve ser pareada com múltiplas mensag, Regressão: mensagem do contato fora da janela de 24h não deve ser pareada., Regressão: quebras de linha extras na mensagem do contato devem ser normalizadas, Mensagens geradas pelo bot (presentes no state.db como assistant) devem ser excl (+1 more)

### Community 63 - "TestDedupPersonalContacts"
Cohesion: 0.15
Nodes (10): Testa _dedup_personal_contacts e _merge_contact_entries., @lid e @s.whatsapp.net devem coexistir — nenhum é removido., Campo 'lid' deve ser adicionado ao @s.whatsapp.net como cross-reference., Dados do @lid não são alterados — cada entrada mantém seus próprios valores., Dois @s.whatsapp.net com mesmo telefone (com/sem 9º dígito) devem ser mesclados., @lid sem telefone mapeado deve permanecer no dict., Campo 'lid' é adicionado ao @s.whatsapp.net mesmo sem entrada @lid no dict., Nome do dono no @lid não deve sobrescrever nome do @s.whatsapp.net. (+2 more)

### Community 64 - "TestExtractJsonFromText"
Cohesion: 0.16
Nodes (5): Testes para _extract_json_from_text., Testa _extract_json_from_text — parser robusto de JSON embutido em texto., TestExtractJsonFromText, _extract_json_from_text(), Extrai o primeiro objeto JSON válido de um texto usando balanceamento de chaves.

### Community 65 - "TestSanitizeSensitive"
Cohesion: 0.12
Nodes (3): Testa _sanitize_sensitive — segurança dos exemplos de diálogo., Valores pequenos como R$ 50 não devem ser bloqueados., TestSanitizeSensitive

### Community 66 - "TestProcessMediaMessage"
Cohesion: 0.21
Nodes (9): Testes para _process_media_message — transcrição de áudio e imagem., Patch das propriedades de config via __get__ no tipo., Sem API key: retorna None., Arquivo de mídia inexistente: retorna None., Tipo de mídia não suportado (vídeo, documento): retorna None., Gemini transcreve áudio com sucesso., Gemini descreve imagem com sucesso., Gemini falha e sem outros providers: retorna None. (+1 more)

### Community 67 - "TestLiveClassifyContact"
Cohesion: 0.17
Nodes (11): Testes para _live_classify_contact., Helper: configura mock SQLite para retornar stats e histórico., Contato novo com mensagens suficientes deve ser classificado via LLM., Sem mensagens no DB, deve retornar None sem chamar LLM., Dono nunca deve ser classificado — deve retornar None imediatamente., manual_relationship definido pelo dono deve sobrescrever o que o LLM classificar, Com poucas mensagens (< mínimo), deve usar classificação padrão sem chamar LLM., Resultado da classificação deve ser gravado em personal_contacts.json. (+3 more)

### Community 68 - "TestFullSummaryFunctions"
Cohesion: 0.19
Nodes (10): Testes para _call_llm_api., TestCallLlmApi, _call_llm_api(), _compress_full_summary(), Atualiza o full_summary de um contato com uma nova sessão de conversa.      Cham, Comprime um full_summary longo em 1-2 linhas para uso no contexto de atendimento, Atualiza full_summary para contatos com sessões novas no state.db.      Processa, Envia uma requisição HTTP POST para uma API de LLM e extrai o texto da resposta. (+2 more)

### Community 69 - "TestPreToolCall"
Cohesion: 0.14
Nodes (10): BasePlatformAdapter, Native Hermes Platform Adapter for WhatsApp Sidecar Bridge., Fallback Base class for standalone testing or direct invocation., Platform Adapter connecting Hermes Gateway to WhatsApp Baileys sidecar bridge., Query connection status from whatsapp-bridge., Return platform status dictionary for Gateway and Web UI Dashboard., Send a text message via whatsapp-bridge, passing through security firewall., Send typing presence indicator to chat. (+2 more)

### Community 71 - "TestBuildLidPhoneMap"
Cohesion: 0.29
Nodes (4): Testa _build_lid_phone_map — construção do mapa LID→telefone., TestBuildLidPhoneMap, _build_lid_phone_map(), Constrói mapa {lid → phone_digits} a partir de três fontes, em ordem de priorida

### Community 72 - "startSocket"
Cohesion: 0.29
Nodes (11): buildLidMap(), handleConnectionUpdate(), handleContactsSet(), handleContactsUpdate(), handleContactsUpsert(), handleMessagingHistorySet(), loadContactsCache(), onChatsUpdate() (+3 more)

### Community 73 - "google_api.py"
Cohesion: 0.22
Nodes (10): build_service(), _extract_body_from_part(), _extract_message_body(), _headers_dict(), Salva as credenciais atualizadas em TOKEN_PATH., Recebe uma mensagem bruta da Gmail API e retorna um dicionário     de headers co, Extrai o corpo da mensagem da Gmail API, suportando:       - Mensagens simples (, Navega recursivamente pelas partes MIME para extrair o corpo. (+2 more)

### Community 74 - "O que o agente deve fazer"
Cohesion: 0.18
Nodes (10): Autorização Google OAuth2 (Gmail), Configuração no Google Cloud Console, Notas Importantes, O que o agente deve fazer, Passo 1 — Verificar se o token já existe, Passo 2 — Verificar credenciais, Passo 3 — Gerar a URL de autorização, Passo 4 — Receber e processar (código ou URL) (+2 more)

### Community 75 - "TestPendingContactUpdate"
Cohesion: 0.13
Nodes (16): WhatsApp Manager Plugin Package Entry Point., commit_file_to_repo(), _ensure_google_libs(), _load_status_notified(), _load_turn_sent_from_disk(), _pull_and_merge_configurations(), Restaura _turn_sent do disco na inicialização, ignorando entradas expiradas., Instala as bibliotecas da Google API no venv do Hermes se ainda não estiverem di (+8 more)

### Community 76 - "test_utils_and_filters.py"
Cohesion: 0.29
Nodes (4): _patch_globals(), Patcha uma função no __globals__ do exec namespace de forma segura., _owner_status_context_block — injeção de status no prompt., TestOwnerStatusContextBlock

### Community 77 - "Research Sources — YouTube, Brave Search e Reddit"
Cohesion: 0.20
Nodes (9): Brave Search — busca web geral, Credenciais necessárias, Fluxo completo recomendado, Jina Reader — ler conteúdo de qualquer URL, Notas, Quando usar, Reddit — buscar posts e discussões, Research Sources — YouTube, Brave Search e Reddit (+1 more)

### Community 78 - "_detect_contact_query"
Cohesion: 0.33
Nodes (3): Testes para _detect_contact_query., TestDetectContactQuery, _detect_contact_query()

### Community 79 - "onMessagesUpsert"
Cohesion: 0.22
Nodes (9): calcDebounceDelay(), flushDebounceBuffer(), getContextInfo(), getMessageContent(), normalizeWhatsAppId(), onMessagesUpsert(), saveBotState(), sendWithTimeout() (+1 more)

### Community 80 - "test_nl_update.py"
Cohesion: 0.53
Nodes (8): call_api(), classify_intent(), extract_fields(), extract_json(), get_google_key(), get_model(), main(), run_case()

### Community 81 - "onMessagesUpsert"
Cohesion: 0.22
Nodes (9): calcDebounceDelay(), flushDebounceBuffer(), getContextInfo(), getMessageContent(), normalizeWhatsAppId(), onMessagesUpsert(), saveBotState(), sendWithTimeout() (+1 more)

### Community 82 - "_search_contact_by_name"
Cohesion: 0.47
Nodes (3): Testes para _search_contact_by_name., TestSearchContactByName, _search_contact_by_name()

### Community 83 - "TestFetchCrossSessionHistory"
Cohesion: 0.31
Nodes (5): Testes para _fetch_cross_session_history., Quando bridge_db não tem resultados, usa state.db., from_me=1 deve aparecer como 'André'; from_me=0 como sender_name ou 'Contato'., TestFetchCrossSessionHistory, _fetch_cross_session_history()

### Community 84 - "TestCheckChatSilenced"
Cohesion: 0.14
Nodes (8): Testes para _update_full_summary, _compress_full_summary e _sync_full_summaries., _update_full_summary deve retornar texto do LLM., Sem chave de API, _update_full_summary deve retornar None., _compress_full_summary deve retornar 1-2 frases do LLM., _sync_full_summaries deve passar ao LLM apenas mensagens role=user (contato)., Sem state.db, retorna 0 sem erros., _sync_full_summaries não deve processar o número do owner., TestFullSummaryFunctions

### Community 85 - "_resolve_contact_name_from_bridge"
Cohesion: 0.33
Nodes (4): Testes para _resolve_contact_name_from_bridge., TestResolveContactNameFromBridge, Consulta o Baileys via bridge para obter o pushName/contact name de um JID., _resolve_contact_name_from_bridge()

### Community 86 - "TestRunSyncInBackground"
Cohesion: 0.38
Nodes (4): Testes para _run_sync_in_background., TestRunSyncInBackground, Executa o sync de contatos em thread daemon, notificando o owner ao terminar., _run_sync_in_background()

### Community 87 - "_get_mime_type"
Cohesion: 0.33
Nodes (4): Testes para _get_mime_type., TestGetMimeType, _get_mime_type(), Retorna o tipo MIME adequado com base na extensão do arquivo.

### Community 88 - "startSocket"
Cohesion: 0.25
Nodes (8): buildLidMap(), handleConnectionUpdate(), handleContactsSet(), handleContactsUpdate(), handleContactsUpsert(), handleMessagingHistorySet(), onChatsUpdate(), startSocket()

### Community 89 - "test_audio_transcription.py"
Cohesion: 0.46
Nodes (7): find_audio_file(), get_google_key(), get_openai_key(), get_openrouter_key(), main(), transcribe_gemini(), transcribe_openai()

### Community 90 - "test_contact_search.py"
Cohesion: 0.54
Nodes (7): get_owner_phone(), is_owner_key(), load_contacts(), main(), normalize_br(), run_case(), search_by_identifier()

### Community 93 - "Diagnóstico e Logs do WhatsApp"
Cohesion: 0.25
Nodes (7): Diagnóstico e Logs do WhatsApp, Logs Físicos no Servidor, O que o agente deve fazer, Passo 1 — Obter o domínio do servidor, Passo 2 — Diagnóstico via Requisição Local (se executado pelo agente no terminal), Passo 3 — Apresentar as Instruções e URLs ao Usuário, Quando usar esta skill

### Community 94 - "startSocket"
Cohesion: 0.25
Nodes (8): buildLidMap(), handleConnectionUpdate(), handleContactsSet(), handleContactsUpdate(), handleContactsUpsert(), handleMessagingHistorySet(), onChatsUpdate(), startSocket()

### Community 95 - "Diagnóstico e Logs do WhatsApp"
Cohesion: 0.25
Nodes (7): Diagnóstico e Logs do WhatsApp, Logs Físicos no Servidor, O que o agente deve fazer, Passo 1 — Obter o domínio do servidor, Passo 2 — Diagnóstico via Requisição Local (se executado pelo agente no terminal), Passo 3 — Apresentar as Instruções e URLs ao Usuário, Quando usar esta skill

### Community 96 - "_extract_contact_name_via_llm"
Cohesion: 0.36
Nodes (4): Testes para _extract_contact_name_via_llm., TestExtractContactNameViaLLM, _extract_contact_name_via_llm(), Usa a LLM para extrair o nome do contato de uma mensagem em linguagem natural.

### Community 97 - "TestShouldRunStyleLearning"
Cohesion: 0.25
Nodes (5): Testa a gate function que decide se o aprendizado deve rodar., Sem arquivo de estado → deve retornar True., Sem banco de dados → deve retornar False., Qualquer exceção deve retornar False silenciosamente., TestShouldRunStyleLearning

### Community 101 - "test_empty_key_bug.py"
Cohesion: 0.48
Nodes (6): main(), normalize_br(), Passo 1 SEM o fix — replicando o bug original., Passo 1 COM o fix — phone < 8 chars é ignorado., step1_com_fix(), step1_sem_fix()

### Community 103 - "_fetch_chat_history"
Cohesion: 0.29
Nodes (4): Testes para o fluxo _pending_contact_update: não encontrado → pede número → apli, Quando contato não é encontrado, armazena pendência e pergunta o número., Quando dono responde com número, pendência é aplicada e removida., TestPendingContactUpdate

### Community 107 - "post_llm_call"
Cohesion: 0.33
Nodes (6): _log_suppressed(), _persist_turn_sent_to_disk(), post_llm_call(), Persiste uma chave de turno recém-enviada no arquivo de estado., Registra em arquivo toda tentativa de envio duplicado suprimida., Intercepta resposta do LLM:     - Para contatos: envia via _human_send (typing +

### Community 108 - "Docker Compose"
Cohesion: 0.50
Nodes (4): Docker Compose, Docker Compose EasyPanel, EasyPanel Config, Portainer Stack

### Community 140 - "_push_personal_contacts_to_github"
Cohesion: 0.38
Nodes (4): Testes para _push_personal_contacts_to_github., TestPushPersonalContactsToGithub, _push_personal_contacts_to_github(), Envia o arquivo personal_contacts.json local diretamente para o repositório do G

### Community 144 - "_fetch_chat_history"
Cohesion: 0.38
Nodes (4): Testes para _fetch_chat_history., TestFetchChatHistory, _fetch_chat_history(), Busca histórico de mensagens do servidor HTTP.

## Knowledge Gaps
- **464 isolated node(s):** `recentLogs`, `errorCounters`, `activityCounters`, `args`, `PORT` (+459 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **50 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TestDedupPersonalContacts` connect `TestDedupPersonalContacts` to `Base WhatsApp Manager Test Suite`, `Graphify workflows definition`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `TestOwnerCommands` connect `TestOwnerCommands` to `Base WhatsApp Manager Test Suite`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Why does `PluginConfig` connect `WhatsApp Manager Configurations` to `Workspace Setup & Architecture Overview`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **What connects `WhatsApp Manager Plugin Package Entry Point.`, `Native Hermes Platform Adapter for WhatsApp Sidecar Bridge.`, `Fallback Base class for standalone testing or direct invocation.` to the rest of the system?**
  _815 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Node.js WhatsApp Bridge` be split into smaller, more focused modules?**
  _Cohesion score 0.031746031746031744 - nodes in this community are weakly interconnected._
- **Should `Deploy Bridge Code Artifacts` be split into smaller, more focused modules?**
  _Cohesion score 0.03278688524590164 - nodes in this community are weakly interconnected._
- **Should `Bridge Documentation Artifacts` be split into smaller, more focused modules?**
  _Cohesion score 0.03278688524590164 - nodes in this community are weakly interconnected._