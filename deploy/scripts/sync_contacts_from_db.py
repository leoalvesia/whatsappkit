#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para sincronizar contatos únicos do banco de dados SQLite (whatsapp_messages.db)
para o arquivo local personal_contacts.json e enviá-los ao repositório privado do GitHub.
"""

import os
import json
import sqlite3
import base64
import urllib.request
import urllib.error
from pathlib import Path

def main():
    print("=" * 60)
    print("👤 SINCRONIZADOR DE CONTATOS DO WHATSAPP")
    print("=" * 60)

    # 1. Carregar caminhos e variáveis de ambiente
    base_dir = Path("/opt/data/.hermes")
    env_paths = [Path("/opt/data/.env"), base_dir / ".env"]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip("\"'")

    config_repo = os.getenv("CONFIG_REPO", "").strip()
    config_token = os.getenv("CONFIG_GITHUB_TOKEN", "").strip()
    setup_user = os.getenv("HERMES_SETUP_GITHUB_USER", "").strip()

    db_path = base_dir / "whatsapp_messages.db"
    pc_path = Path("/opt/data/personal_contacts.json")

    # 2. Garantir que o JSON existe
    personal_contacts = {}
    if pc_path.exists():
        try:
            with open(pc_path, "r", encoding="utf-8") as f:
                personal_contacts = json.load(f)
        except Exception as e:
            print(f"⚠️ Erro ao ler {pc_path}: {e}")

    # 3. Ler contatos únicos do banco SQLite
    if not db_path.exists():
        print(f"❌ Banco de dados SQLite não encontrado em {db_path}.")
        return

    print(f"🔍 Lendo conversas do banco {db_path}...")
    db_contacts = {}
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Obter JID e nome do remetente
        cursor.execute("""
            SELECT chat_id, MAX(sender_name) as name
            FROM messages
            WHERE chat_id NOT LIKE '%@g.us%' AND chat_id IS NOT NULL
            GROUP BY chat_id
        """)
        rows = cursor.fetchall()
        for chat_id, name in rows:
            if chat_id:
                db_contacts[chat_id] = name
        conn.close()
        print(f"✓ Encontrados {len(db_contacts)} contatos individuais no banco de dados.")
    except Exception as e:
        print(f"❌ Erro ao ler banco de dados SQLite: {e}")
        return

    # 4. Mesclar dados mantendo existentes
    updated = False
    for chat_id, name in db_contacts.items():
        # Limpar JID/número
        phone = chat_id.split("@")[0]
        
        # Verificar se já existe (por JID completo ou apenas número)
        exists = False
        for key in list(personal_contacts.keys()):
            if key == chat_id or key == phone:
                exists = True
                break
                
        if not exists:
            # Adicionar novo contato com campos padrão
            personal_contacts[chat_id] = {
                "name": name or f"Contato {phone}",
                "relationship": "cliente/contato",
                "tone": "polido e profissional",
                "guidelines": "Responda de forma prestativa."
            }
            print(f"➕ Adicionado novo contato: {name or phone} ({chat_id})")
            updated = True

    if not updated:
        print("✓ Nenhum contato novo para adicionar.")
    else:
        # Salvar arquivo JSON local
        try:
            with open(pc_path, "w", encoding="utf-8") as f:
                json.dump(personal_contacts, f, indent=2, ensure_ascii=False)
            print(f"✓ {pc_path} atualizado localmente.")
        except Exception as e:
            print(f"❌ Erro ao salvar {pc_path}: {e}")
            return

    # 5. Commit e Push para o GitHub se configurado
    if config_repo and config_token:
        if "/" in config_repo:
            repo_parts = config_repo.split("/")
            repo_user = repo_parts[0]
            repo_name = repo_parts[1]
        else:
            repo_user = setup_user or "empreendedorserial"
            repo_name = config_repo

        print(f"📤 Enviando atualização de personal_contacts.json para o GitHub ({repo_user}/{repo_name})...")
        
        try:
            with open(pc_path, "rb") as f:
                content = f.read()
            content_b64 = base64.b64encode(content).decode("utf-8")
            
            # Buscar SHA atual do arquivo no GitHub para evitar conflito
            get_url = f"https://api.github.com/repos/{repo_user}/{repo_name}/contents/personal_contacts.json"
            req_get = urllib.request.Request(get_url)
            req_get.add_header("Authorization", f"token {config_token}")
            req_get.add_header("Accept", "application/vnd.github+json")
            req_get.add_header("User-Agent", "Hermes-Agent-Plugin")
            
            sha = None
            try:
                with urllib.request.urlopen(req_get, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    sha = data.get("sha")
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    print(f"⚠️ Erro ao buscar SHA do arquivo no GitHub (HTTP {e.code}).")
            
            # Atualizar conteúdo
            put_data = {
                "message": "Update personal_contacts.json from WhatsApp database history",
                "content": content_b64,
                "branch": "main"
            }
            if sha:
                put_data["sha"] = sha
                
            req_put = urllib.request.Request(get_url, data=json.dumps(put_data).encode("utf-8"), method="PUT")
            req_put.add_header("Authorization", f"token {config_token}")
            req_put.add_header("Accept", "application/vnd.github+json")
            req_put.add_header("User-Agent", "Hermes-Agent-Plugin")
            req_put.add_header("Content-Type", "application/json")
            
            with urllib.request.urlopen(req_put, timeout=10) as resp:
                if resp.status in [200, 201]:
                    print("✓ personal_contacts.json atualizado no GitHub com sucesso!")
        except Exception as e:
            print(f"⚠️ Erro ao sincronizar com GitHub: {e}")
    else:
        print("ℹ️ Credenciais do GitHub não configuradas na VPS, pulando push remoto.")

if __name__ == "__main__":
    main()
