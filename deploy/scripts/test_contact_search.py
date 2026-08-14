#!/usr/bin/env python3
"""Testa a busca e atualização de contatos sem reiniciar o container.

Uso:
    python3 test_contact_search.py              # suite completa
    python3 test_contact_search.py "Rosemery"  # busca ad-hoc por nome
    python3 test_contact_search.py "558699997003"  # busca ad-hoc por número
"""

import json
import os
import re
import sys
import sqlite3
import urllib.request
import urllib.parse
from pathlib import Path

HERMES_HOME = os.getenv("HERMES_HOME", "/opt/data/.hermes")
PC_PATH = Path("/opt/data/personal_contacts.json")
DB_PATH = Path(f"{HERMES_HOME}/whatsapp_messages.db")
BRIDGE_URL = os.getenv("BRIDGE_URL", "http://localhost:3000")

# Casos: (identifier, deve_encontrar, chave_esperada_contém, desc)
CASOS = [
    # Busca por número exato (Rosemery)
    ("5511996472188", True, "5511996472188", "número exato Rosemery"),
    # Busca por nome exato
    ("Rosemery", True, "5511996472188", "nome exato Rosemery"),
    # Busca por nome parcial
    ("Rose", True, "5511996472188", "substring do nome Rosemery"),
    # Número com espaços e hífens (como usuário digita)
    ("+55 11 9964-72188", True, "5511996472188", "número formatado com espaços"),
    # Nome que NÃO deve encontrar contato errado
    ("Suporte", False, None, "nome sem match — não deve pegar contato errado"),
    # Número que não existe — não deve colidir com nenhum existente
    ("558699997003", False, None, "número inexistente"),
]


def normalize_br(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 13 and digits.startswith("55") and digits[4] == "9":
        return digits[:4] + digits[5:]
    if len(digits) == 12 and digits.startswith("55"):
        return digits[:4] + "9" + digits[4:]
    return digits


def load_contacts():
    if not PC_PATH.exists():
        print(f"[ERRO] {PC_PATH} não encontrado")
        sys.exit(1)
    return json.loads(PC_PATH.read_text(encoding="utf-8"))


def is_owner_key(key: str, owner_phone: str) -> bool:
    phone = key.split("@")[0]
    return bool(owner_phone) and (phone == owner_phone or normalize_br(phone) == normalize_br(owner_phone))


def search_by_identifier(identifier: str, contacts: dict, owner_phone: str) -> tuple[str | None, str]:
    id_norm = identifier.lower().strip()
    id_digits = re.sub(r"\D", "", identifier)
    id_norm_br = normalize_br(id_digits) if id_digits else ""

    # Passo 1: número
    if re.match(r"^\+?[\d\s\-\(\)]+$", identifier) and len(id_digits) >= 8:
        for key in contacts:
            if is_owner_key(key, owner_phone):
                continue
            phone = key.split("@")[0].split(":")[0]
            phone_br = normalize_br(phone)
            if id_digits in phone or phone in id_digits or (id_norm_br and id_norm_br == phone_br):
                return key, "passo 1 (número)"

    # Passo 2: nome exato
    for key, data in contacts.items():
        if is_owner_key(key, owner_phone):
            continue
        if (data.get("name") or "").lower() == id_norm:
            return key, "passo 2 (nome exato)"

    # Passo 3: nickname/pet_name exato
    for key, data in contacts.items():
        if is_owner_key(key, owner_phone):
            continue
        for field in ["nickname", "pet_name"]:
            if (data.get(field) or "").lower() == id_norm:
                return key, f"passo 3 ({field})"

    # Passo 4: substring
    best_key, best_score = None, 0
    for key, data in contacts.items():
        if is_owner_key(key, owner_phone):
            continue
        name_norm = (data.get("name") or "").lower()
        if name_norm and id_norm in name_norm:
            if len(name_norm) > best_score:
                best_key, best_score = key, len(name_norm)
    if best_key:
        return best_key, "passo 4 (substring)"

    # Passo 5: DB
    if DB_PATH.exists():
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                cur = conn.cursor()
                cur.execute("SELECT chat_id, MAX(sender_name) FROM messages WHERE chat_id NOT LIKE '%@g.us%' GROUP BY chat_id")
                for chat_id_row, sender_name in cur.fetchall():
                    if not sender_name or is_owner_key(chat_id_row, owner_phone):
                        continue
                    sn_norm = sender_name.lower()
                    if id_norm in sn_norm or sn_norm in id_norm:
                        phone_row = chat_id_row.split("@")[0]
                        for key in contacts:
                            if key.split("@")[0] == phone_row:
                                return key, f"passo 5 (DB sender_name={sender_name})"
                        return chat_id_row, f"passo 5 (DB novo — {sender_name})"
        except Exception as e:
            print(f"  [DB] erro: {e}")

    # Passo 6: bridge
    try:
        url = f"{BRIDGE_URL}/contacts/search?name={urllib.parse.quote(identifier, safe='')}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            results = json.loads(resp.read().decode()).get("results", [])

        valid = [e for e in results if e.get("jid") and not is_owner_key(e.get("jid", ""), owner_phone)]
        id_lower = identifier.lower()

        def score(e):
            n = (e.get("name") or "").lower()
            if not n or len(n) < 3:
                return 0
            if n == id_lower:
                return 3
            if id_lower in n or n in id_lower:
                return 2
            iw = set(w for w in id_lower.split() if len(w) >= 3)
            nw = set(w for w in n.split() if len(w) >= 3)
            return len(iw & nw)

        # Pass 1: match existente com nome compatível
        for entry in valid:
            jid = entry.get("jid", "")
            real_name = (entry.get("name") or "").lower()
            phone_row = jid.split("@")[0]
            if len(real_name) < 3:
                continue
            iw = set(w for w in id_lower.split() if len(w) >= 3)
            nw = set(w for w in real_name.split() if len(w) >= 3)
            if id_lower not in real_name and real_name not in id_lower and not (iw & nw):
                continue
            for key in contacts:
                if key.split("@")[0] == phone_row:
                    return key, f"passo 6 pass1 (bridge name={entry.get('name')})"

        # Pass 2: melhor score
        if valid:
            best = max(valid, key=score)
            if score(best) > 0:
                jid = best.get("jid", "")
                phone = jid.split("@")[0]
                key = jid if "@" in jid else f"{phone}@s.whatsapp.net"
                return key, f"passo 6 pass2 novo (bridge name={best.get('name')} score={score(best)})"
            else:
                return None, f"passo 6: {len(valid)} resultados mas score=0 — abortado"
    except Exception as e:
        return None, f"passo 6 erro: {e}"

    return None, "não encontrado"


def get_owner_phone():
    try:
        auth_path = Path(HERMES_HOME) / "auth.json"
        if auth_path.exists():
            auth = json.loads(auth_path.read_text())
            return re.sub(r"\D", "", auth.get("whatsapp_owner_number", ""))
    except Exception:
        pass
    return ""


def run_case(identifier, deve_encontrar, chave_esperada, desc, contacts, owner_phone):
    print(f"\n  Busca   : '{identifier}' — {desc}")
    matched_key, passo = search_by_identifier(identifier, contacts, owner_phone)

    if matched_key:
        name = contacts.get(matched_key, {}).get("name", "?") if matched_key in contacts else "NOVO"
        phone = matched_key.split("@")[0] if matched_key else ""
        print(f"  Resultado: {passo}")
        print(f"  Chave   : {matched_key} (name='{name}')")
    else:
        print(f"  Resultado: {passo}")

    ok = True
    if deve_encontrar and not matched_key:
        print(f"  *** FALHOU: esperava encontrar contato mas não encontrou")
        ok = False
    elif not deve_encontrar and matched_key:
        name = contacts.get(matched_key, {}).get("name", "?")
        print(f"  *** FALHOU: não deveria encontrar mas encontrou '{name}' ({matched_key})")
        ok = False
    elif deve_encontrar and chave_esperada and matched_key and chave_esperada not in matched_key:
        print(f"  *** CHAVE ERRADA: esperava '{chave_esperada}' mas encontrou '{matched_key}'")
        ok = False

    print(f"  Status  : {'✓ OK' if ok else '✗ FALHOU'}")
    return ok


def main():
    print("=" * 60)
    print("Teste de Busca de Contatos — whatsapp-manager")
    print("=" * 60)

    contacts = load_contacts()
    owner_phone = get_owner_phone()
    print(f"\nContatos: {len(contacts)} entradas")
    print(f"Owner   : {owner_phone or 'não detectado'}")
    print(f"DB      : {'✓' if DB_PATH.exists() else '✗ ausente'}")
    print(f"Bridge  : {BRIDGE_URL}")

    # Modo ad-hoc
    if len(sys.argv) > 1:
        identifier = " ".join(sys.argv[1:])
        print(f"\n--- Busca ad-hoc ---")
        matched_key, passo = search_by_identifier(identifier, contacts, owner_phone)
        if matched_key:
            data = contacts.get(matched_key, {})
            print(f"  Passo   : {passo}")
            print(f"  Chave   : {matched_key}")
            print(f"  Nome    : {data.get('name')}")
            print(f"  Rel     : {data.get('relationship')} / {data.get('manual_relationship')}")
        else:
            print(f"  {passo}")
        return

    # Suite completa
    print(f"\n--- {len(CASOS)} casos de teste ---")
    ok = sum(run_case(*c, contacts, owner_phone) for c in CASOS)
    print(f"\n{'=' * 60}")
    print(f"Resultado: {ok}/{len(CASOS)} casos corretos")
    if ok < len(CASOS):
        sys.exit(1)


if __name__ == "__main__":
    main()
