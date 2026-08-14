---
name: google-oauth
description: "Autoriza acesso ao Gmail via OAuth2 — gera a URL de login para o usuário clicar e salva o token de acesso."
category: integrations
---

# Autorização Google OAuth2 (Gmail)

Esta skill ensina o agente a gerar a URL de autorização OAuth2 do Google para que o André possa clicar e autorizar o acesso ao Gmail — sem precisar rodar nada em terminal.

---

## Quando usar esta skill

Use quando o usuário disser algo como:
- "autoriza o gmail"
- "quero autorizar o email"
- "google oauth"
- "gerar link de autorização do google"
- "o suporte de email não está funcionando"
- "google_token.json não existe"

---

## O que o agente deve fazer

### Passo 1 — Verificar se o token já existe

```bash
ls -la /opt/data/.hermes/google_token.json 2>/dev/null && echo "TOKEN EXISTE" || echo "TOKEN AUSENTE"
```

Se existir e for válido, informar o usuário e testar a conexão (Passo 4).
Se não existir, continuar com o Passo 2.

---

### Passo 2 — Verificar credenciais

```bash
python3 -c "
import os
client_id = os.getenv('GOOGLE_CLIENT_ID', '')
client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')
if client_id and client_secret:
    print(f'✅ GOOGLE_CLIENT_ID: {client_id[:20]}...')
    print(f'✅ GOOGLE_CLIENT_SECRET: {client_secret[:6]}...')
else:
    print('❌ Credenciais não encontradas no ambiente.')
    print('   Configure GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no Portainer.')
"
```

Se as credenciais não existirem → instruir o usuário a configurá-las no Portainer antes de continuar.

---

### Passo 3 — Gerar a URL de autorização

Execute o script abaixo **no container** para gerar a URL de autorização:

```bash
PYTHONPATH=/opt/hermes/.venv/lib/python3.13/site-packages python3 - <<'EOF'
import os, urllib.parse

try:
    from dotenv import load_dotenv
    load_dotenv("/opt/data/.env")
except ImportError:
    pass

client_id = os.getenv("GOOGLE_CLIENT_ID", "")
if not client_id:
    print("❌ GOOGLE_CLIENT_ID não configurado.")
    exit(1)

SCOPES = " ".join([
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
])

# Usa OOB: o Google exibe o código na página, sem redirect para localhost
params = urllib.parse.urlencode({
    "client_id": client_id,
    "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
    "response_type": "code",
    "scope": SCOPES,
    "access_type": "offline",
    "prompt": "consent",
})
auth_url = f"https://accounts.google.com/o/oauth2/auth?{params}"

print("\n" + "="*60)
print("👉 CLIQUE NESTE LINK PARA AUTORIZAR O GMAIL:")
print("="*60)
print(auth_url)
print("="*60)
print("\nO Google vai mostrar um CÓDIGO na tela (ex: 4/0Adk...)")
print("")
print("Após autorizar:")
print("  1. O browser vai abrir uma página com ERRO (site inacessível) — isso é normal!")
print("  2. Copie a URL completa da barra de endereço do browser")
print("  3. Envie essa URL para o agente")
EOF
```

**O agente deve:**
1. Apresentar a URL como link clicável
2. Avisar o usuário com esta mensagem exata:

> *"Clique no link e autorize. Depois da autorização o browser vai abrir uma página com erro (é normal, esperado). Copie a URL completa da barra de endereço do browser e me manda aqui."*

---

### Passo 4 — Receber e processar (código ou URL)

**REGRA DO AGENTE:** Assim que o usuário mandar qualquer coisa após a autorização, extrair o `code` e executar:
- Se contiver `code=` (URL completa como `http://localhost:8080/?state=...&code=4/0Adk...`): extrair automaticamente o parâmetro `code`
- Se começar com `4/`: usar diretamente
- Substituir `CODIGO_AQUI` no script pelo código extraído e executar

O script extrai o `code` da URL automaticamente:

```bash
PYTHONPATH=/opt/hermes/.venv/lib/python3.13/site-packages python3 - <<'EOF'
import os, json, urllib.request, urllib.parse
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv("/opt/data/.env")
except ImportError:
    pass

# ← SUBSTITUIR pelo código recebido do usuário (só o code, não a URL)
AUTH_CODE = "CODIGO_AQUI"

# Se vier URL completa, extrair o code
if "code=" in AUTH_CODE:
    parsed = urllib.parse.urlparse(AUTH_CODE)
    params = urllib.parse.parse_qs(parsed.query)
    AUTH_CODE = params.get("code", [""])[0]
    print(f"[info] Código extraído da URL: {AUTH_CODE[:20]}...")

client_id = os.getenv("GOOGLE_CLIENT_ID", "")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

if not client_id or not client_secret:
    print("❌ GOOGLE_CLIENT_ID ou GOOGLE_CLIENT_SECRET não configurados.")
    exit(1)

# Trocar o code por tokens via HTTP direto (sem state/code_verifier)
payload = urllib.parse.urlencode({
    "code": AUTH_CODE,
    "client_id": client_id,
    "client_secret": client_secret,
    "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
    "grant_type": "authorization_code",
}).encode()

req = urllib.request.Request(
    "https://oauth2.googleapis.com/token",
    data=payload,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST",
)

try:
    with urllib.request.urlopen(req) as resp:
        token_data = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    err = json.loads(e.read().decode())
    print(f"❌ Erro {e.code}: {err.get('error')} — {err.get('error_description')}")
    print("   Gere uma URL nova (Passo 3) e autorize novamente.")
    exit(1)

TOKEN_PATH = Path("/opt/data/.hermes/google_token.json")
TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(TOKEN_PATH, "w") as f:
    json.dump({
        "token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": token_data.get("scope", "").split(),
    }, f, indent=2)

print(f"✅ Token salvo em {TOKEN_PATH}")
print(f"   refresh_token: {'presente' if token_data.get('refresh_token') else 'AUSENTE — gere nova URL'}")
print("   O support_agent.py agora tem acesso ao Gmail.")
EOF
```

> **Se der erro `invalid_grant`:** o código já foi usado ou expirou (validade de ~10 min). Execute o Passo 3 novamente para gerar uma URL nova e autorize de novo.

---

### Passo 5 — Testar o acesso ao Gmail

```bash
PYTHONPATH=/opt/hermes/.venv/lib/python3.13/site-packages python3 - <<'EOF'
import sys
sys.path.insert(0, "/opt/data/.hermes/skills/productivity/google-workspace/scripts")

try:
    from dotenv import load_dotenv
    load_dotenv("/opt/data/.env")
except ImportError:
    pass

from google_api import build_service
service = build_service("gmail", "v1")
profile = service.users().getProfile(userId="me").execute()
print(f"✅ Gmail conectado com sucesso!")
print(f"   Conta: {profile.get('emailAddress')}")
print(f"   Total de mensagens: {profile.get('messagesTotal')}")
EOF
```

Se retornar a conta de e-mail, a autorização está completa e o agente de suporte de e-mail está pronto.

---

## Notas Importantes

- O token é salvo em `/opt/data/.hermes/google_token.json` (volume persistente — sobrevive a restarts)
- O `refresh_token` permite renovação automática sem precisar autorizar novamente
- Se a autorização expirar (raro com refresh_token), basta repetir o Passo 3
- As credenciais `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` devem ser do tipo **"Aplicativo de computador"** (não "Web") no Google Cloud Console

## Configuração no Google Cloud Console

Se as credenciais ainda não existem:
1. Acesse https://console.cloud.google.com/apis/credentials
2. Crie um **OAuth 2.0 Client ID** do tipo **"Aplicativo para computador"** (Desktop app)
3. Baixe o JSON e extraia `client_id` e `client_secret`
4. Configure no Portainer Stack como `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`
