#!/usr/bin/env python3
"""
authorize_google.py — Gera o google_token.json via OAuth2 (primeira vez)

Execute UMA VEZ no container para autorizar o acesso ao Gmail:
  cd /opt/data && PYTHONPATH=/opt/hermes/.venv/lib/python3.13/site-packages \
    python3 .hermes/scripts/authorize_google.py

Requisitos:
  - GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET configurados no ambiente ou em /opt/data/.env
  - Acesso à internet para abrir a URL de autorização
  - O redirect_uri configurado no Google Cloud Console deve incluir: http://localhost:8080

Após autorizar, o refresh_token é salvo em /opt/data/.hermes/google_token.json
e o support_agent.py usa automaticamente esse token sem precisar de novos logins.
"""

import os
import json
import sys

PERSISTENT_DATA_DIR = "/opt/data"
HERMES_HOME = os.path.join(PERSISTENT_DATA_DIR, ".hermes")
TOKEN_PATH = os.path.join(HERMES_HOME, "google_token.json")
DOTENV_PATH = os.path.join(PERSISTENT_DATA_DIR, ".env")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

try:
    from dotenv import load_dotenv
    load_dotenv(DOTENV_PATH)
except ImportError:
    pass

client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

if not client_id or not client_secret:
    print("❌ GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET não encontrados.")
    print(f"   Configure-os em {DOTENV_PATH} ou nas variáveis de ambiente do Portainer.")
    sys.exit(1)

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
except ImportError:
    print("❌ Bibliotecas Google não encontradas. Execute:")
    print("   uv pip install --python /opt/hermes/.venv/bin/python google-auth-oauthlib google-api-python-client")
    sys.exit(1)

client_config = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uris": ["http://localhost:8080", "urn:ietf:wg:oauth:2.0:oob"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

print("🔐 Iniciando fluxo de autorização OAuth2 com o Google...")
print("   Será aberta uma URL no browser (ou cole no browser manualmente).")
print()

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

# Tentar porta local. Se não funcionar (sem browser), usar OOB.
try:
    creds = flow.run_local_server(port=8080, prompt="consent", open_browser=True)
except Exception:
    print("⚠️  Browser local não disponível. Use o modo manual:")
    auth_url, _ = flow.authorization_url(prompt="consent")
    print(f"\n👉 Abra esta URL no seu browser:\n{auth_url}\n")
    code = input("Cole aqui o código de autorização recebido: ").strip()
    flow.fetch_token(code=code)
    creds = flow.credentials

# Salvar token
os.makedirs(HERMES_HOME, exist_ok=True)
with open(TOKEN_PATH, "w") as f:
    json.dump(
        {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes or []),
        },
        f,
        indent=2,
    )

print(f"\n✅ Autorização concluída! Token salvo em: {TOKEN_PATH}")
print("   O support_agent.py agora pode acessar o Gmail automaticamente.")
