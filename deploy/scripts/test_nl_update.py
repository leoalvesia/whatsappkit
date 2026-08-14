#!/usr/bin/env python3
"""Testa a classificação de intenção e extração de campos NL via LLM.

Uso:
    python3 test_nl_update.py                    # suite completa
    python3 test_nl_update.py "mensagem aqui"    # teste ad-hoc
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

HERMES_HOME = os.getenv("HERMES_HOME", "/opt/data/.hermes")
AUTH_JSON = Path(HERMES_HOME) / "auth.json"

# (mensagem, is_update esperado, contact_name esperado, campos esperados)
CASOS_INTENT = [
    # Devem ser detectados como update
    ("coloque a Mayra como namorada",                    True,  "Mayra",  {"relationship": "AmigoProximo", "manual_relationship": "Namorada"}),
    ("coloque o Pedro como filho",                       True,  "Pedro",  {"relationship": "Filho"}),
    ("cadastre um apelido para Pedro, o apelido é Pedrinho", True, "Pedro", {"nickname": "Pedrinho"}),
    ("coloque uma observação no Juan: ele prefere WhatsApp", True, "Juan", {"notes": "ele prefere WhatsApp"}),
    ("o apelido da Mayra é May",                         True,  "Mayra",  {"nickname": "May"}),
    ("atualize o nome para Juan Carlos",                 True,  "Juan",   {"name": "Juan Carlos"}),
    ("coloque uma nota no Pedro: mora em São Paulo",     True,  "Pedro",  {"notes": "mora em São Paulo"}),
    ("anote que a Vivi Oliveira prefere contato por e-mail", True, "Vivi", {"notes": "prefere contato por e-mail"}),
    # NÃO devem ser detectados como update
    ("qual o saldo da conta?",                           False, None, {}),
    ("manda um relatório de vendas",                     False, None, {}),
    ("o que você acha do Pedro?",                        False, None, {}),
    ("me lembra de ligar para o Juan amanhã",            False, None, {}),
]


def get_google_key():
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not key and AUTH_JSON.exists():
        try:
            auth = json.loads(AUTH_JSON.read_text())
            key = (auth.get("credential_pool", {}).get("gemini", "") or "").strip()
        except Exception:
            pass
    return key


def get_model():
    return os.getenv("WHATSAPP_CONTACT_CLASSIFIER_MODEL", "gemini-3.1-flash-lite")


def call_api(url, headers, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"(\{[\s\S]*\})", text)
        if m:
            return json.loads(m.group(1))
        raise


def classify_intent(message: str, google_key: str, model: str) -> dict:
    clean_msg = message
    m = re.match(r'\[Áudio:\s*"(.+?)"\]', message, re.IGNORECASE | re.DOTALL)
    if m:
        clean_msg = m.group(1)

    prompt = (
        "Você é um classificador de intenções para um assistente de WhatsApp.\n"
        "Analise a mensagem do usuário e determine se é um COMANDO DE ATUALIZAÇÃO DE CONTATO.\n\n"
        "É um comando de atualização quando o usuário quer:\n"
        "- Mudar/definir o relacionamento, apelido, observação, nome ou produto de um contato\n"
        "- Exemplos: 'coloque a Mayra como namorada', 'cadastre um apelido para Pedro como Pedrinho',\n"
        "  'coloque uma observação no Juan', 'atualize o nome da Viviane', 'defina o Pedro como filho'\n\n"
        "NÃO é atualização quando o usuário:\n"
        "- Faz perguntas, pedidos ao bot, ou comandos gerais sem mencionar um contato específico\n\n"
        f"Mensagem: \"{clean_msg}\"\n\n"
        "Retorne APENAS JSON:\n"
        "Se for atualização: {\"is_update\": true, \"contact_name\": \"nome do contato mencionado\", \"intent\": \"descrição em 5 palavras\"}\n"
        "Se não for: {\"is_update\": false, \"intent\": \"descrição em 5 palavras\"}\n"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 128}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={google_key}"
    result = call_api(url, {"Content-Type": "application/json"}, payload)
    text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
    return extract_json(text)


def extract_fields(contact_name: str, message: str, google_key: str, model: str) -> dict:
    prompt = (
        f"O usuário pediu para atualizar o contato '{contact_name}' com a seguinte instrução:\n"
        f"\"{message}\"\n\n"
        "Extraia SOMENTE os campos explicitamente mencionados e retorne um JSON.\n"
        "Campos permitidos: relationship, manual_relationship, nickname, pet_name, notes, product, name.\n"
        "- notes = observação/anotação (texto livre)\n"
        "- nickname = apelido\n"
        "- relationship enum: Amigo, AmigoProximo, Parente, Filho, Cliente, Vendedor\n"
        "- manual_relationship: valor livre (ex: Namorada, Filho, Esposa, Cliente VIP)\n"
        "NÃO invente campos. Retorne APENAS JSON.\n"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 256}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={google_key}"
    result = call_api(url, {"Content-Type": "application/json"}, payload)
    text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
    return extract_json(text)


def run_case(message, expected_update, expected_name, expected_fields, google_key, model):
    print(f"\n  Mensagem : {message}")
    try:
        intent = classify_intent(message, google_key, model)
        is_update = intent.get("is_update", False)
        contact_name = intent.get("contact_name", "")
        intent_label = intent.get("intent", "")
        print(f"  Intenção : is_update={is_update} | intent='{intent_label}' | contato='{contact_name}'")

        ok_intent = is_update == expected_update
        ok_name = True
        ok_fields = True
        fields = {}

        if is_update and expected_update:
            # Validar nome extraído (case-insensitive, substring)
            ok_name = expected_name and expected_name.lower() in contact_name.lower()
            if not ok_name:
                print(f"  *** NOME ERRADO: esperado '{expected_name}', got '{contact_name}'")

            # Extrair campos e validar
            fields = extract_fields(contact_name or expected_name, message, google_key, model)
            print(f"  Campos   : {json.dumps(fields, ensure_ascii=False)}")
            for k, v in expected_fields.items():
                if k not in fields:
                    print(f"  *** CAMPO AUSENTE: '{k}' não extraído")
                    ok_fields = False
                elif v and v.lower() not in str(fields[k]).lower():
                    print(f"  *** VALOR ERRADO: '{k}'='{fields[k]}' (esperado '{v}')")
                    ok_fields = False

        elif not is_update and expected_update:
            print(f"  *** FALSO NEGATIVO: deveria ser update mas não foi detectado")
            ok_intent = False

        elif is_update and not expected_update:
            print(f"  *** FALSO POSITIVO: não deveria ser update mas foi detectado")
            ok_intent = False

        passed = ok_intent and ok_name and ok_fields
        print(f"  Status   : {'✓ OK' if passed else '✗ FALHOU'}")
        return passed

    except Exception as e:
        print(f"  ERRO: {e}")
        return False


def main():
    print("=" * 65)
    print("Teste de Intenção NL + Extração de Campos — whatsapp-manager")
    print("=" * 65)

    google_key = get_google_key()
    if not google_key:
        print("[ERRO] GOOGLE_API_KEY não encontrada (env nem auth.json)")
        sys.exit(1)

    model = get_model()
    print(f"\nModelo : {model}")

    # Modo ad-hoc
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        print(f"\n--- Teste ad-hoc ---")
        try:
            intent = classify_intent(message, google_key, model)
            print(f"  Intenção : {json.dumps(intent, ensure_ascii=False)}")
            if intent.get("is_update"):
                name = intent.get("contact_name", "Contato")
                fields = extract_fields(name, message, google_key, model)
                print(f"  Campos   : {json.dumps(fields, ensure_ascii=False)}")
        except Exception as e:
            print(f"  ERRO: {e}")
        return

    # Suite completa
    updates = [c for c in CASOS_INTENT if c[1]]
    non_updates = [c for c in CASOS_INTENT if not c[1]]
    print(f"\n--- {len(updates)} casos de UPDATE + {len(non_updates)} casos de NÃO-UPDATE ---")

    ok = 0
    for msg, exp_update, exp_name, exp_fields in CASOS_INTENT:
        if run_case(msg, exp_update, exp_name, exp_fields, google_key, model):
            ok += 1

    total = len(CASOS_INTENT)
    print(f"\n{'=' * 65}")
    print(f"Resultado: {ok}/{total} casos corretos")
    if ok < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
