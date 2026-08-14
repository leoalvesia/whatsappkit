#!/usr/bin/env python3
"""
Diagnóstico e teste do style learning.

Uso:
  python3 test_style_learning.py              # diálogos coletados (como o bot veria)
  python3 test_style_learning.py --preview    # preview do SOUL_WHATSAPP.md
  python3 test_style_learning.py --diag       # diagnóstico completo de contatos e banco
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

PREVIEW = "--preview" in sys.argv
DIAG = "--diag" in sys.argv
MIN_MSGS = 1  # mesmo threshold do bot


def norm_text(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


def norm_phone(digits: str) -> str:
    """Normaliza telefone brasileiro (remove 9 extra quando necessário)."""
    if len(digits) == 13 and digits.startswith("55"):
        # Remove o 9 extra: 5586 9XXXX → 5586 XXXX para comparação
        area = digits[2:4]
        rest = digits[4:]
        if rest.startswith("9") and len(rest) == 9:
            return digits[:4] + rest[1:]
    return digits


def sanitize(text: str) -> str | None:
    if not text:
        return None
    patterns = [
        r"\b\d{4,6}\b.*senha|senha.*\b\d{4,6}\b",
        r"senha|password|pin\b",
        r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",
        r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",
        r"ag[eê]ncia\s*:?\s*\d{3,6}",
        r"conta\s*:?\s*\d{4,}",
        r"cart[aã]o\s*:?\s*[\d\s]{13,19}",
        r"\b\d{13,19}\b",
        r"cvv|cvc\s*:?\s*\d{3}",
        r"saldo.*R\$\s*[\d.,]+",
        r"R\$\s*[\d.,]{4,}",
        r"chave\s+pix.*@|@.*chave\s+pix",
        r"token|código de verificação|código de acesso",
    ]
    tl = text.lower()
    for p in patterns:
        if re.search(p, tl, re.IGNORECASE):
            return None
    return text


def load_contacts():
    if not CONTACTS_PATH.exists():
        print(f"❌ personal_contacts.json não encontrado em {CONTACTS_PATH}")
        sys.exit(1)
    with open(CONTACTS_PATH) as f:
        return json.load(f)


def load_contacts_cache() -> dict:
    """Carrega contacts_cache.json do bridge (pushNames capturados em tempo real)."""
    if not CONTACTS_CACHE_PATH.exists():
        return {}
    try:
        with open(CONTACTS_CACHE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def build_lookups(personal_contacts: dict):
    """
    Retorna:
      raw_to_rel, raw_to_name  — indexados pelo prefixo bruto (antes do @)
      phone_to_rel, phone_to_name — indexados pelo telefone normalizado
    """
    raw_to_rel, raw_to_name = {}, {}
    phone_to_rel, phone_to_name = {}, {}

    # Nomes do cache do bridge (pushName capturado em tempo real)
    cache = load_contacts_cache()
    cache_names: dict[str, str] = {}
    for jid, data in cache.items():
        cname = data.get("notify") or data.get("name") or data.get("pushName") or ""
        _cn = norm_text(cname)
        if _cn and _cn not in ("andre alencar", "andré alencar", "andre", "andré"):
            raw_c = jid.split("@")[0].split(":")[0]
            digits_c = "".join(c for c in raw_c if c.isdigit())
            cache_names[raw_c] = cname
            if digits_c:
                cache_names[norm_phone(digits_c)] = cname

    for key, data in personal_contacts.items():
        rel = data.get("manual_relationship") or data.get("relationship") or "Cliente"
        name = data.get("nickname") or data.get("name") or ""
        _nn = norm_text(name)
        if _nn in ("andre alencar", "andré alencar", "andre", "andré"):
            name = ""
        elif _nn.startswith("contato ") or _nn.startswith("usuario ") or _nn.startswith("desconhecido"):
            name = ""

        raw = key.split("@")[0]
        digits = "".join(c for c in raw if c.isdigit())
        pnorm = norm_phone(digits)

        # Fallback para nome do cache do bridge
        if not name:
            name = cache_names.get(raw) or cache_names.get(pnorm) or ""

        raw_to_rel[raw] = rel
        phone_to_rel[pnorm] = rel
        if name:
            raw_to_name[raw] = name
            phone_to_name[pnorm] = name

    return raw_to_rel, raw_to_name, phone_to_rel, phone_to_name


SESSION_DIR = Path("/opt/data/.hermes/platforms/whatsapp/session")


def build_lid_phone_map(conn) -> dict[str, str]:
    """
    Constrói mapa lid_prefix → phone_prefix.
    Tenta: 1) arquivos lid-mapping-{phone}.json da sessão  2) sender_id das msgs recebidas.
    """
    mapping = {}
    # Fonte 1: arquivos de sessão (mais confiável)
    if SESSION_DIR.exists():
        import re as _re
        for f in SESSION_DIR.iterdir():
            m = _re.match(r'^lid-mapping-(\d+)\.json$', f.name)
            if not m:
                continue
            phone = m.group(1)
            try:
                lid = json.loads(f.read_text()).strip().strip('"')
                if lid:
                    mapping[lid] = phone
            except Exception:
                pass
    # Fonte 2: sender_id das mensagens recebidas em chats @lid
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT chat_id, sender_id FROM messages
        WHERE from_me=0 AND chat_id LIKE '%@lid%'
        AND sender_id IS NOT NULL
        AND sender_id NOT LIKE '%@lid%'
        AND sender_id NOT LIKE '%@g.us%'
    """)
    for chat_id, sender_id in cur.fetchall():
        lid = chat_id.split("@")[0]
        phone = sender_id.split("@")[0].split(":")[0]
        if phone and phone.isdigit() and lid not in mapping:
            mapping[lid] = phone
    return mapping


def lookup_contact(chat_id: str, lid_phone_map: dict,
                   raw_to_rel, raw_to_name, phone_to_rel, phone_to_name):
    """
    Resolve relacionamento e nome para um chat_id.
    Tenta: raw prefix → reverse lid (phone→lid) → lid→phone → phone normalizado.
    """
    # Mapa reverso: phone → lid (calculado uma vez seria melhor, mas aqui é simples)
    phone_to_lid = {v: k for k, v in lid_phone_map.items()}

    raw = chat_id.split("@")[0].split(":")[0]
    digits = "".join(c for c in raw if c.isdigit())
    pnorm = norm_phone(digits)

    # 1. Tentativa direta pelo raw prefix (funciona para @lid entries diretos)
    rel = raw_to_rel.get(raw)
    name = raw_to_name.get(raw)

    # 2. Para @lid chat, tentar via lid→phone no personal_contacts
    if rel is None and "@lid" in chat_id:
        phone_from_lid = lid_phone_map.get(raw, "")
        if phone_from_lid:
            palt = norm_phone("".join(c for c in phone_from_lid if c.isdigit()))
            rel = raw_to_rel.get(phone_from_lid, phone_to_rel.get(palt))
            name = raw_to_name.get(phone_from_lid, phone_to_name.get(palt))

    # 3. Para @s.whatsapp.net, tentar via phone→lid (contato pode estar sob @lid no personal_contacts)
    if (rel is None or name is None) and "@lid" not in chat_id:
        lid_from_phone = phone_to_lid.get(digits) or phone_to_lid.get(pnorm)
        if lid_from_phone:
            rel = rel or raw_to_rel.get(lid_from_phone)
            name = name or raw_to_name.get(lid_from_phone)

    # 4. Fallback pelo telefone normalizado
    if rel is None:
        rel = phone_to_rel.get(pnorm, "Geral")
    if name is None:
        name = phone_to_name.get(pnorm, rel)

    return rel or "Geral", name or rel or "Geral"


def main():
    if not DB_PATH.exists():
        print(f"❌ Banco não encontrado: {DB_PATH}")
        sys.exit(1)

    personal_contacts = load_contacts()
    raw_to_rel, raw_to_name, phone_to_rel, phone_to_name = build_lookups(personal_contacts)

    with sqlite3.connect(str(DB_PATH)) as conn:
        lid_phone_map = build_lid_phone_map(conn)
        cur = conn.cursor()

        if DIAG:
            print("=== DIAGNÓSTICO ===\n")
            print(f"personal_contacts.json: {len(personal_contacts)} contatos")
            print(f"Cross-reference @lid→phone: {len(lid_phone_map)} mapeamentos")
            if lid_phone_map:
                for lid, phone in list(lid_phone_map.items())[:10]:
                    rel = raw_to_rel.get(phone, phone_to_rel.get(norm_phone("".join(c for c in phone if c.isdigit())), "?"))
                    name = raw_to_name.get(phone, phone_to_name.get(norm_phone("".join(c for c in phone if c.isdigit())), ""))
                    print(f"  {lid}@lid → {phone} → {rel} / {name or '(sem nome)'}")
            print()

            cur.execute("""
                SELECT chat_id,
                       SUM(CASE WHEN from_me=1 AND (sender_name IS NULL OR sender_name != 'Bot') THEN 1 ELSE 0 END) as manual_out,
                       SUM(CASE WHEN from_me=0 THEN 1 ELSE 0 END) as received,
                       MAX(timestamp) as last_ts
                FROM messages
                WHERE chat_id NOT LIKE '%@g.us%'
                GROUP BY chat_id ORDER BY last_ts DESC
            """)
            raw_rows = cur.fetchall()

            # Agrupa @lid e @s.whatsapp.net do mesmo contato
            phone_to_lid_rev = {v: k for k, v in lid_phone_map.items()}
            merged: dict[str, dict] = {}
            for chat_id, manual_out, received, last_ts in raw_rows:
                raw = chat_id.split("@")[0]
                digits = "".join(c for c in raw if c.isdigit())
                pnorm = norm_phone(digits)
                # Chave canônica: phone normalizado se disponível, senão raw
                if "@lid" in chat_id:
                    phone = lid_phone_map.get(raw, "")
                    key = norm_phone("".join(c for c in phone if c.isdigit())) if phone else raw
                else:
                    key = pnorm or raw
                if key not in merged:
                    merged[key] = {"chat_ids": [], "manual_out": 0, "received": 0, "last_ts": 0}
                merged[key]["chat_ids"].append(chat_id)
                merged[key]["manual_out"] += manual_out
                merged[key]["received"] += received
                merged[key]["last_ts"] = max(merged[key]["last_ts"], last_ts or 0)

            print(f"Chats no banco: {len(raw_rows)} JIDs → {len(merged)} contatos únicos\n")
            for key, info in sorted(merged.items(), key=lambda x: -x[1]["last_ts"]):
                primary_id = info["chat_ids"][0]
                rel, name = lookup_contact(primary_id, lid_phone_map, raw_to_rel, raw_to_name, phone_to_rel, phone_to_name)
                manual_out = info["manual_out"]
                received = info["received"]
                flag = "✅" if manual_out >= MIN_MSGS else ("⚠️" if manual_out > 0 else "❌")
                jids_str = " + ".join(info["chat_ids"]) if len(info["chat_ids"]) > 1 else primary_id
                print(f"{flag} {jids_str}")
                print(f"   msgs_saída={manual_out} recebidas={received} | {rel} / {name}")
            return

        # Coleta normal
        cur.execute("""
            SELECT chat_id, MAX(timestamp) as last_ts FROM messages
            WHERE from_me=1 AND (sender_name IS NULL OR sender_name != 'Bot')
            AND chat_id NOT LIKE '%@g.us%'
            GROUP BY chat_id ORDER BY last_ts DESC
        """)
        all_chats = cur.fetchall()
        print(f"=== STYLE LEARNING — {len(all_chats)} chat(s) com msgs saídas ===\n")

        cutoff = int(time.time()) - 90 * 24 * 3600
        groups: dict[str, list] = {}
        total = 0

        for chat_id, _ in all_chats:
            rel, contact_name = lookup_contact(chat_id, lid_phone_map, raw_to_rel, raw_to_name, phone_to_rel, phone_to_name)

            cur.execute("""
                SELECT m.body, m.timestamp,
                       (SELECT body FROM messages
                        WHERE chat_id=? AND from_me=0 AND timestamp < m.timestamp
                        AND body IS NOT NULL AND length(trim(body)) > 1
                        AND body NOT LIKE '<Media omitted>%'
                        AND length(body) <= 300
                        ORDER BY timestamp DESC LIMIT 1) as contact_msg
                FROM messages m
                WHERE m.from_me=1 AND (m.sender_name IS NULL OR m.sender_name != 'Bot')
                AND m.chat_id=? AND m.timestamp >= ?
                AND m.body IS NOT NULL AND length(trim(m.body)) > 1
                AND m.body NOT LIKE '[%'
                AND m.body NOT LIKE '<Media omitted>%'
                AND length(m.body) <= 300
                ORDER BY m.timestamp DESC LIMIT 20
            """, (chat_id, chat_id, cutoff))

            msgs = []
            for body, ts, contact_msg in cur.fetchall():
                body_clean = sanitize(body)
                if not body_clean:
                    continue
                msgs.append({
                    "contact": contact_msg,
                    "andre": body_clean,
                    "contact_name": contact_name,
                })

            if not msgs:
                continue

            total += len(msgs)
            groups.setdefault(rel, []).extend(msgs)
            flag = "✅" if len(msgs) >= MIN_MSGS else "⚠️ (poucas msgs — bot descarta)"
            print(f"📱 {chat_id} {flag}")
            print(f"   Relacionamento: {rel} | Label: {contact_name} | {len(msgs)} msg(s)")
            for item in msgs[:5]:
                if item["contact"]:
                    print(f'   {contact_name}: "{item["contact"][:60]}"')
                print(f'   André → {contact_name}: "{item["andre"][:80]}"')
            print()

        # Aplicar filtro >= MIN_MSGS (igual ao bot)
        filtered = {r: m for r, m in groups.items() if len(m) >= MIN_MSGS}
        dropped = [r for r in groups if r not in filtered]

        print(f"Total coletado: {total} msg(s)")
        if dropped:
            print(f"⚠️  Grupos descartados pelo bot (< {MIN_MSGS} msgs): {dropped}")
        print(f"Grupos que passam para o SOUL_WHATSAPP.md: {list(filtered.keys())}")

        if PREVIEW and filtered:
            from datetime import datetime
            print(f"\n=== PREVIEW SOUL_WHATSAPP.md ===\n")
            print(f"## EXEMPLOS REAIS DE ESCRITA")
            print(f"> Gerado em {datetime.now().strftime('%d/%m/%Y')}\n")
            for rel, msgs in filtered.items():
                print(f"### {rel}")
                for item in msgs[:5]:
                    label = item["contact_name"]
                    ct = sanitize(item.get("contact") or "")
                    at = sanitize(item.get("andre", ""))
                    if not at:
                        continue
                    if ct:
                        print(f'- **{label}:** "{ct[:60]}"')
                        print(f'  **André → {label}:** "{at[:80]}"')
                    else:
                        print(f'- **André → {label}:** "{at[:80]}"')
                print()


if __name__ == "__main__":
    main()
