#!/usr/bin/env python3
"""
Simula e exibe o processo completo de geração dos exemplos de diálogo do SOUL_WHATSAPP.md.

Uso:
  python3 preview_soul.py              # mostra exemplos que seriam gerados
  python3 preview_soul.py --verbose    # mostra cada etapa do processo
  python3 preview_soul.py --contact 558699997003  # filtra por número de telefone
"""

import sys
import re
import json
import sqlite3
import unicodedata
import time
from pathlib import Path

DB_PATH = Path("/opt/data/.hermes/whatsapp_messages.db")
CONTACTS_PATH = Path("/opt/data/personal_contacts.json")
CONTACTS_CACHE_PATH = Path("/opt/data/.hermes/contacts_cache.json")
SESSION_DIR = Path("/opt/data/.hermes/platforms/whatsapp/session")

VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv
FILTER_CONTACT = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--contact" and i + 1 < len(sys.argv)), None)
CUTOFF_DAYS = 90


def log(msg):
    if VERBOSE:
        print(f"\033[90m  {msg}\033[0m")


def norm_text(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def norm_phone(digits):
    if len(digits) == 13 and digits.startswith("55"):
        area, rest = digits[2:4], digits[4:]
        if rest.startswith("9") and len(rest) == 9:
            return digits[:4] + rest[1:]
    return digits


def sanitize(text):
    if not text:
        return None
    patterns = [
        r"senha|password|pin\b",
        r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",
        r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",
        r"ag[eê]ncia\s*:?\s*\d{3,6}",
        r"conta\s*:?\s*\d{4,}",
        r"cart[aã]o\s*:?\s*[\d\s]{13,19}",
        r"\b\d{13,19}\b",
        r"cvv|cvc\s*:?\s*\d{3}",
        r"saldo.*R\$\s*[\d.,]+|R\$\s*[\d.,]{4,}",
        r"chave\s+pix.*@|token|código de verificação",
    ]
    for p in patterns:
        if re.search(p, text.lower(), re.IGNORECASE):
            return None
    return text


def load_contacts_cache():
    if not CONTACTS_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CONTACTS_CACHE_PATH.read_text())
    except Exception:
        return {}


def build_lid_phone_map(conn):
    mapping = {}
    if SESSION_DIR.exists():
        for f in SESSION_DIR.iterdir():
            m = re.match(r'^lid-mapping-(\d+)\.json$', f.name)
            if not m:
                continue
            try:
                lid = json.loads(f.read_text()).strip().strip('"')
                if lid:
                    mapping[lid] = m.group(1)
            except Exception:
                pass
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT chat_id, sender_id FROM messages
        WHERE from_me=0 AND chat_id LIKE '%@lid%'
        AND sender_id IS NOT NULL AND sender_id NOT LIKE '%@lid%'
    """)
    for chat_id, sender_id in cur.fetchall():
        lid = chat_id.split("@")[0]
        phone = sender_id.split("@")[0].split(":")[0]
        if phone and phone.isdigit() and lid not in mapping:
            mapping[lid] = phone
    return mapping


def build_lookups(personal_contacts, contacts_cache):
    raw_to_rel, raw_to_name = {}, {}
    phone_to_rel, phone_to_name = {}, {}
    owner_norms = {"andre alencar", "andré alencar", "andre", "andré"}

    # Nomes do cache do bridge
    cache_names = {}
    for jid, data in contacts_cache.items():
        cname = data.get("notify") or data.get("name") or data.get("pushName") or ""
        if norm_text(cname) and norm_text(cname) not in owner_norms:
            raw_c = jid.split("@")[0].split(":")[0]
            digits_c = "".join(c for c in raw_c if c.isdigit())
            cache_names[raw_c] = cname
            if digits_c:
                cache_names[norm_phone(digits_c)] = cname

    for key, data in personal_contacts.items():
        rel = data.get("manual_relationship") or data.get("relationship") or "Cliente"
        name = data.get("nickname") or data.get("name") or ""
        nn = norm_text(name)
        if nn in owner_norms or nn.startswith("contato ") or nn.startswith("usuario "):
            name = ""
        raw = key.split("@")[0]
        digits = "".join(c for c in raw if c.isdigit())
        pnorm = norm_phone(digits)
        if not name:
            name = cache_names.get(raw) or cache_names.get(pnorm) or ""
        raw_to_rel[raw] = rel
        phone_to_rel[pnorm] = rel
        if name:
            raw_to_name[raw] = name
            phone_to_name[pnorm] = name

    return raw_to_rel, raw_to_name, phone_to_rel, phone_to_name


def lookup_contact(chat_id, lid_phone_map, raw_to_rel, raw_to_name, phone_to_rel, phone_to_name):
    phone_to_lid = {v: k for k, v in lid_phone_map.items()}
    raw = chat_id.split("@")[0].split(":")[0]
    digits = "".join(c for c in raw if c.isdigit())
    pnorm = norm_phone(digits)

    rel = raw_to_rel.get(raw)
    name = raw_to_name.get(raw)

    if rel is None and "@lid" in chat_id:
        phone = lid_phone_map.get(raw, "")
        if phone:
            palt = norm_phone("".join(c for c in phone if c.isdigit()))
            rel = raw_to_rel.get(phone, phone_to_rel.get(palt))
            name = raw_to_name.get(phone, phone_to_name.get(palt))

    if "@lid" not in chat_id:
        lid = phone_to_lid.get(digits) or phone_to_lid.get(pnorm)
        if lid:
            lid_rel = raw_to_rel.get(lid)
            lid_name = raw_to_name.get(lid)
            if lid_rel:
                rel = lid_rel
            if lid_name:
                name = lid_name

    rel = rel or phone_to_rel.get(pnorm, "Geral")
    name = name or phone_to_name.get(pnorm) or rel

    # Nunca usar nome do dono como label
    owner_norms = {"andre alencar", "andré alencar", "andre", "andré"}
    if norm_text(name) in owner_norms:
        name = rel

    return rel, name


def main():
    if not DB_PATH.exists():
        print(f"❌ Banco não encontrado: {DB_PATH}")
        sys.exit(1)
    if not CONTACTS_PATH.exists():
        print(f"❌ personal_contacts.json não encontrado")
        sys.exit(1)

    personal_contacts = json.loads(CONTACTS_PATH.read_text())
    contacts_cache = load_contacts_cache()
    raw_to_rel, raw_to_name, phone_to_rel, phone_to_name = build_lookups(personal_contacts, contacts_cache)

    print(f"\033[1m=== PREVIEW SOUL_WHATSAPP.md — geração de exemplos ===\033[0m\n")
    log(f"personal_contacts: {len(personal_contacts)} contatos")
    log(f"contacts_cache: {len(contacts_cache)} entradas")

    with sqlite3.connect(str(DB_PATH)) as conn:
        lid_phone_map = build_lid_phone_map(conn)
        log(f"lid_phone_map: {len(lid_phone_map)} mapeamentos")

        cur = conn.cursor()
        cur.execute("""
            SELECT chat_id, MAX(timestamp) FROM messages
            WHERE from_me=1 AND (sender_name IS NULL OR sender_name != 'Bot')
            AND chat_id NOT LIKE '%@g.us%'
            GROUP BY chat_id ORDER BY MAX(timestamp) DESC
        """)
        all_chats = cur.fetchall()
        log(f"chats com msgs enviadas: {len(all_chats)}")

        cutoff = int(time.time()) - CUTOFF_DAYS * 24 * 3600
        groups = {}
        total_dialogues = 0
        total_standalone = 0

        for chat_id, _ in all_chats:
            if FILTER_CONTACT and FILTER_CONTACT not in chat_id:
                continue

            rel, contact_name = lookup_contact(chat_id, lid_phone_map, raw_to_rel, raw_to_name, phone_to_rel, phone_to_name)

            cur.execute("""
                SELECT body, timestamp FROM messages
                WHERE from_me=1 AND (sender_name IS NULL OR sender_name != 'Bot')
                AND chat_id=? AND timestamp >= ?
                AND body IS NOT NULL AND length(trim(body)) > 1
                AND body NOT LIKE '<Media omitted>%'
                AND body NOT LIKE '[%'
                AND length(body) <= 300
                ORDER BY timestamp DESC LIMIT 20
            """, (chat_id, cutoff))
            andre_msgs = cur.fetchall()

            cur.execute("""
                SELECT body, timestamp FROM messages
                WHERE from_me=0 AND chat_id=? AND timestamp >= ?
                AND body IS NOT NULL AND length(trim(body)) > 1
                AND body NOT LIKE '<Media omitted>%' AND length(body) <= 300
            """, (chat_id, cutoff - 86400))
            contact_msgs = cur.fetchall()

            msgs = []
            used_contact_ts = set()
            used_contact_bodies = set()
            for body, ts in andre_msgs:
                body_clean = sanitize(body)
                if not body_clean:
                    log(f"  ⚠️  filtrado (sensível): {body[:50]}")
                    continue
                # Mensagem do contato mais próxima dentro de 24h
                # (cada timestamp e cada conteúdo usado uma única vez)
                candidates = sorted(
                    ((abs(cts - ts), cts, cb) for cb, cts in contact_msgs
                     if abs(cts - ts) <= 86400
                     and cts not in used_contact_ts
                     and " ".join(cb.split()) not in used_contact_bodies),
                    key=lambda x: x[0],
                )
                contact_msg = None
                if candidates:
                    _, nearest_cts, nearest_cb = candidates[0]
                    contact_msg = " ".join(nearest_cb.split())
                    used_contact_ts.add(nearest_cts)
                    used_contact_bodies.add(contact_msg)
                msgs.append({"contact": contact_msg, "andre": body_clean})

            if not msgs:
                log(f"  ⚠️  {chat_id} sem msgs válidas após filtros")
                continue

            # Exibir
            has_dialogue = any(m["contact"] for m in msgs)
            d_count = sum(1 for m in msgs if m["contact"])
            s_count = sum(1 for m in msgs if not m["contact"])
            total_dialogues += d_count
            total_standalone += s_count

            print(f"\033[1m📱 {contact_name}\033[0m  \033[90m({chat_id})\033[0m")
            print(f"   \033[36mRelacionamento:\033[0m {rel}  |  diálogos: {d_count}  sem contexto: {s_count}")

            for item in msgs:
                if item["contact"]:
                    print(f'   \033[33m- {contact_name}: "{item["contact"][:80]}"\033[0m')
                    print(f'   \033[32m- André: "{item["andre"][:80]}"\033[0m')
                    print()
                else:
                    print(f'   \033[90m- André: "{item["andre"][:80]}"\033[0m')

            groups.setdefault(rel, []).extend(msgs)
            print()

        print(f"\033[1m─────────────────────────────────────────\033[0m")
        print(f"Total: {total_dialogues} diálogos com contexto + {total_standalone} mensagens sem contexto")
        print(f"Grupos: {list(groups.keys())}")

        if not groups:
            print("\n\033[31m❌ Nenhuma mensagem coletada. Verifique se André respondeu contatos no período.\033[0m")
        else:
            print(f"\n\033[32m✅ Estes exemplos serão incluídos no SOUL_WHATSAPP.md\033[0m")


if __name__ == "__main__":
    main()
