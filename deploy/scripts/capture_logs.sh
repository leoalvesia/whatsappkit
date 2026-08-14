#!/bin/bash
# Captura logs do processo hermes em /tmp/hermes_debug.log
# Uso: bash capture_logs.sh [segundos]
# Depois: python3 diagnose_bridge_dedup.py /tmp/hermes_debug.log

DURATION=${1:-30}
OUT=/tmp/hermes_debug.log

# PID do processo hermes gateway
PID=$(ps aux | grep "hermes gateway run" | grep -v grep | awk '{print $1}' | head -1)

if [ -z "$PID" ]; then
    echo "Processo hermes não encontrado. Tentando PID 7..."
    PID=7
fi

echo "Capturando output do PID $PID por ${DURATION}s → $OUT"
echo "Mande uma mensagem pelo WhatsApp durante esse tempo."
echo ""

# Usar strace para capturar writes do processo hermes
> "$OUT"
timeout "$DURATION" strace -p "$PID" -e trace=write -s 300 -q 2>&1 \
    | grep -o '"[^"]*"' \
    | sed 's/^"//;s/"$//' \
    | tr -d '\\n' \
    | sed 's/\\n/\n/g' \
    | grep "whatsapp-manager" \
    >> "$OUT" &

STRACE_PID=$!
echo "Aguardando ${DURATION}s..."
sleep "$DURATION"
kill "$STRACE_PID" 2>/dev/null

LINES=$(wc -l < "$OUT")
echo "Capturado: $LINES linhas em $OUT"
echo ""

if [ "$LINES" -eq 0 ]; then
    echo "Sem output via strace. Tentando /proc/$PID/fd/1..."
    # Alternativa: ler stderr do processo
    timeout 5 cat /proc/"$PID"/fd/2 2>/dev/null | grep "whatsapp-manager" | tee "$OUT"
fi

echo ""
echo "Agora rode:"
echo "  python3 /opt/data/workspace/hermes-whatsapp-mixed/deploy/scripts/diagnose_bridge_dedup.py $OUT"
