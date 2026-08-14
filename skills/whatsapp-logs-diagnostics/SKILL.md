---
name: whatsapp-logs-diagnostics
description: "Consulta os logs em tempo real, status e saúde da integração do WhatsApp através do endpoint /whatsapp/debug do bridge."
category: diagnostics
---

# Diagnóstico e Logs do WhatsApp

Esta skill orienta o agente a acessar e obter os logs de erro, status de pareamento e informações de diagnóstico do WhatsApp.

---

## Quando usar esta skill

Use quando o usuário solicitar informações de diagnóstico do WhatsApp ou logs de erro, como:
- "verificar logs do whatsapp"
- "como ver os logs do whatsapp"
- "erro no pareamento do whatsapp"
- "diagnóstico do whatsapp"
- "ver status da conexão do whatsapp"
- "whatsapp debug"

---

## O que o agente deve fazer

### Passo 1 — Obter o domínio do servidor

O agente deve extrair a variável `HERMES_SERVER_DOMAIN` das variáveis de ambiente do sistema. 
Para fazer isso programaticamente a partir do terminal, o agente pode rodar:

```bash
python3 -c '
import os
from pathlib import Path
domain = os.getenv("HERMES_SERVER_DOMAIN")
if not domain:
    for p in ["/opt/data/.env", "/opt/data/.hermes/.env"]:
        if Path(p).exists():
            with open(p, "r") as f:
                for line in f:
                    if line.strip().startswith("HERMES_SERVER_DOMAIN="):
                        domain = line.split("=", 1)[1].strip().strip("\"'")
                        break
print(domain or "DOMINIO_NAO_CONFIGURADO")
'
```

* Nota: Se o domínio retornar `DOMINIO_NAO_CONFIGURADO`, informe ao usuário que ele precisa configurar a variável `HERMES_SERVER_DOMAIN` na stack do Portainer (ou arquivo `.env`) para conseguir visualizar via browser externo.

---

### Passo 2 — Diagnóstico via Requisição Local (se executado pelo agente no terminal)

Caso o próprio agente precise investigar o status do bridge para ajudar o usuário, ele deve fazer uma requisição local diretamente à API do bridge do WhatsApp:

```bash
curl -s http://localhost:3000/whatsapp/debug
```
*Ou usando o nome do serviço docker:*
```bash
curl -s http://whatsapp-bridge:3000/whatsapp/debug
```

Esta requisição retornará um JSON contendo o status detalhado, diagnóstico de credenciais e as últimas 50 linhas de logs de execução do console.

---

### Passo 3 — Apresentar as Instruções e URLs ao Usuário

O agente deve apresentar as informações de monitoramento ao usuário de forma estruturada.

Com base no domínio obtido no **Passo 1** (ex: `https://hermes.seu-dominio.com`):
* **Endpoint de Diagnóstico Completo & Logs**: `{HERMES_SERVER_DOMAIN}/whatsapp/debug`
* **Status da Conexão Simplificado**: `{HERMES_SERVER_DOMAIN}/whatsapp/status`
* **Visualizar QR Code (SVG)**: `{HERMES_SERVER_DOMAIN}/whatsapp/qr?format=svg`
* **Visualizar QR Code (PNG)**: `{HERMES_SERVER_DOMAIN}/whatsapp/qr?format=png`

---

## Logs Físicos no Servidor

Caso o endpoint `/whatsapp/debug` esteja inacessível por queda total do bridge Node.js, os logs brutos persistidos podem ser consultados no servidor pelo terminal usando:

```bash
tail -n 50 /opt/data/.hermes/platforms/whatsapp/bridge.log
```
