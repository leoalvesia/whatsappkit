#!/usr/bin/env python3
"""Testa a transcrição de áudio do plugin whatsapp-manager.

Uso:
    python3 test_audio_transcription.py [caminho_do_audio.ogg]

Se não informar o arquivo, usa o mais recente do audio_cache.
"""
import json
import os
import sys
import base64
import urllib.request
import urllib.error
from pathlib import Path


HERMES_HOME = os.getenv("HERMES_HOME", "/opt/data/.hermes")
AUDIO_CACHE = Path(HERMES_HOME) / "audio_cache"
AUTH_JSON = Path(HERMES_HOME) / "auth.json"


def get_google_key():
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not key and AUTH_JSON.exists():
        try:
            auth = json.loads(AUTH_JSON.read_text())
            key = (auth.get("credential_pool", {}).get("gemini", "") or "").strip()
            if key:
                print(f"  [OK] GOOGLE_API_KEY lida do auth.json")
        except Exception as e:
            print(f"  [ERRO] Falha ao ler auth.json: {e}")
    elif key:
        print(f"  [OK] GOOGLE_API_KEY lida do ambiente")
    return key


def get_openai_key():
    return os.getenv("OPENAI_API_KEY", "").strip()


def get_openrouter_key():
    return os.getenv("OPENROUTER_API_KEY", "").strip()


def find_audio_file(path_arg=None):
    if path_arg:
        p = Path(path_arg)
        if p.exists():
            return p
        print(f"[ERRO] Arquivo não encontrado: {path_arg}")
        sys.exit(1)

    if not AUDIO_CACHE.exists():
        print(f"[ERRO] audio_cache não encontrado: {AUDIO_CACHE}")
        sys.exit(1)

    files = sorted(AUDIO_CACHE.glob("aud_*.ogg"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        print(f"[ERRO] Nenhum arquivo .ogg encontrado em {AUDIO_CACHE}")
        sys.exit(1)

    return files[0]


def transcribe_gemini(audio_path, google_key):
    model = os.getenv("WHATSAPP_CLIENT_MEDIA_MODEL", "gemini-3.1-flash-lite")
    mime = "audio/ogg"
    b64 = base64.b64encode(audio_path.read_bytes()).decode()
    prompt = "Transcreva o áudio de forma literal e precisa, em português. Retorne APENAS o texto da transcrição, sem nenhuma introdução, explicação, aspas ou comentários."
    payload = {"contents": [{"parts": [
        {"inlineData": {"mimeType": mime, "data": b64}},
        {"text": prompt}
    ]}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={google_key}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=45) as resp:
        result = json.loads(resp.read().decode())
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()


def transcribe_openai(audio_path, openai_key):
    b64 = base64.b64encode(audio_path.read_bytes()).decode()
    prompt = "Transcreva o áudio de forma literal e precisa, em português. Retorne APENAS o texto da transcrição."
    payload = {
        "model": "gpt-4o-audio-preview",
        "modalities": ["text"],
        "messages": [{"role": "user", "content": [
            {"type": "input_audio", "input_audio": {"data": b64, "format": "wav"}},
            {"type": "text", "text": prompt},
        ]}],
    }
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"}, method="POST")
    with urllib.request.urlopen(req, timeout=45) as resp:
        result = json.loads(resp.read().decode())
        return result["choices"][0]["message"]["content"].strip()


def main():
    print("=" * 60)
    print("Teste de Transcrição de Áudio — whatsapp-manager")
    print("=" * 60)

    audio_path = find_audio_file(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"\nArquivo: {audio_path}")
    print(f"Tamanho: {audio_path.stat().st_size / 1024:.1f} KB")

    print("\n--- Verificando chaves ---")
    google_key = get_google_key()
    openai_key = get_openai_key()
    openrouter_key = get_openrouter_key()

    print(f"  GOOGLE_API_KEY:    {'✓ configurada' if google_key else '✗ ausente'}")
    print(f"  OPENAI_API_KEY:    {'✓ configurada' if openai_key else '✗ ausente'}")
    print(f"  OPENROUTER_API_KEY:{'✓ configurada' if openrouter_key else '✗ ausente'}")

    if not google_key and not openai_key and not openrouter_key:
        print("\n[ERRO] Nenhuma API key disponível. Configure pelo menos uma.")
        sys.exit(1)

    print("\n--- Transcrevendo ---")

    if google_key:
        print("  Tentando Gemini...", end=" ", flush=True)
        try:
            text = transcribe_gemini(audio_path, google_key)
            print(f"✓")
            print(f"\n[Resultado Gemini]\n{text}")
            return
        except Exception as e:
            print(f"✗ {e}")

    if openai_key:
        print("  Tentando OpenAI...", end=" ", flush=True)
        try:
            text = transcribe_openai(audio_path, openai_key)
            print(f"✓")
            print(f"\n[Resultado OpenAI]\n{text}")
            return
        except Exception as e:
            print(f"✗ {e}")

    print("\n[ERRO] Todos os provedores falharam.")
    sys.exit(1)


if __name__ == "__main__":
    main()
