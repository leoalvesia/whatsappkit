#!/bin/bash
# Monitora logs do plugin em tempo real, filtrando só o whatsapp-manager
# Uso: bash watch_plugin.sh
echo "=== Monitorando whatsapp-manager (Ctrl+C para sair) ==="
tail -f /opt/data/.hermes/logs/hermes.log 2>/dev/null \
  || journalctl -u hermes -f 2>/dev/null \
  || docker logs -f hermes 2>/dev/null \
  | grep --line-buffered "whatsapp-manager"
