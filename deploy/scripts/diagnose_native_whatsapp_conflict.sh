#!/bin/bash
# Diagnóstico: conflito entre o plugin whatsapp-manager (bridge.js próprio)
# e a plataforma WhatsApp nativa do Hermes Agent >= 0.19 ("Quicksilver").
#
# Roda dentro do container hermes (Portainer → Console, ou `docker exec -it hermes bash`).
# Somente leitura — não mata processos nem altera arquivos.
#
# Uso: bash diagnose_native_whatsapp_conflict.sh [porta]
set -uo pipefail

PORT="${1:-3000}"
HERMES_DIR="${HERMES_HOME:-/opt/data/.hermes}"
BRIDGE_FILE="${HERMES_DIR}/platforms/whatsapp/bridge/bridge.js"
SESSION_DIR="${HERMES_DIR}/platforms/whatsapp/session"

hr() { printf '%s\n' "----------------------------------------------------------------"; }

echo "=== 1. Versão do Hermes ==="
if command -v hermes >/dev/null 2>&1; then
    hermes --version 2>&1
else
    echo "binário 'hermes' não encontrado no PATH"
fi
hr

echo "=== 2. Variáveis de ambiente relevantes ==="
env | grep -E '^WHATSAPP_' | sort
if [ -z "$(env | grep -E '^WHATSAPP_ENABLED')" ]; then
    echo "WHATSAPP_ENABLED não está setada"
fi
hr

echo "=== 3. Quem está escutando na porta ${PORT} ==="
LISTEN_PID=""
if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"${PORT}" -sTCP:LISTEN -n -P 2>/dev/null
    LISTEN_PID=$(lsof -tiTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null | head -1)
elif command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :${PORT}" 2>/dev/null
    LISTEN_PID=$(ss -ltnp "sport = :${PORT}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1)
else
    echo "nem lsof nem ss disponíveis — instale um dos dois para checar a porta"
fi

if [ -n "${LISTEN_PID}" ]; then
    echo ""
    echo "--> PID ${LISTEN_PID} escutando na porta ${PORT}. Cmdline completa:"
    tr '\0' ' ' < "/proc/${LISTEN_PID}/cmdline" 2>/dev/null; echo
    echo ""
    echo "--> Caminho do script Node (se aplicável):"
    tr '\0' '\n' < "/proc/${LISTEN_PID}/cmdline" 2>/dev/null | grep -i '\.js$'
else
    echo "Nenhum processo escutando na porta ${PORT} agora (bridge pode estar caída ou usando outra porta)."
fi
hr

echo "=== 4. Todos os processos node/bridge ativos ==="
ps -eo pid,ppid,etime,cmd 2>/dev/null | grep -iE 'node|bridge\.js' | grep -v grep
hr

echo "=== 5. bridge.js em disco: qual versão é (custom vs nativa)? ==="
if [ -f "${BRIDGE_FILE}" ]; then
    echo "Arquivo: ${BRIDGE_FILE}"
    echo "Tamanho / mtime:"
    ls -la "${BRIDGE_FILE}"
    echo "SHA256: $(sha256sum "${BRIDGE_FILE}" | awk '{print $1}')"
    echo ""
    CUSTOM_HITS=$(grep -cE 'matchesAllowedUser|calcDebounceDelay|/whatsapp/qr' "${BRIDGE_FILE}" 2>/dev/null)
    NATIVE_HITS=$(grep -cE 'send-poll|send-location|SendResult' "${BRIDGE_FILE}" 2>/dev/null)
    echo "Marcadores do bridge CUSTOM deste projeto encontrados: ${CUSTOM_HITS}"
    echo "Marcadores do bridge NATIVO (v0.19+, polls/location) encontrados: ${NATIVE_HITS}"
    if [ "${CUSTOM_HITS:-0}" -gt 0 ] && [ "${NATIVE_HITS:-0}" -eq 0 ]; then
        echo "==> Este é o bridge.js DO PLUGIN (whatsapp-manager)."
    elif [ "${NATIVE_HITS:-0}" -gt 0 ] && [ "${CUSTOM_HITS:-0}" -eq 0 ]; then
        echo "==> Este é o bridge.js NATIVO do Hermes — o do plugin foi sobrescrito ou nunca copiado!"
    elif [ "${NATIVE_HITS:-0}" -gt 0 ] && [ "${CUSTOM_HITS:-0}" -gt 0 ]; then
        echo "==> AMBIGUO: marcadores dos dois aparecem — arquivo pode ter sido parcialmente sobrescrito."
    else
        echo "==> Nenhum marcador reconhecido — versão desconhecida."
    fi
else
    echo "Arquivo ${BRIDGE_FILE} não existe."
fi
hr

echo "=== 6. Diretório de sessão (colisão de state) ==="
if [ -d "${SESSION_DIR}" ]; then
    echo "Conteúdo de ${SESSION_DIR}:"
    ls -la "${SESSION_DIR}"
    echo ""
    if [ -f "${SESSION_DIR}/bridge.pid" ]; then
        echo "bridge.pid: $(cat "${SESSION_DIR}/bridge.pid")"
    fi
    if [ -f "${SESSION_DIR}/creds.json" ]; then
        echo "creds.json mtime: $(stat -c '%y' "${SESSION_DIR}/creds.json" 2>/dev/null || stat -f '%Sm' "${SESSION_DIR}/creds.json" 2>/dev/null)"
    fi
else
    echo "Diretório ${SESSION_DIR} não existe."
fi
hr

echo "=== 7. Logs do gateway — evidência de re-registro de plataforma ==="
LOG_SOURCES_FOUND=0
if command -v journalctl >/dev/null 2>&1 && journalctl -u hermes --no-pager -n 1 >/dev/null 2>&1; then
    LOG_SOURCES_FOUND=1
    echo "-- via journalctl --"
    journalctl -u hermes --no-pager -n 5000 2>/dev/null \
        | grep -iE "platform 'whatsapp'|re-registered|register_platform|whatsapp.*adapter|bridge\.js" \
        | tail -n 40
fi
for LOGFILE in "${HERMES_DIR}/logs/gateway.log" "${HERMES_DIR}/gateway.log" "/opt/data/.hermes/platforms/whatsapp/bridge.log"; do
    if [ -f "${LOGFILE}" ]; then
        LOG_SOURCES_FOUND=1
        echo "-- via ${LOGFILE} --"
        grep -iE "platform 'whatsapp'|re-registered|register_platform|whatsapp.*adapter" "${LOGFILE}" 2>/dev/null | tail -n 40
    fi
done
if [ "${LOG_SOURCES_FOUND}" -eq 0 ]; then
    echo "Nenhuma fonte de log conhecida encontrada (journalctl/gateway.log). Ajuste os caminhos no script se o seu setup for diferente."
fi
hr

echo "=== 8. Registry de plataformas — consulta direta (best-effort) ==="
PYBIN=$(command -v python3 || command -v python)
if [ -n "${PYBIN}" ]; then
    "${PYBIN}" - <<'PYEOF' 2>&1
try:
    from gateway.platform_registry import platform_registry
    platform_registry._resolve_all()
    entry = platform_registry.get("whatsapp")
    if entry is None:
        print("Nenhuma entrada 'whatsapp' registrada no momento desta checagem.")
    else:
        print(f"name={entry.name} label={entry.label} source={getattr(entry, 'source', '?')}")
        print(f"adapter_factory={entry.adapter_factory}")
except Exception as e:
    print(f"Não foi possível consultar o registry neste processo (esperado se rodar fora do processo do gateway): {e}")
PYEOF
else
    echo "python3 não encontrado."
fi
hr

echo "=== RESUMO ==="
echo "Porta ${PORT} ocupada por PID: ${LISTEN_PID:-nenhum}"
echo "bridge.js em disco: $( [ -f "${BRIDGE_FILE}" ] && echo 'presente' || echo 'AUSENTE' )"
echo "Revise as seções 3, 5 e 7 acima: se os marcadores do bridge em disco não baterem"
echo "com o processo realmente escutando na porta, ou se aparecer 're-registered' nos logs,"
echo "há conflito confirmado entre o plugin e a plataforma nativa."
