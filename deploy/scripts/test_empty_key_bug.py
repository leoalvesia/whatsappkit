#!/usr/bin/env python3
"""Valida o bug da chave vazia no passo 1 de _update_contact_fields.

Simula o contacts dict com uma chave vazia ("") e confirma que:
1. Sem o fix: "" causa falso match (phone in id_digits sempre True)
2. Com o fix: len(phone) < 8 pula a chave vazia e acha o contato correto

Uso:
    python3 test_empty_key_bug.py
"""

import json
import re
from pathlib import Path

PC_PATH = Path("/opt/data/personal_contacts.json")


def normalize_br(phone: str) -> str:
    clean = "".join(c for c in phone if c.isdigit())
    if clean.startswith("55") and len(clean) >= 11:
        ddd = clean[2:4]
        rest = clean[4:]
        if len(rest) == 9 and rest.startswith("9"):
            clean = f"55{ddd}{rest[1:]}"
    return clean


def step1_sem_fix(identifier: str, contacts: dict) -> tuple[str | None, str]:
    """Passo 1 SEM o fix — replicando o bug original."""
    id_digits = re.sub(r"\D", "", identifier)
    id_norm_br = normalize_br(id_digits)
    for key in contacts:
        phone = key.split("@")[0].split(":")[0]
        phone_norm_br = normalize_br(phone)
        if id_digits in phone or phone in id_digits or id_norm_br == phone_norm_br:
            return key, f"match (phone='{phone}')"
    return None, "nenhum match"


def step1_com_fix(identifier: str, contacts: dict) -> tuple[str | None, str]:
    """Passo 1 COM o fix — phone < 8 chars é ignorado."""
    id_digits = re.sub(r"\D", "", identifier)
    id_norm_br = normalize_br(id_digits)
    for key in contacts:
        phone = key.split("@")[0].split(":")[0]
        if len(phone) < 8:
            continue  # ← o fix
        phone_norm_br = normalize_br(phone)
        if id_digits in phone or phone in id_digits or id_norm_br == phone_norm_br:
            return key, f"match (phone='{phone}')"
    return None, "nenhum match"


def main():
    print("=" * 60)
    print("Diagnóstico: bug da chave vazia no passo 1")
    print("=" * 60)

    # ── Teste sintético (independente do contacts real) ────────────
    print("\n── Teste sintético ──")
    fake_contacts = {
        "": {"name": "entrada inválida"},           # chave vazia ← bug
        "558699997003@s.whatsapp.net": {"name": "EmpreendedorSerial"},
        "5511996472188@s.whatsapp.net": {"name": "Rosemery"},
    }
    identifier = "558699997003"

    key_sem, msg_sem = step1_sem_fix(identifier, fake_contacts)
    key_com, msg_com = step1_com_fix(identifier, fake_contacts)

    ok_sem = key_sem != "558699997003@s.whatsapp.net"
    ok_com = key_com == "558699997003@s.whatsapp.net"

    print(f"  SEM fix → key='{key_sem}' ({msg_sem})")
    print(f"  Status  : {'✗ BUG confirmado — achou chave errada' if ok_sem else '? sem bug aqui'}")
    print()
    print(f"  COM fix → key='{key_com}' ({msg_com})")
    print(f"  Status  : {'✓ fix correto — achou chave certa' if ok_com else '✗ fix não resolveu'}")

    # ── Teste com contacts real ────────────────────────────────────
    if PC_PATH.exists():
        print(f"\n── Teste com {PC_PATH} ──")
        contacts = json.loads(PC_PATH.read_text(encoding="utf-8"))

        # Verificar se existe chave inválida (vazia ou phone < 8 chars)
        bad_keys = [k for k in contacts if len(k.split("@")[0].split(":")[0]) < 8]
        print(f"  Chaves com phone < 8 chars: {bad_keys or 'nenhuma'}")

        # Buscar 558699997003
        target = "558699997003"
        key_sem, msg_sem = step1_sem_fix(target, contacts)
        key_com, msg_com = step1_com_fix(target, contacts)

        expected = "558699997003@s.whatsapp.net"
        in_contacts = expected in contacts

        print(f"  Contato alvo no arquivo: {'✓' if in_contacts else '✗ ausente!'}")
        print(f"  SEM fix → '{key_sem}' ({msg_sem})")
        print(f"  COM fix → '{key_com}' ({msg_com})")

        ok_real = key_com == expected
        print(f"  Resultado: {'✓ fix resolve o problema real' if ok_real else '✗ ainda não acha — investigar'}")
    else:
        print(f"\n[AVISO] {PC_PATH} não encontrado — pule para o container")

    print()


if __name__ == "__main__":
    main()
