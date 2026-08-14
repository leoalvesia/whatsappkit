"""Teste local do Gemini gemini-3.5-flash para diagnosticar truncamento de JSON.

Uso:
    GOOGLE_API_KEY=xxx python3 tests/test_gemini_classification.py

O script:
  1. Faz a mesma chamada que _classify_contact_via_llm faz.
  2. Testa com maxOutputTokens=1024 (atual) e 4096 (proposto).
  3. Loga finishReason, tamanho da resposta e se o JSON parseou.
  4. Salva a resposta bruta em /tmp para inspeção.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

MODEL = "gemini-3.1-flash-lite"

# Prompt reduzido mas fiel ao usado em _classify_contact_via_llm
PROMPT = (
    "You are a classification assistant for a WhatsApp bot.\n"
    "The owner of the WhatsApp account is named André Alencar.\n"
    "Your task is to analyze the recent conversation history and statistics between André and a contact named 'Carlos Silva' "
    "to classify their relationship, tone, nickname, pet names (terms of endearment), frequent greetings, "
    "conversation summary, the intent of their latest interactions, the frequency of their conversations, "
    "and specific guidelines for the bot when responding to them.\n\n"
    "Conversation Statistics:\n"
    "Total messages: 47. First message date: 2024-03-15. Last message date: 2025-11-02.\n\n"
    "Recent Chat history:\n"
    "[André]: eae carlos, beleza?\n"
    "[Carlos]: eae mano, tudo certo! bora marcar aquele futebol sabado?\n"
    "[André]: pode ser, que horas?\n"
    "[Carlos]: 10h la no parque. leva o clebin tb\n"
    "[André]: blz mano, vou chamar ele. valeu!\n"
    "[Carlos]: tranquilo, depois me confirma. abraco\n"
    "[André]: abraco carlos, tmj!\n"
    "[Carlos]: eae andré, conseguiu resolver aquela parada do cliente?\n"
    "[André]: sim mano, era só uma config no crm. agora ta rodando liso\n"
    "[Carlos]: que bom! parabens. e o churrasco de domingo ta confirmado?\n"
    "[André]: confirmado, leva a cerveja gelada rs\n"
    "[Carlos]: pode deixar, chego cedo. ate la\n"
    "[André]: valeu! ate\n\n\n"
    "Classify into one of: Amigo, AmigoProximo, Parente, Filho, Cliente, Vendedor.\n\n"
    "Return a JSON object with this exact structure (do NOT wrap it in markdown code blocks like ```json, just raw JSON):\n"
    "{\n"
    '  "relationship": "Amigo" | "AmigoProximo" | "Parente" | "Filho" | "Cliente" | "Vendedor",\n'
    '  "tone": "informal e carinhoso" | "informal e amigável" | "polido e profissional" | "técnico e direto",\n'
    '  "nickname": string | null,\n'
    '  "pet_name": string | null,\n'
    '  "frequent_greeting": string | null,\n'
    '  "summary": "...máx 150 caracteres...",\n'
    '  "intent": "...máx 100 caracteres...",\n'
    '  "frequency": "diária" | "semanal" | "mensal" | "esporádica",\n'
    '  "product": string | null,\n'
    '  "guidelines": "...máx 200 caracteres..."\n'
    "}"
)


def call_gemini(api_key: str, max_tokens: int, timeout: int = 45) -> dict:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
        f"?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": PROMPT}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": max_tokens,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    started = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    elapsed_ms = int((time.time() - started) * 1000)
    return {"body": body, "elapsed_ms": elapsed_ms}


def analyze(body: str) -> dict:
    """Extrai finishReason, tamanho e tenta parsear o JSON."""
    result = json.loads(body)
    candidate = result["candidates"][0]
    finish_reason = candidate.get("finishReason", "UNKNOWN")
    parts = candidate.get("content", {}).get("parts", [])
    text_content = parts[0].get("text", "") if parts else ""
    usage = result.get("usageMetadata", {})

    parsed_ok = False
    parsed_err = None
    parsed_data = None
    try:
        parsed_data = json.loads(text_content)
        parsed_ok = True
    except json.JSONDecodeError as e:
        parsed_err = str(e)

    return {
        "finish_reason": finish_reason,
        "text_len": len(text_content),
        "output_tokens": usage.get("candidatesTokenCount"),
        "thoughts_tokens": usage.get("thoughtsTokenCount"),
        "total_tokens": usage.get("totalTokenCount"),
        "parsed_ok": parsed_ok,
        "parsed_err": parsed_err,
        "text_content": text_content,
        "parsed_data": parsed_data,
    }


def balance_braces(text: str) -> str:
    """Fecha chaves faltantes (mesma lógica proposta para _extract_json_from_text)."""
    depth = 0
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
    return text + ("}" * depth) if depth > 0 else text


def try_recover(text: str) -> dict | None:
    """Tenta parsear fechando chaves faltantes."""
    if not text or "{" not in text:
        return None
    recovered = balance_braces(text)
    try:
        return json.loads(recovered)
    except json.JSONDecodeError:
        pass
    # Tentar cortar no último campo completo (após `null` ou `}`)
    for sep in ['"null"', '"Cliente"', '"Amigo"', '"Vendedor"']:
        idx = text.rfind(sep)
        if idx == -1:
            continue
        candidate = balance_braces(text[: idx + len(sep)])
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def main() -> int:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        print("ERRO: defina GOOGLE_API_KEY no ambiente antes de rodar.")
        print("Ex: GOOGLE_API_KEY=xxx python3 tests/test_gemini_classification.py")
        return 2

    print(f"Modelo: {MODEL}")
    print(f"Prompt len: {len(PROMPT)} chars (~{len(PROMPT)//4} tokens estimados)")
    print("=" * 70)

    results = []
    for max_tokens in (1024, 4096):
        print(f"\n>>> Testando com maxOutputTokens={max_tokens}")
        try:
            r = call_gemini(api_key, max_tokens)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")[:500]
            print(f"  HTTP {e.code}: {err_body}")
            results.append({"max_tokens": max_tokens, "http_error": e.code, "body": err_body})
            continue
        except Exception as e:
            print(f"  Erro: {e}")
            results.append({"max_tokens": max_tokens, "error": str(e)})
            continue

        info = analyze(r["body"])
        info["max_tokens"] = max_tokens
        info["http_elapsed_ms"] = r["elapsed_ms"]
        results.append(info)

        print(f"  HTTP {r['elapsed_ms']}ms")
        print(f"  finishReason:   {info['finish_reason']}")
        print(f"  text length:    {info['text_len']} chars")
        print(f"  output tokens:  {info['output_tokens']}")
        print(f"  total tokens:   {info['total_tokens']}")
        print(f"  JSON parse OK:  {info['parsed_ok']}")
        if info["parsed_err"]:
            print(f"  parse error:    {info['parsed_err'][:120]}")

        if info["parsed_ok"]:
            print(f"  CAMPOS: {sorted(info['parsed_data'].keys())}")
        else:
            # Tentar recuperação
            recovered = try_recover(info["text_content"])
            if recovered:
                print(f"  RECUPERADO: {sorted(recovered.keys())}")
                print(f"    -> relationship={recovered.get('relationship')!r}")
            else:
                tail = info["text_content"][-200:]
                print(f"  ÚLTIMOS 200 CHARS: {tail!r}")

        # Salvar resposta bruta
        out_path = f"/tmp/gemini_response_{max_tokens}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(r["body"])
        print(f"  Resposta salva em: {out_path}")

    print("\n" + "=" * 70)
    print("RESUMO:")
    print("=" * 70)
    for r in results:
        if "http_error" in r:
            print(f"maxTokens={r['max_tokens']}: HTTP {r['http_error']}")
        elif "error" in r:
            print(f"maxTokens={r['max_tokens']}: erro de rede")
        else:
            status = "OK" if r["parsed_ok"] else "FALHOU"
            rec = ""
            if not r["parsed_ok"]:
                rec = try_recover(r["text_content"])
                rec = " (recuperável)" if rec else " (irrecuperável)"
            print(
                f"maxTokens={r['max_tokens']:>5}: {status:6} "
                f"finish={r['finish_reason']:10} "
                f"tokens={r['output_tokens']:>4} "
                f"len={r['text_len']:>5} chars{rec}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
