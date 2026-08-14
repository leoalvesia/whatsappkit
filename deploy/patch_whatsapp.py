#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Documentação de Patches do Bridge.js - Hermes Agent (Modo Misto WhatsApp)

Este arquivo aplica e documenta as modificações do bridge.js do WhatsApp
para o funcionamento do "Modo Misto Híbrido" (Auto-respostas para clientes
e assistente pessoal para o dono).

As correções incluem:
- bridge ouvindo em 0.0.0.0 para o Traefik conseguir alcançar a porta 3000;
- package.json com "type": "module" para eliminar o warning do Node;
- endpoint /whatsapp/qr e /whatsapp/status mantidos para pareamento sem Telegram.

Este script é executado pelo setup.sh durante a sincronização para manter o
bridge consistente com a stack publicada.

MODIFICAÇÕES DOCUMENTADAS:
==========================

1. BOT STATE PERSISTENCE (botPaused via bot_state.json)
   - Local: /root/.hermes/whatsapp/session/bot_state.json
   - Funções: loadBotState(), saveBotState()
   - Mantém o estado de pausa do bot entre reinicializações

2. ENDPOINT /bot-status
   - GET /bot-status retorna { botPaused, uptime }
   - Usado pelo whatsapp-manager plugin para verificar antes de processar mensagens
   - Permite pausar o bot sem matar o processo

3. stop_bot / start_bot COMMANDS (textLower comparison)
   - Comandos aceitos (case-insensitive): stop_bot, start_bot
   - Aliases em português: !pausar, !parar, !retomar, !iniciar
   - Verificação de owner usa tanto myNumber quanto myLid

4. isOwner CHECK ATUALIZADO
   - Usa both myNumber AND myLid para identificar o dono
   - Comparação: senderClean === myNumber || senderClean === myLid
   - Suporta LID format ( WhatsApp ID)

5. fromMe FILTER PARA OWNER COMMANDS
   - Permite que comandos stop_bot/start_bot funcionem mesmo fora do self-chat
   - Verifica se é um comando de bot antes de pular a mensagem
   - owner pode controlar o bot de qualquer chat

6. SIGNATURE STRIPPER (formatOutgoingMessage)
   - Remove e-mails de mensagens de clientes
   - Remove assinaturas como "Abraços, André", "Atenciosamente, João", etc.
   - Limpa espaços em branco no final

ARQUIVO ORIGINAL:
================
O arquivo original era based em ~201 linhas.
A versão atual tem 862 linhas e inclui todas as patches listadas acima.

Para verificar se sua bridge.js já tem estas patches, procure por:
- "BOT_STATE_FILE" ou "bot_state.json"
- "loadBotState" ou "saveBotState"
- "/bot-status"
- "stop_bot" ou "start_bot"
- "myNumber || myLid" ou "myLid"

Se encontrar estas strings, suas patches já estão aplicadas!
"""

import os
import sys

def main():
    print("=" * 60)
    print("📖 DOCUMENTAÇÃO DE PATCHES DO BRIDGE.JS")
    print("            Hermes Agent - Modo Misto WhatsApp")
    print("=" * 60)

    # Caminhos possíveis do bridge.js
    possible_paths = [
        os.path.expanduser("~/.hermes/platforms/whatsapp/bridge/bridge.js"),
        "/opt/data/.hermes/platforms/whatsapp/bridge/bridge.js",
        "/opt/hermes/scripts/whatsapp-bridge/bridge.js",
        "/root/.hermes/platforms/whatsapp/bridge/bridge.js",
    ]

    found_any = False

    for path in possible_paths:
        if not os.path.exists(path):
            continue

        print(f"\n📂 Encontrado arquivo da ponte em: {path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verificar cada patch
        patches = [
            ("BOT_STATE_FILE ou bot_state.json", "Estado de pausa persistente"),
            ("loadBotState", "Função de carregar estado do bot"),
            ("saveBotState", "Função de salvar estado do bot"),
            ("/bot-status", "Endpoint HTTP para status do bot"),
            ("stop_bot", "Comando para pausar bot"),
            ("start_bot", "Comando para retomar bot"),
            ("myLid", "Verificação de owner com LID"),
            ("failsafe signature stripper", "Remoção de assinaturas"),
        ]

        print("\n📋 Patches detectadas neste arquivo:")
        all_found = True
        for pattern, description in patches:
            if pattern in content:
                print(f"  ✅ {description}")
            else:
                print(f"  ❌ {description} (NÃO ENCONTRADA)")
                all_found = False

        if all_found:
            print("\n✨ Todas as patches do Modo Misto estão aplicadas!")

        found_any = True

    if not found_any:
        print("\n❌ Nenhum arquivo bridge.js foi encontrado.")
        print("   Execute o setup.sh primeiro para baixar os arquivos.")
        return

    print("\n" + "=" * 60)
    print("📝 RESUMO DAS PATCHES:")
    print("=" * 60)
    print("""
1. botPaused STATE PERSISTENCE
   - O estado de pausa do bot é salvo em bot_state.json
   - Suporta reinicializações sem perder o estado

2. /bot-status ENDPOINT
   - GET /bot-status retorna { botPaused, uptime }
   - O plugin whatsapp-manager consulta antes de processar

3. stop_bot / start_bot COMMANDS
   - Comandos: stop_bot, start_bot (case-insensitive)
   - Aliases: !pausar, !parar, !retomar, !iniciar
   - Funciona de qualquer chat para o dono

4. isOwner CHECK COM myNumber E myLid
   - Usa ambos números para identificar o dono
   - Suporta formato LID do WhatsApp

5. fromMe FILTER
   - Permite comandos do dono mesmo fora do self-chat
   - Verifica se é comando de bot antes de continuar

6. SIGNATURE STRIPPER
   - Remove e-mails e assinaturas como "Abraços, André"
   - Mantém as mensagens mais limpas
""")

if __name__ == "__main__":
    main()