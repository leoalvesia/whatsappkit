#!/bin/bash
# Diagnóstico de respostas duplicadas — roda no console do container hermes
# Uso: bash diagnose_duplicates.sh [minutos_atras]
MINS=${1:-5}
echo "=== post_llm_call nos últimos ${MINS} minutos ==="
journalctl -u hermes --no-pager -n 2000 2>/dev/null \
  | grep -E "post_llm_call (chamado|Enviando|Turno|Debounce|Dedup)" \
  | tail -n 60 \
  | while IFS= read -r line; do
      ts=$(echo "$line" | grep -oP '\d{2}:\d{2}:\d{2}')
      echo "$ts $line"
    done

echo ""
echo "=== Contagem de 'Enviando ao contato' ==="
journalctl -u hermes --no-pager -n 2000 2>/dev/null \
  | grep "Enviando ao contato" | wc -l

echo ""
echo "=== Threads ativas no processo hermes ==="
ps -eLf | grep hermes | grep -v grep | wc -l
