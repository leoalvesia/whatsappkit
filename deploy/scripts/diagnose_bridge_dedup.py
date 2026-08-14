#!/usr/bin/env python3
"""
Diagnóstico: valida se o bridge entrega o mesmo messageId duas vezes.

Injeta um patch em whatsapp_manager para logar cada messageId recebido
e contar duplicatas. Lê o log em tempo real e exibe um resumo.

Uso no container hermes:
    python3 /opt/data/workspace/hermes-whatsapp-mixed/deploy/scripts/diagnose_bridge_dedup.py

Ctrl+C para parar e ver o resumo.
"""

import sys
import os
import re
import time
import subprocess
from collections import defaultdict, Counter
from pathlib import Path

PLUGIN_PATH = Path("/opt/data/.hermes/plugins/whatsapp-manager/whatsapp_manager.py")
LOG_CANDIDATES = [
    "/opt/data/.hermes/logs/hermes.log",
    "/opt/hermes/hermes.log",
    "/tmp/hermes.log",
]

# ── Verificar se o plugin tem o dedup de message_id ───────────────────────────

def check_plugin():
    if not PLUGIN_PATH.exists():
        print(f"[ERRO] Plugin não encontrado em {PLUGIN_PATH}")
        sys.exit(1)
    src = PLUGIN_PATH.read_text(encoding="utf-8")
    has_dedup = "_seen_message_ids" in src
    has_pre_tool = "pre_tool_call" in src
    has_turn = "_turn_key" in src
    print("=== Status do plugin ativo ===")
    print(f"  dedup de message_id (pre_gateway_dispatch): {'✓' if has_dedup else '✗ AUSENTE'}")
    print(f"  pre_tool_call registrado:                   {'✓' if has_pre_tool else '✗ AUSENTE'}")
    print(f"  controle de turno (_turn_key):              {'✓' if has_turn else '✗ AUSENTE'}")
    print()
    return has_dedup


# ── Encontrar o log ────────────────────────────────────────────────────────────

def find_log():
    for path in LOG_CANDIDATES:
        if os.path.exists(path):
            return path
    # Tentar via processo do hermes
    try:
        result = subprocess.run(
            ["find", "/opt", "/var/log", "-name", "*.log", "-newer", "/opt/hermes/setup-hermes.sh"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if "hermes" in line.lower():
                return line.strip()
    except Exception:
        pass
    return None


# ── Monitor em tempo real ──────────────────────────────────────────────────────

def monitor_log(log_path: str):
    print(f"=== Monitorando {log_path} ===")
    print("Mande uma mensagem pelo WhatsApp e observe o output abaixo.")
    print("Ctrl+C para parar.\n")

    msg_id_count: Counter = Counter()
    pre_gw_calls = 0
    post_llm_calls = 0
    sends = 0
    duplicates_blocked = 0

    pattern_msg_id   = re.compile(r"Mensagem duplicada '([^']+)'")
    pattern_pre_gw   = re.compile(r"\[pre_gateway_dispatch\]")
    pattern_post_llm = re.compile(r"\[post_llm_call\] chamado")
    pattern_send     = re.compile(r"Enviando ao contato")
    pattern_turno    = re.compile(r"Novo turno para")
    pattern_bloq     = re.compile(r"(já respondido|Turno.*ignorando|Bloqueando tool)")

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)  # ir para o final
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue

                line = line.rstrip()

                if pattern_pre_gw.search(line):
                    pre_gw_calls += 1
                    print(f"  [IN]  {line}")

                if pattern_post_llm.search(line):
                    post_llm_calls += 1
                    print(f"  [LLM] {line}")

                if pattern_send.search(line):
                    sends += 1
                    print(f"  [SEND] {line}")

                if pattern_turno.search(line):
                    print(f"  [TURN] {line}")

                if pattern_bloq.search(line):
                    duplicates_blocked += 1
                    print(f"  [BLOQUED] {line}")

                if pattern_msg_id.search(line):
                    mid = pattern_msg_id.search(line).group(1)
                    msg_id_count[mid] += 1
                    print(f"  [DUP!] messageId duplicado: {mid}")

    except KeyboardInterrupt:
        pass

    print("\n=== Resumo ===")
    print(f"  pre_gateway_dispatch chamado: {pre_gw_calls}x")
    print(f"  post_llm_call chamado:        {post_llm_calls}x")
    print(f"  _human_send disparado:        {sends}x")
    print(f"  duplicatas bloqueadas:        {duplicates_blocked}x")
    if msg_id_count:
        print(f"  messageIds duplicados vistos: {dict(msg_id_count)}")
    else:
        print("  nenhum messageId duplicado detectado no log")
    print()
    if sends > post_llm_calls:
        print("  ⚠ sends > post_llm_calls: _human_send chamado fora do post_llm_call")
    if post_llm_calls > pre_gw_calls:
        print("  ⚠ post_llm_call > pre_gateway_dispatch: mais ciclos LLM que mensagens recebidas")
    if pre_gw_calls > 1 and msg_id_count:
        print("  ✓ Hipótese confirmada: bridge entregou a mesma mensagem duas vezes")
    elif pre_gw_calls > 1 and not msg_id_count:
        print("  ⚠ pre_gateway_dispatch chamado múltiplas vezes mas sem messageId duplicado")
        print("    → mensagens distintas OU messageId não está disponível no evento")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    check_plugin()

    # Modo stdin: lê linhas coladas/redirecionadas de stdin
    # Uso: python3 diagnose... < /tmp/log.txt
    # Ou:  cat /proc/7/fd/2 2>/dev/null | python3 diagnose...
    # Ou pipar a saída do hermes para o script enquanto ele roda

    if len(sys.argv) > 1 and sys.argv[1] != "-":
        log_path = sys.argv[1]
        monitor_log(log_path)
    else:
        print("=== Lendo do stdin (cole linhas de log ou redirecione) ===")
        print("Ctrl+C ou Ctrl+D para parar.\n")
        # Reutiliza o mesmo parser mas lendo de sys.stdin linha a linha
        import io
        monitor_log.__globals__['open'] = lambda path, *a, **kw: sys.stdin
        monitor_log("-")  # o path é ignorado pois open foi patchado
