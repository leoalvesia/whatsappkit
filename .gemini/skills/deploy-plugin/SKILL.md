---
name: deploy-plugin
description: "Realiza o deploy do plugin whatsapp-manager no servidor Hermes — commit, push, pull e restart do container."
category: deploy
---

# Deploy do Plugin WhatsApp Manager

Esta skill guia o processo completo de deploy de alterações no plugin `whatsapp-manager` para o servidor Hermes em produção.

---

## Quando usar esta skill

Use quando o usuário disser algo como:
- "faz o deploy"
- "publica as alterações"
- "sobe pro servidor"
- "atualiza o plugin"
- "deploy do whatsapp"
- "deploy do plugin"
- "manda pro hermes"

---

## Pré-requisitos

- O repositório local está no workspace ativo
- O remote `origin` aponta para o repositório no GitHub
- O servidor Hermes tem o plugin clonado em `/opt/data/.hermes/plugins/whatsapp-manager`
- Acesso ao Dashboard do Hermes e ao Portainer do servidor

---

## Etapa 1 — Commit e Push no GitHub

### 1.1 Verificar o que mudou

```bash
git status
```

Revisar as alterações e confirmar com o usuário se está tudo certo.

### 1.2 Adicionar e commitar

```bash
git add -A && git commit -m "MENSAGEM_DO_COMMIT"
```

> **Regra:** A mensagem de commit deve ser descritiva e em português. Exemplos:
> - `fix: bot continuava respondendo após stop_bot`
> - `feat: adiciona delay na primeira resposta ao cliente`
> - `chore: atualiza SOUL_WHATSAPP.md com novas regras`

### 1.3 Push para o GitHub

```bash
git push origin main
```

Se der erro de divergência, usar `git pull --rebase origin main` antes do push.

---

## Etapa 2 — Git Pull no Dashboard do Hermes

O plugin é atualizado diretamente pelo painel do Hermes, na aba de Plugins.

### 2.1 Acessar o Dashboard do Hermes

1. Acesse o Dashboard do Hermes
2. Navegue até a aba **Plugins**

### 2.2 Atualizar o plugin

1. Localize o plugin `whatsapp-manager` na lista
2. Clique no botão de **Pull** / **Atualizar** do plugin
3. Aguarde a confirmação de que o pull foi concluído

> **Verificar:** Confirme que a mensagem de sucesso aparece. Se aparecer `Already up to date`, o push da Etapa 1 pode não ter sido concluído.

---

## Etapa 3 — Restart do Container

As alterações no plugin só são carregadas quando o Hermes reinicia.

### Opção A — Pelo Portainer (Recomendado)

1. Acesse o Portainer do servidor
2. Vá em **Containers** → selecione o container do Hermes
3. Clique em **Restart**
4. Aguarde o container subir (status `running`)

### Opção B — Pelo Portainer Stack

1. Vá em **Stacks** → selecione a stack do Hermes
2. Clique em **Update the stack** → **Update**

### Opção C — Via CLI (se tiver acesso SSH ao host)

```bash
docker restart hermes
```

---

## Verificação Pós-Deploy

### Conferir se o container subiu

No Portainer → Containers → verificar que o status é `running` e que o uptime é recente (poucos segundos/minutos).

### Conferir logs do plugin

No terminal do container (via Console do Portainer):

```bash
grep "whatsapp-manager" /opt/data/.hermes/logs/hermes.log | tail -20
```

Procurar por:
- `✓ bridge.js atualizado` — confirma que o bridge foi copiado
- `✓ Skills registradas` — confirma que as skills carregaram
- Ausência de erros `⚠️` ou `❌`

### Testar o bot

Envie `start_bot` ou `stop_bot` no WhatsApp para confirmar que o bridge está respondendo.

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| `git pull` dá conflito no container | `cd /opt/data/.hermes/plugins/whatsapp-manager && git reset --hard origin/main` |
| Container não sobe após restart | Verificar logs no Portainer → Containers → Logs |
| Plugin não carrega as alterações | Conferir se o `git pull` trouxe os arquivos e se o container foi reiniciado |
| `bridge.js` não atualiza no bridge | O `register()` do plugin copia automaticamente no boot — verificar logs por `bridge.js atualizado` |
| Push rejeitado por divergência | `git pull --rebase origin main && git push origin main` |

---

## Notas Importantes

- O **branch principal** é `main`
- O plugin é carregado automaticamente pelo Hermes no boot via `register()` em `__init__.py`
- O `bridge.js` é copiado automaticamente do plugin para `/opt/data/.hermes/platforms/whatsapp/bridge/` durante o `register()`
- Arquivos como `SOUL_WHATSAPP.md`, `support_rules.md` e `SOUL_EMAIL.md` são baixados automaticamente na primeira inicialização se não existirem no volume
- O `bot_state.json` (estado de pause do bot) é persistido e **não é afetado** pelo restart
