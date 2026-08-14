#!/usr/bin/env python3
"""
google_api.py — Auxiliar de autenticação OAuth2 para a Gmail API
Usado por: support_agent.py

Fluxo:
  1. Lê GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET do ambiente (Portainer stack env ou .env)
  2. Carrega/salva o refresh_token em /opt/data/.hermes/google_token.json
  3. Devolve um Resource object da googleapiclient pronto para uso

Dependências (já instaladas no venv do Hermes):
  google-auth, google-auth-oauthlib, google-auth-httplib2, google-api-python-client
"""

import os
import json
import logging
import base64

# ---------------------------------------------------------------------------
# Paths e constantes
# ---------------------------------------------------------------------------
PERSISTENT_DATA_DIR = "/opt/data"
HERMES_HOME = os.path.join(PERSISTENT_DATA_DIR, ".hermes")
TOKEN_PATH = os.path.join(HERMES_HOME, "google_token.json")
DOTENV_PATH = os.path.join(PERSISTENT_DATA_DIR, ".env")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

# ---------------------------------------------------------------------------
# Carrega .env se necessário (fallback para quando rodado fora do venv)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(DOTENV_PATH)
except ImportError:
    pass  # variáveis já devem estar no ambiente via Portainer

# ---------------------------------------------------------------------------
# build_service — ponto de entrada principal
# ---------------------------------------------------------------------------
def build_service(api_name: str = "gmail", api_version: str = "v1"):
    """
    Constrói e retorna um Resource da Google API autenticado via OAuth2.

    Requer as variáveis de ambiente:
      GOOGLE_CLIENT_ID
      GOOGLE_CLIENT_SECRET

    O refresh_token é lido/escrito em TOKEN_PATH (google_token.json).
    Se o token não existir ainda, levanta RuntimeError com instruções.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError as e:
        raise ImportError(
            "Bibliotecas do Google não encontradas. "
            "Execute: uv pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        ) from e

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET não encontrados. "
            "Configure-os no Portainer (stack env vars) ou em /opt/data/.env"
        )

    creds = None

    # Tentar carregar credenciais salvas
    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, "r") as f:
                token_data = json.load(f)
            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES,
            )
        except Exception as e:
            logging.warning(f"Erro ao carregar token salvo ({TOKEN_PATH}): {e}. Tentando renovar.")
            creds = None

    # Renovar se expirado ou inválido
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds)
            logging.info("Token Google renovado com sucesso.")
        except Exception as e:
            logging.error(f"Falha ao renovar token Google: {e}")
            creds = None

    if not creds or not creds.valid:
        raise RuntimeError(
            f"Credenciais Google inválidas ou ausentes em {TOKEN_PATH}.\n"
            "Para gerar o token inicial, rode no container:\n"
            "  cd /opt/data && python3 .hermes/scripts/authorize_google.py\n"
            "Ou configure o refresh_token manualmente em google_token.json."
        )

    service = build(api_name, api_version, credentials=creds, cache_discovery=False)
    return service


def _save_token(creds):
    """Salva as credenciais atualizadas em TOKEN_PATH."""
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
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


# ---------------------------------------------------------------------------
# _headers_dict — extrai headers de uma mensagem da Gmail API
# ---------------------------------------------------------------------------
def _headers_dict(message: dict) -> dict:
    """
    Recebe uma mensagem bruta da Gmail API e retorna um dicionário
    de headers com chaves em lowercase.

    Exemplo:
        headers = _headers_dict(msg)
        subject = headers.get("subject", "(sem assunto)")
    """
    payload = message.get("payload", {})
    raw_headers = payload.get("headers", [])
    return {h["name"].lower(): h["value"] for h in raw_headers}


# ---------------------------------------------------------------------------
# _extract_message_body — extrai o corpo de texto de uma mensagem
# ---------------------------------------------------------------------------
def _extract_message_body(message: dict, prefer_plain: bool = True) -> str:
    """
    Extrai o corpo da mensagem da Gmail API, suportando:
      - Mensagens simples (payload direto)
      - Mensagens multipart (nested parts)

    Retorna texto UTF-8 decodificado, ou string vazia se não encontrado.
    """
    payload = message.get("payload", {})
    return _extract_body_from_part(payload, prefer_plain=prefer_plain)


def _extract_body_from_part(part: dict, prefer_plain: bool = True) -> str:
    """Navega recursivamente pelas partes MIME para extrair o corpo."""
    mime_type = part.get("mimeType", "")
    parts = part.get("parts", [])

    # Parte simples (sem sub-partes)
    if not parts:
        data = part.get("body", {}).get("data", "")
        if data:
            try:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            except Exception:
                return ""
        return ""

    # Multipart: procurar o tipo preferido primeiro
    preferred_mime = "text/plain" if prefer_plain else "text/html"
    fallback_mime = "text/html" if prefer_plain else "text/plain"

    for p in parts:
        if p.get("mimeType") == preferred_mime and not p.get("parts"):
            text = _extract_body_from_part(p, prefer_plain)
            if text:
                return text

    for p in parts:
        if p.get("mimeType") == fallback_mime and not p.get("parts"):
            text = _extract_body_from_part(p, prefer_plain)
            if text:
                return text

    # Recursão: tentar partes multipart aninhadas
    for p in parts:
        text = _extract_body_from_part(p, prefer_plain)
        if text:
            return text

    return ""
