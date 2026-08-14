#!/bin/bash
set -e

# Define o caminho base do Hermes dentro do container
BASE_DIR="/opt/data/.hermes"

# Carrega variáveis do arquivo .env local se existirem (para ler chaves de desenvolvedor)
if [ -f "/opt/data/.env" ]; then
    # Filtra linhas vazias ou comentários antes de exportar
    export $(grep -v '^#' /opt/data/.env | xargs) 2>/dev/null || true
fi
if [ -f "$BASE_DIR/.env" ]; then
    export $(grep -v '^#' "$BASE_DIR/.env" | xargs) 2>/dev/null || true
fi

# Parâmetros:
# $1: Usuário do GitHub do Cliente para o Fork do Código (opcional)
# $2: Token do GitHub do Desenvolvedor para baixar o código privado (opcional, do .env)
# $3: Repositório de configurações privado do Cliente (opcional)
# $4: Token do GitHub do Cliente para o repositório de configurações (opcional)

HERMES_SETUP_GITHUB_USER="${1:-${HERMES_SETUP_GITHUB_USER:-}}"
DEV_GITHUB_TOKEN="${2:-$DEV_GITHUB_TOKEN}"
CONFIG_REPO="${3:-${CONFIG_REPO:-hermes_agent_context_contatcs}}"
CONFIG_GITHUB_TOKEN="${4:-$CONFIG_GITHUB_TOKEN}"

# Consolidação dos repositórios e tokens:
CODE_USER="${HERMES_SETUP_GITHUB_USER:-${DEV_GITHUB_USER:-empreendedorserial}}"
CODE_TOKEN="$DEV_GITHUB_TOKEN"

echo "=========================================================="
echo "🤖 CONFIGURADOR DE MODO MISTO DO EMPREENDEDOR SERIAL 🤖"
echo "           GitHub User  : $CODE_USER"
echo "           Config Repo  : $CONFIG_REPO"
if [ -n "$CONFIG_GITHUB_TOKEN" ]; then
echo "           Config Token : CONFIGURADO (tamanho: ${#CONFIG_GITHUB_TOKEN} caracteres)"
else
echo "           Config Token : ⚠️ VAZIO OU NÃO CONFIGURADO NA STACK"
fi
echo "=========================================================="

mkdir -p "$BASE_DIR"
mkdir -p "/opt/data"

# Configura cabeçalhos de autenticação
CURL_CODE_AUTH_HEADER=""
if [ -n "$CODE_TOKEN" ]; then
    CURL_CODE_AUTH_HEADER="Authorization: token $CODE_TOKEN"
fi

CURL_CONFIG_AUTH_HEADER=""
if [ -n "$CONFIG_GITHUB_TOKEN" ]; then
    CURL_CONFIG_AUTH_HEADER="Authorization: token $CONFIG_GITHUB_TOKEN"
fi

# Função auxiliar para fazer download via curl tratando autenticação e erros
download_file() {
    local url="$1"
    local output="$2"
    local auth_header="$3"
    if [ -n "$auth_header" ]; then
        curl -f -H "$auth_header" -sSL "$url" -o "$output"
    else
        curl -f -sSL "$url" -o "$output"
    fi
}

# Função auxiliar para fazer download de forma segura (sem abortar com set -e)
safe_download() {
    local url="$1"
    local output="$2"
    local auth_header="$3"
    local desc="${4:-$output}"
    if download_file "$url" "$output" "$auth_header"; then
        return 0
    else
        echo "  ⚠️ Falha ao baixar $desc (pode ser seguro ignorar se o arquivo já existir localmente)."
        return 0
    fi
}

# URL Base para os arquivos de código (bridge, plugins, etc.) do GitHub
RAW_ROOT="https://raw.githubusercontent.com/$CODE_USER/hermes-whatsapp-mixed/main"
RAW_URL="$RAW_ROOT/deploy"

# URL para os arquivos de configuração (SOULs, regras, contatos)
if [ -n "$CONFIG_REPO" ] && [ -n "$CONFIG_GITHUB_TOKEN" ]; then
    if [[ "$CONFIG_REPO" == *"/"* ]]; then
        REPO_USER=$(echo "$CONFIG_REPO" | cut -d'/' -f1)
        REPO_NAME=$(echo "$CONFIG_REPO" | cut -d'/' -f2)
    else
        REPO_USER="$CODE_USER"
        REPO_NAME="$CONFIG_REPO"
        CONFIG_REPO="$REPO_USER/$REPO_NAME"
    fi

    echo "🔍 Verificando repositório de configurações '$REPO_USER/$REPO_NAME'..."
    HTTP_STATUS=$(curl -o /dev/null -s -w "%{http_code}" -H "$CURL_CONFIG_AUTH_HEADER" "https://api.github.com/repos/$REPO_USER/$REPO_NAME")
    if [ "$HTTP_STATUS" = "404" ] && [ -n "$CONFIG_GITHUB_TOKEN" ]; then
        echo "  ⚠️ Repositório de configurações '$REPO_USER/$REPO_NAME' não existe. Tentando criar automaticamente..."
        
        # Cria o repositório privado via API do GitHub
        CREATE_RESPONSE=$(curl -s -X POST \
            -H "Authorization: token $CONFIG_GITHUB_TOKEN" \
            -H "Accept: application/vnd.github+json" \
            -d "{\"name\":\"$REPO_NAME\",\"private\":true,\"description\":\"Hermes Configuration Repository\",\"auto_init\":true}" \
            "https://api.github.com/user/repos")
        
        CREATE_STATUS=$(echo "$CREATE_RESPONSE" | grep -o '"id":' | head -n1)
        if [ -n "$CREATE_STATUS" ]; then
            echo "  ✓ Repositório privado '$REPO_USER/$REPO_NAME' criado com sucesso!"
            
            # Aguarda 3 segundos para o GitHub processar a criação do repositório e do branch main
            sleep 3
            
            # Função para commitar arquivo via API do GitHub
            commit_file_to_github() {
                local file_path="$1"
                local github_path="$2"
                local content_base64=""
                if [ -f "$file_path" ]; then
                    if command -v base64 >/dev/null 2>&1; then
                        content_base64=$(base64 < "$file_path" | tr -d '\n\r')
                    elif command -v openssl >/dev/null 2>&1; then
                        content_base64=$(openssl base64 < "$file_path" | tr -d '\n\r')
                    fi
                fi
                
                if [ -n "$content_base64" ]; then
                    curl -s -o /dev/null -X PUT \
                        -H "Authorization: token $CONFIG_GITHUB_TOKEN" \
                        -H "Accept: application/vnd.github+json" \
                        -d "{\"message\":\"Add initial $github_path\",\"content\":\"$content_base64\",\"branch\":\"main\"}" \
                        "https://api.github.com/repos/$REPO_USER/$REPO_NAME/contents/$github_path"
                fi
            }
            
            # Baixa temporariamente os templates padrão para commitar no novo repo
            echo "  📤 Inicializando arquivos padrão no novo repositório..."
            mkdir -p /tmp/hermes-init-templates
            
            safe_download "$RAW_ROOT/SOUL.md" "/tmp/hermes-init-templates/SOUL.md" "$CURL_CODE_AUTH_HEADER" "template SOUL.md"
            safe_download "$RAW_ROOT/SOUL_WHATSAPP.md" "/tmp/hermes-init-templates/SOUL_WHATSAPP.md" "$CURL_CODE_AUTH_HEADER" "template SOUL_WHATSAPP.md"
            safe_download "$RAW_ROOT/SOUL_EMAIL.md" "/tmp/hermes-init-templates/SOUL_EMAIL.md" "$CURL_CODE_AUTH_HEADER" "template SOUL_EMAIL.md"
            safe_download "$RAW_ROOT/support_rules.md" "/tmp/hermes-init-templates/support_rules.md" "$CURL_CODE_AUTH_HEADER" "template support_rules.md"
            safe_download "$RAW_URL/personal_contacts.json.example" "/tmp/hermes-init-templates/personal_contacts.json" "$CURL_CODE_AUTH_HEADER" "template personal_contacts.json"
            
            commit_file_to_github "/tmp/hermes-init-templates/SOUL.md" "SOUL.md"
            commit_file_to_github "/tmp/hermes-init-templates/SOUL_WHATSAPP.md" "SOUL_WHATSAPP.md"
            commit_file_to_github "/tmp/hermes-init-templates/SOUL_EMAIL.md" "SOUL_EMAIL.md"
            commit_file_to_github "/tmp/hermes-init-templates/support_rules.md" "support_rules.md"
            commit_file_to_github "/tmp/hermes-init-templates/personal_contacts.json" "personal_contacts.json"
            
            rm -rf /tmp/hermes-init-templates
            echo "  ✓ Arquivos padrão inicializados no repositório privado."
        else
            echo "  ❌ Falha ao criar repositório automaticamente. Verifique se o CONFIG_GITHUB_TOKEN possui a permissão 'repo'."
        fi
    elif [ "$HTTP_STATUS" = "200" ]; then
        echo "  ✓ Repositório '$REPO_USER/$REPO_NAME' já existe."
    else
        echo "  ⚠️ Não foi possível verificar o repositório '$REPO_USER/$REPO_NAME' (HTTP $HTTP_STATUS)."
    fi

    CONFIG_URL="https://raw.githubusercontent.com/$CONFIG_REPO/main"
else
    CONFIG_URL="$RAW_URL"
fi



echo "⏳ 1. Baixando arquivos de configuração e personas..."

# Baixa e atualiza o arquivo de persona (SOUL.md) com fallback para o repositório do código base caso a URL de configuração falhe
if download_file "$CONFIG_URL/SOUL.md" "/opt/data/SOUL.md" "$CURL_CONFIG_AUTH_HEADER"; then
    cp "/opt/data/SOUL.md" "$BASE_DIR/SOUL.md"
    echo "  ✓ Persona SOUL.md sincronizada"
else
    echo "  ⚠️ Falha ao baixar SOUL.md de CONFIG_URL ($CONFIG_URL)"
    if [ "$CONFIG_URL" != "$RAW_URL" ]; then
        echo "  🔄 Tentando baixar do repositório de código público..."
        if download_file "$RAW_URL/SOUL.md" "/opt/data/SOUL.md" "$CURL_CODE_AUTH_HEADER"; then
            cp "/opt/data/SOUL.md" "$BASE_DIR/SOUL.md"
            echo "  ✓ Persona SOUL.md sincronizada (código base)"
        fi
    fi
fi

# Baixa e atualiza o arquivo de persona do suporte do WhatsApp
if download_file "$CONFIG_URL/SOUL_WHATSAPP.md" "/opt/data/SOUL_WHATSAPP.md" "$CURL_CONFIG_AUTH_HEADER"; then
    echo "  ✓ Persona do WhatsApp SOUL_WHATSAPP.md sincronizada"
else
    echo "  ⚠️ Falha ao baixar SOUL_WHATSAPP.md de CONFIG_URL"
    if [ "$CONFIG_URL" != "$RAW_URL" ]; then
        echo "  🔄 Tentando baixar do repositório de código público..."
        if download_file "$RAW_URL/SOUL_WHATSAPP.md" "/opt/data/SOUL_WHATSAPP.md" "$CURL_CODE_AUTH_HEADER"; then
            echo "  ✓ Persona do WhatsApp SOUL_WHATSAPP.md sincronizada (código base)"
        fi
    fi
fi

# Baixa e atualiza o arquivo de persona do suporte de E-mail
if download_file "$CONFIG_URL/SOUL_EMAIL.md" "/opt/data/SOUL_EMAIL.md" "$CURL_CONFIG_AUTH_HEADER"; then
    echo "  ✓ Persona de E-mail SOUL_EMAIL.md sincronizada"
else
    echo "  ⚠️ Falha ao baixar SOUL_EMAIL.md de CONFIG_URL"
    if [ "$CONFIG_URL" != "$RAW_URL" ]; then
        echo "  🔄 Tentando baixar do repositório de código público..."
        if download_file "$RAW_URL/SOUL_EMAIL.md" "/opt/data/SOUL_EMAIL.md" "$CURL_CODE_AUTH_HEADER"; then
            echo "  ✓ Persona de E-mail SOUL_EMAIL.md sincronizada (código base)"
        fi
    fi
fi

# Baixa e atualiza a base de conhecimento de suporte (support_rules.md)
if download_file "$CONFIG_URL/support_rules.md" "/opt/data/support_rules.md" "$CURL_CONFIG_AUTH_HEADER"; then
    echo "  ✓ Regras de suporte support_rules.md sincronizadas"
else
    echo "  ⚠️ Falha ao baixar support_rules.md de CONFIG_URL"
    if [ "$CONFIG_URL" != "$RAW_URL" ]; then
        echo "  🔄 Tentando baixar do repositório de código público..."
        if download_file "$RAW_URL/support_rules.md" "/opt/data/support_rules.md" "$CURL_CODE_AUTH_HEADER"; then
            echo "  ✓ Regras de suporte support_rules.md sincronizadas (código base)"
        fi
    fi
fi

# Baixa personal_contacts.json se estiver usando repositório privado válido
if [ -n "$CONFIG_REPO" ] && [ -n "$CONFIG_GITHUB_TOKEN" ]; then
    if download_file "$CONFIG_URL/personal_contacts.json" "/opt/data/personal_contacts.json" "$CURL_CONFIG_AUTH_HEADER"; then
        echo "  ✓ Contatos pessoais personal_contacts.json sincronizados com sucesso"
    else
        echo "  - personal_contacts.json não encontrado no repositório, mantendo o arquivo local se existir"
    fi
fi

# Instala o plugin whatsapp-manager automaticamente caso não esteja presente no volume
if [ ! -d "/opt/data/.hermes/plugins/whatsapp-manager" ]; then
    echo "⏳ Instalando o plugin whatsapp-manager..."
    mkdir -p "/opt/data/.hermes/plugins/whatsapp-manager"
    safe_download "$RAW_ROOT/plugin.yaml"     "/opt/data/.hermes/plugins/whatsapp-manager/plugin.yaml" "$CURL_CODE_AUTH_HEADER" "plugin.yaml"
    safe_download "$RAW_ROOT/__init__.py"     "/opt/data/.hermes/plugins/whatsapp-manager/__init__.py" "$CURL_CODE_AUTH_HEADER" "__init__.py"
    safe_download "$RAW_ROOT/whatsapp_manager.py" "/opt/data/.hermes/plugins/whatsapp-manager/whatsapp_manager.py" "$CURL_CODE_AUTH_HEADER" "whatsapp_manager.py"
    safe_download "$RAW_ROOT/adapter.py"      "/opt/data/.hermes/plugins/whatsapp-manager/adapter.py" "$CURL_CODE_AUTH_HEADER" "adapter.py"
    safe_download "$RAW_ROOT/bridge.js"       "/opt/data/.hermes/plugins/whatsapp-manager/bridge.js" "$CURL_CODE_AUTH_HEADER" "bridge.js"
    safe_download "$RAW_ROOT/package.json"    "/opt/data/.hermes/plugins/whatsapp-manager/package.json" "$CURL_CODE_AUTH_HEADER" "package.json"
    safe_download "$RAW_ROOT/google_api.py"   "/opt/data/.hermes/plugins/whatsapp-manager/google_api.py" "$CURL_CODE_AUTH_HEADER" "google_api.py"
    
    # Instalar skills bundled do plugin
    mkdir -p "/opt/data/.hermes/plugins/whatsapp-manager/skills/google-oauth"
    safe_download "$RAW_ROOT/skills/google-oauth/SKILL.md" "/opt/data/.hermes/plugins/whatsapp-manager/skills/google-oauth/SKILL.md" "$CURL_CODE_AUTH_HEADER" "skills/google-oauth/SKILL.md"
    mkdir -p "/opt/data/.hermes/plugins/whatsapp-manager/skills/research-sources"
    safe_download "$RAW_ROOT/skills/research-sources/SKILL.md" "/opt/data/.hermes/plugins/whatsapp-manager/skills/research-sources/SKILL.md" "$CURL_CODE_AUTH_HEADER" "skills/research-sources/SKILL.md"
    mkdir -p "/opt/data/.hermes/plugins/whatsapp-manager/skills/whatsapp-logs-diagnostics"
    safe_download "$RAW_ROOT/skills/whatsapp-logs-diagnostics/SKILL.md" "/opt/data/.hermes/plugins/whatsapp-manager/skills/whatsapp-logs-diagnostics/SKILL.md" "$CURL_CODE_AUTH_HEADER" "skills/whatsapp-logs-diagnostics/SKILL.md"
    echo "  ✓ Plugin whatsapp-manager instalado com sucesso (incluindo skills e google_api)."
else
    if [ -d "/opt/data/.hermes/plugins/whatsapp-manager/.git" ]; then
        echo "🔄 /opt/data/.hermes/plugins/whatsapp-manager é um repositório Git. Atualizando via Git..."
        (
            cd "/opt/data/.hermes/plugins/whatsapp-manager" || exit 1
            # Limpa modificações locais nos arquivos do plugin para evitar conflitos de merge
            git reset --hard HEAD
            # Realiza a atualização via pull
            if [ -n "$CODE_TOKEN" ]; then
                git -c http.extraHeader="Authorization: token $CODE_TOKEN" pull origin main || git pull origin main
            else
                git pull origin main
            fi
        )
        if [ $? -eq 0 ]; then
            echo "  ✓ Plugin atualizado via Git pull com sucesso."
        else
            echo "  ⚠️ Falha ao atualizar via Git pull. Tentando fallback para atualização de arquivos individuais..."
            # Fallback para download individual caso falhe por qualquer motivo
            safe_download "$RAW_ROOT/__init__.py"   "/opt/data/.hermes/plugins/whatsapp-manager/__init__.py" "$CURL_CODE_AUTH_HEADER" "__init__.py"
            safe_download "$RAW_ROOT/whatsapp_manager.py" "/opt/data/.hermes/plugins/whatsapp-manager/whatsapp_manager.py" "$CURL_CODE_AUTH_HEADER" "whatsapp_manager.py"
            safe_download "$RAW_ROOT/adapter.py"    "/opt/data/.hermes/plugins/whatsapp-manager/adapter.py" "$CURL_CODE_AUTH_HEADER" "adapter.py"
            safe_download "$RAW_ROOT/google_api.py" "/opt/data/.hermes/plugins/whatsapp-manager/google_api.py" "$CURL_CODE_AUTH_HEADER" "google_api.py"
            mkdir -p "/opt/data/.hermes/plugins/whatsapp-manager/skills/google-oauth"
            safe_download "$RAW_ROOT/skills/google-oauth/SKILL.md" "/opt/data/.hermes/plugins/whatsapp-manager/skills/google-oauth/SKILL.md" "$CURL_CODE_AUTH_HEADER" "skills/google-oauth/SKILL.md"
            mkdir -p "/opt/data/.hermes/plugins/whatsapp-manager/skills/research-sources"
            safe_download "$RAW_ROOT/skills/research-sources/SKILL.md" "/opt/data/.hermes/plugins/whatsapp-manager/skills/research-sources/SKILL.md" "$CURL_CODE_AUTH_HEADER" "skills/research-sources/SKILL.md"
            mkdir -p "/opt/data/.hermes/plugins/whatsapp-manager/skills/whatsapp-logs-diagnostics"
            safe_download "$RAW_ROOT/skills/whatsapp-logs-diagnostics/SKILL.md" "/opt/data/.hermes/plugins/whatsapp-manager/skills/whatsapp-logs-diagnostics/SKILL.md" "$CURL_CODE_AUTH_HEADER" "skills/whatsapp-logs-diagnostics/SKILL.md"
            echo "  ✓ __init__.py, whatsapp_manager.py, adapter.py, google_api.py e skills atualizados via download."
        fi
    else
        echo "  - Plugin whatsapp-manager já instalado (não-Git). Atualizando __init__.py, whatsapp_manager.py, adapter.py, skills e módulos..."
        safe_download "$RAW_ROOT/__init__.py"   "/opt/data/.hermes/plugins/whatsapp-manager/__init__.py" "$CURL_CODE_AUTH_HEADER" "__init__.py"
        safe_download "$RAW_ROOT/whatsapp_manager.py" "/opt/data/.hermes/plugins/whatsapp-manager/whatsapp_manager.py" "$CURL_CODE_AUTH_HEADER" "whatsapp_manager.py"
        safe_download "$RAW_ROOT/adapter.py"    "/opt/data/.hermes/plugins/whatsapp-manager/adapter.py" "$CURL_CODE_AUTH_HEADER" "adapter.py"
        safe_download "$RAW_ROOT/google_api.py" "/opt/data/.hermes/plugins/whatsapp-manager/google_api.py" "$CURL_CODE_AUTH_HEADER" "google_api.py"
        mkdir -p "/opt/data/.hermes/plugins/whatsapp-manager/skills/google-oauth"
        safe_download "$RAW_ROOT/skills/google-oauth/SKILL.md" "/opt/data/.hermes/plugins/whatsapp-manager/skills/google-oauth/SKILL.md" "$CURL_CODE_AUTH_HEADER" "skills/google-oauth/SKILL.md"
        mkdir -p "/opt/data/.hermes/plugins/whatsapp-manager/skills/research-sources"
        safe_download "$RAW_ROOT/skills/research-sources/SKILL.md" "/opt/data/.hermes/plugins/whatsapp-manager/skills/research-sources/SKILL.md" "$CURL_CODE_AUTH_HEADER" "skills/research-sources/SKILL.md"
        mkdir -p "/opt/data/.hermes/plugins/whatsapp-manager/skills/whatsapp-logs-diagnostics"
        safe_download "$RAW_ROOT/skills/whatsapp-logs-diagnostics/SKILL.md" "/opt/data/.hermes/plugins/whatsapp-manager/skills/whatsapp-logs-diagnostics/SKILL.md" "$CURL_CODE_AUTH_HEADER" "skills/whatsapp-logs-diagnostics/SKILL.md"
        echo "  ✓ __init__.py, whatsapp_manager.py, google_api.py e skills atualizados."
    fi
fi

# Baixa o modelo de config.yaml se ele não existir localmente
if [ ! -f "$BASE_DIR/config.yaml" ]; then
    safe_download "$RAW_URL/config.yaml.example" "$BASE_DIR/config.yaml" "$CURL_CODE_AUTH_HEADER" "config.yaml"
    echo "  ✓ config.yaml inicial configurado."
else
    echo "  - config.yaml já existe localmente, pulando."
    # Garantir que max_turns seja reduzido de 60 para 8 para evitar custos abusivos no Gemini
    if grep -q "max_turns: 60" "$BASE_DIR/config.yaml"; then
        echo "🔄 Atualizando max_turns de 60 para 8 no seu config.yaml para reduzir custos do Gemini..."
        sed -i.bak 's/max_turns: 60/max_turns: 8/g' "$BASE_DIR/config.yaml" 2>/dev/null || sed -i 's/max_turns: 60/max_turns: 8/g' "$BASE_DIR/config.yaml"
        rm -f "$BASE_DIR/config.yaml.bak"
    fi
    # Garantir que migre gemini-3.5-flash para gemini-3.1-flash-lite para reduzir custos
    if grep -q "gemini-3.5-flash" "$BASE_DIR/config.yaml"; then
        echo "🔄 Atualizando modelo padrão de gemini-3.5-flash para gemini-3.1-flash-lite no seu config.yaml..."
        sed -i.bak 's/gemini-3.5-flash/gemini-3.1-flash-lite/g' "$BASE_DIR/config.yaml" 2>/dev/null || sed -i 's/gemini-3.5-flash/gemini-3.1-flash-lite/g' "$BASE_DIR/config.yaml"
        rm -f "$BASE_DIR/config.yaml.bak"
    fi
fi

# Permite configurar max_turns via variável de ambiente da stack (Portainer/Easypanel)
ENV_MAX_TURNS="${MAX_TURNS:-$HERMES_MAX_TURNS}"
if [ -n "$ENV_MAX_TURNS" ] && [ -f "$BASE_DIR/config.yaml" ]; then
    echo "⚙️ Configurando max_turns para $ENV_MAX_TURNS conforme variável de ambiente da stack..."
    sed -i.bak "s/max_turns: [0-9]*/max_turns: $ENV_MAX_TURNS/g" "$BASE_DIR/config.yaml" 2>/dev/null || sed -i "s/max_turns: [0-9]*/max_turns: $ENV_MAX_TURNS/g" "$BASE_DIR/config.yaml"
    rm -f "$BASE_DIR/config.yaml.bak"
fi

# Configuração de Autenticação do Dashboard (zero-config para o cliente final)
DASH_USER="${HERMES_DASHBOARD_BASIC_AUTH_USERNAME:-admin}"
DASH_PASS_PLAIN="${HERMES_DASHBOARD_PASSWORD:-${HERMES_DASH_PASSWORD:-${API_SERVER_KEY:-admin123}}}"

PYTHON_BIN="/opt/hermes/.venv/bin/python"
[ ! -x "$PYTHON_BIN" ] && PYTHON_BIN="python3"

echo "🔒 Configurando autenticação automática do Dashboard..."
$PYTHON_BIN -c "import os, yaml; from plugins.dashboard_auth.basic import hash_password; usr=os.environ.get('HERMES_DASHBOARD_BASIC_AUTH_USERNAME') or '$DASH_USER'; pwd=os.environ.get('HERMES_DASHBOARD_PASSWORD') or os.environ.get('API_SERVER_KEY') or '$DASH_PASS_PLAIN'; h=hash_password(pwd); paths=['$BASE_DIR/config.yaml', os.path.expanduser('~/.hermes/config.yaml')]; [os.makedirs(os.path.dirname(p), exist_ok=True) for p in paths]; exec('''for p in paths:\n  try:\n    with open(p,\"r\") as f: cfg=yaml.safe_load(f) or {}\n  except Exception: cfg={}\n  if not isinstance(cfg, dict): cfg={}\n  dash=cfg.get(\"dashboard\")\n  if not isinstance(dash, dict): dash={\"enabled\": True, \"host\": \"0.0.0.0\", \"port\": 9119}\n  dash[\"enabled\"]=True; dash[\"host\"]=\"0.0.0.0\"; dash[\"port\"]=9119\n  dash[\"basic_auth\"]={\"username\": usr, \"password_hash\": h}\n  cfg[\"dashboard\"]=dash\n  cfg[\"session_reset\"]={\"notify_user\": False}\n  disp=cfg.get(\"display\") or {}\n  if not isinstance(disp, dict): disp={}\n  disp[\"show_system_header\"]=False\n  disp[\"tool_progress\"]=\"off\"\n  disp[\"platforms\"]={\"whatsapp\": {\"tool_progress\": \"off\"}}\n  cfg[\"display\"]=disp\n  if \"model\" not in cfg or not isinstance(cfg[\"model\"], dict):\n    cfg[\"model\"]={\"default\": \"gemini-3.1-flash-lite\", \"provider\": \"gemini\"}\n  with open(p,\"w\") as f: yaml.dump(cfg, f, default_flow_style=False)\n''')" 2>/dev/null || true
echo "  ✓ Autenticação e limpeza de mensagens do Dashboard/Config configuradas! (Usuário: $DASH_USER | Senha: $DASH_PASS_PLAIN)"

# Baixa o modelo de chaves de API (.env) se ele não existir localmente
if [ ! -f "$BASE_DIR/.env" ]; then
    if ! download_file "$RAW_URL/env.example" "$BASE_DIR/.env" "$CURL_CODE_AUTH_HEADER"; then
        safe_download "$RAW_URL/.env.example" "$BASE_DIR/.env" "$CURL_CODE_AUTH_HEADER" ".env"
    fi
    echo "  ✓ Arquivo de chaves .env inicial criado."
else
    echo "  - Arquivo .env já existe localmente, pulando."
fi


echo "⏳ 2. Baixando e aplicando o Patch do WhatsApp..."
# Sincroniza o arquivo bridge.js modificado diretamente do repositório
mkdir -p "/opt/data/.hermes/platforms/whatsapp/bridge"
safe_download "$RAW_ROOT/docs/bridge-artifacts/bridge.js" "/opt/data/.hermes/platforms/whatsapp/bridge/bridge.js" "$CURL_CODE_AUTH_HEADER" "bridge.js"
safe_download "$RAW_ROOT/docs/bridge-artifacts/package.json" "/opt/data/.hermes/platforms/whatsapp/bridge/package.json" "$CURL_CODE_AUTH_HEADER" "package.json"
echo "  ✓ Arquivos bridge.js e package.json sincronizados."

# Corrige o desalinhamento de caminhos da sessão do WhatsApp (symlink antiga -> nova)
mkdir -p "/opt/data/.hermes/platforms/whatsapp/session"
if [ -d "/opt/data/.hermes/whatsapp/session" ] && [ ! -L "/opt/data/.hermes/whatsapp/session" ]; then
    echo "  🔄 Movendo arquivos de sessão do caminho antigo para o novo..."
    mv /opt/data/.hermes/whatsapp/session/* /opt/data/.hermes/platforms/whatsapp/session/ 2>/dev/null || true
    rm -rf "/opt/data/.hermes/whatsapp/session"
fi
if [ ! -e "/opt/data/.hermes/whatsapp/session" ]; then
    ln -sfn "/opt/data/.hermes/platforms/whatsapp/session" "/opt/data/.hermes/whatsapp/session"
    echo "  ✓ Link de compatibilidade da sessão configurado automaticamente."
fi

# Baixa os scripts do agente de suporte de e-mail direto do repositório
mkdir -p "/opt/data/.hermes/scripts"
safe_download "$RAW_URL/scripts/support_agent.py" "/opt/data/.hermes/scripts/support_agent.py" "$CURL_CODE_AUTH_HEADER" "support_agent.py"
chmod +x "/opt/data/.hermes/scripts/support_agent.py"
echo "  ✓ support_agent.py sincronizado."

# Baixa o script de sincronização de contatos a partir do banco de dados SQLite
safe_download "$RAW_URL/scripts/sync_contacts_from_db.py" "/opt/data/.hermes/scripts/sync_contacts_from_db.py" "$CURL_CODE_AUTH_HEADER" "sync_contacts_from_db.py"
chmod +x "/opt/data/.hermes/scripts/sync_contacts_from_db.py"
echo "  ✓ sync_contacts_from_db.py sincronizado."

# Baixa o módulo google_api.py (autenticação OAuth2 Gmail)
mkdir -p "/opt/data/.hermes/skills/productivity/google-workspace/scripts"
safe_download "$RAW_URL/scripts/google_api.py" "/opt/data/.hermes/skills/productivity/google-workspace/scripts/google_api.py" "$CURL_CODE_AUTH_HEADER" "google_api.py"
echo "  ✓ google_api.py sincronizado."

# Baixa o script de autorização OAuth2 (necessário na primeira vez)
safe_download "$RAW_URL/scripts/authorize_google.py" "/opt/data/.hermes/scripts/authorize_google.py" "$CURL_CODE_AUTH_HEADER" "authorize_google.py"
chmod +x "/opt/data/.hermes/scripts/authorize_google.py"
echo "  ✓ authorize_google.py sincronizado."

# Baixa e executa o patch_whatsapp.py para verificar a integridade
safe_download "$RAW_URL/patch_whatsapp.py" "/tmp/patch_whatsapp.py" "$CURL_CODE_AUTH_HEADER" "patch_whatsapp.py"
if [ -f "/tmp/patch_whatsapp.py" ]; then
    python3 /tmp/patch_whatsapp.py || echo "  ⚠️ Falha ao executar patch_whatsapp.py"
fi


echo "⏳ 3. Instalando dependências da ponte e de geração de imagem do QR Code..."

# Instala dependências Node.js da ponte do WhatsApp (necessário para iniciar o pareamento)
if [ -d "/opt/hermes/scripts/whatsapp-bridge" ]; then
    (cd /opt/hermes/scripts/whatsapp-bridge && npm install --no-fund --no-audit --silent 2>/dev/null) \
        && echo "  ✓ Dependências Node.js da ponte do WhatsApp instaladas." \
        || echo "  ⚠️  npm install falhou (pode ser seguro ignorar se já instalado)."
else
    echo "  - Pasta whatsapp-bridge não encontrada, pulando npm install."
fi

# Instala qrcode e pillow no venv do Hermes
if [ -x "/opt/hermes/.venv/bin/python" ]; then
    uv pip install --python /opt/hermes/.venv/bin/python qrcode pillow --quiet 2>/dev/null \
        && echo "  ✓ Bibliotecas qrcode e pillow instaladas no ambiente virtual." \
        || echo "  ⚠️  uv pip install falhou (pode ser seguro ignorar se já instalado)."

    # Instala dependências do Gmail API
    uv pip install --python /opt/hermes/.venv/bin/python \
        google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client \
        --quiet 2>/dev/null \
        && echo "  ✓ Bibliotecas Google API instaladas no ambiente virtual." \
        || echo "  ⚠️  Instalação das libs Google falhou (verificar conectividade)."
else
    echo "  - Ambiente virtual do Hermes não encontrado em /opt/hermes/.venv, pulando."
fi

# Sincroniza e desativa todas as ferramentas no profile de atendimento WhatsApp por padrão
mkdir -p "/opt/data/.hermes/profiles/whatsapp"
cp "/opt/data/SOUL_WHATSAPP.md" "/opt/data/.hermes/profiles/whatsapp/SOUL.md" 2>/dev/null || true
$PYTHON_BIN -c "import yaml, os; p='/opt/data/.hermes/profiles/whatsapp/config.yaml'; os.makedirs(os.path.dirname(p), exist_ok=True); ts_list=['file_operations','code_execution','vision','image_generation','video_analysis','video_generation','web_search','browser','terminal','text_to_speech','skills','task_planning','todo','memory','context_engine','session_search','clarifying_questions','clarify','task_delegation','delegate_task','cronjob','cron_jobs','home_assistant','spotify','discord','discord_admin','yuanbao','computer_use','x_search','twitter_search']; cfg={'model': {'default': 'gemini-3.1-flash-lite', 'provider': 'gemini'}, 'agent': {'tool_use_enforcement': 'disabled'}, 'toolsets': [], 'disabled_toolsets': ts_list, 'tools': [], 'skills': {'enabled': False}, 'terminal': {'backend': 'disabled'}, 'display': {'show_system_header': False, 'tool_progress': 'off'}}; open(p, 'w').write(yaml.dump(cfg, default_flow_style=False))" 2>/dev/null || true
echo "  ✓ Profile de WhatsApp configurado com a persona SOUL_WHATSAPP.md e ferramentas desativadas por padrão."

# Se o profile de E-mail do Hermes já existir, sincroniza também o SOUL_EMAIL
if [ -d "/opt/data/.hermes/profiles/email" ]; then
    cp "/opt/data/SOUL_EMAIL.md" "/opt/data/.hermes/profiles/email/SOUL.md"
    echo "  ✓ Profile de E-mail atualizado com a persona SOUL_EMAIL.md"
fi

echo "=========================================================="
echo "🎉 SINCRONIZAÇÃO E CONFIGURAÇÃO CONCLUÍDAS COM SUCESSO!"
echo "=========================================================="
echo "Seu Hermes foi sincronizado com o seu GitHub Fork ($GITHUB_USER)!"
if [ -n "$CONFIG_REPO" ]; then
echo "Configurações e personas sincronizadas com $CONFIG_REPO!"
fi
echo "=========================================================="
