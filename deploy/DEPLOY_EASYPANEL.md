# Deploy no EasyPanel — passo a passo

Guia para subir uma instância deste kit para um cliente. Use `deploy/docker-compose.easypanel.yml`
(o `docker-compose.yml` é a variante Portainer/Swarm e exige Traefik + volume externo).

---

## Antes de tocar no painel

### 1. Preencher as personas

`deploy/SOUL.md`, `deploy/SOUL_WHATSAPP.md`, `deploy/SOUL_EMAIL.md` e `deploy/support_rules.md`
são **templates com placeholders `{{...}}`**. Preencha e faça push antes de implantar.

```bash
grep -rn '{{' deploy/SOUL*.md deploy/support_rules.md   # nao deve sobrar nada
```

Placeholder não substituído vai **literal** para o cliente no WhatsApp. E um
`support_rules.md` com produto errado é pior que vazio: o bot passa a afirmar preço e
oferta que não existem.

### 2. Ter em mãos

| Item | Onde conseguir |
|---|---|
| `OPENROUTER_API_KEY` | https://openrouter.ai/keys |
| `API_SERVER_KEY` | `openssl rand -hex 32` |
| Número do dono | Formato internacional sem `+` (ex: `5511999999999`) |
| Celular do dono | Necessário no pareamento — não dá para automatizar |

---

## Criar o serviço

1. EasyPanel → **New Service** → **Compose**.
2. Cole o conteúdo de `deploy/docker-compose.easypanel.yml`.
3. Aba **Ambiente** → marque **"Criar arquivo .env"**.
   **Sem isso o container ignora todas as variáveis e falha ao iniciar.**
4. Preencha as variáveis abaixo.

### Variáveis mínimas

```env
API_SERVER_KEY=<openssl rand -hex 32>
OPENROUTER_API_KEY=sk-or-...
WHATSAPP_OWNER_NUMBER=5511999999999
WHATSAPP_OWNER_NAME=Nome do Dono
WHATSAPP_PIX_KEY=chave@pix.com.br
WHATSAPP_ENABLED=false
HERMES_SERVER_DOMAIN=https://dominio-do-cliente.com
```

> ⚠️ **Deixe `GOOGLE_API_KEY` e `OPENAI_API_KEY` vazias.** O plugin tenta os providers na
> ordem Google → OpenAI → OpenRouter e **para na primeira chave preenchida**. Qualquer
> valor nelas faz o OpenRouter nunca ser alcançado, e a conta vai para o provider errado.

`WHATSAPP_ENABLED=false` é proposital nesta etapa — veja o pareamento abaixo.

### Modelos (já vêm como default, só mexa se quiser trocar)

```env
WHATSAPP_OWNER_MODEL=deepseek/deepseek-v4-flash
WHATSAPP_CLIENT_MODEL=deepseek/deepseek-v4-flash
WHATSAPP_CONTACT_CLASSIFIER_MODEL=deepseek/deepseek-v4-flash
WHATSAPP_CLIENT_MEDIA_MODEL=google/gemini-3.1-flash-lite
WHATSAPP_OWNER_PROVIDER=openrouter
WHATSAPP_CLIENT_PROVIDER=openrouter
```

O modelo de mídia **precisa ser multimodal**. DeepSeek aceita apenas texto — colocá-lo
em `WHATSAPP_CLIENT_MEDIA_MODEL` quebra transcrição de áudio e leitura de imagem.

### Opcional — versionar contatos no GitHub

```env
CONFIG_REPO=nome-do-repo-privado
CONFIG_GITHUB_TOKEN=ghp_...
```

Sem os dois o bot funciona normalmente; só não há backup nem histórico dos contatos.

---

## Domínios

Aba **Domains & Proxy**:

| Porta | Serve |
|---|---|
| 9119 | Dashboard, WebSocket, e também `/whatsapp/qr` e `/whatsapp/status` |
| 8642 | API REST |

**Ative "Password Protection" no domínio da porta 9119.** O Dashboard expõe terminal,
logs e todas as conversas.

---

## Parear o WhatsApp (primeira vez)

A URL `/whatsapp/qr` serve para **reconexão**, não para o primeiro pareamento.

1. Implante com `WHATSAPP_ENABLED=false` (mantém o container estável).
2. Abra o **Console** do serviço e rode:
   ```bash
   hermes whatsapp
   ```
3. No celular: **WhatsApp → Aparelhos Conectados → Conectar um aparelho** → escaneie o
   QR que apareceu no terminal.
4. Mude `WHATSAPP_ENABLED=true` → **Implantar** de novo.

A partir daí `https://dominio/whatsapp/qr` funciona para reconexões futuras.

---

## Conferir se subiu

```bash
# 1. O plugin foi clonado?
ls /opt/data/.hermes/plugins/whatsapp-manager/whatsapp_manager.py

# 2. O perfil de isolamento dos clientes existe? (toolsets deve estar vazio)
cat /opt/data/.hermes/profiles/whatsapp/config.yaml

# 3. Bridge respondendo?
curl -s http://127.0.0.1:3000/whatsapp/status

# 4. Log do plugin
grep "whatsapp-manager" /opt/data/.hermes/logs/hermes.log | tail -20
```

No log procure por `[setup] plugin clonado` ou `[setup] plugin atualizado`, e por
`bridge.js atualizado`. Ausência de `⚠️` e `❌`.

### Teste funcional

1. Mande `quais comandos` para si mesmo no WhatsApp → deve responder com o menu.
2. Mande `stop_bot` e depois `start_bot` → confirma que o bridge processa comandos.
3. Peça para alguém mandar mensagem → deve responder com a persona de cliente.
4. **Mande um áudio** → veja o item de risco conhecido abaixo.

---

## Atualizar depois

```bash
git push origin main      # na sua maquina
```

Depois: **Restart do serviço no EasyPanel**. O `command:` faz `fetch` + `reset --hard`
na `main` a cada boot. Como é clone de verdade, arquivos novos também chegam.

Não é necessário rodar `setup.sh` — ele existe para instalação manual, fora deste fluxo.

---

## Riscos conhecidos

**Transcrição de áudio via OpenRouter não foi validada em produção.** O PTT do WhatsApp é
OGG/Opus e a documentação do OpenRouter cita `wav`/`mp3` para `input_audio`. O código
tenta `input_audio` e, se falhar, refaz a chamada com data URI. Se a transcrição não
funcionar, o log mostra:

```
[media] OpenRouter falhou (tentativa 1/2): ...
[media] OpenRouter falhou (tentativa 2/2): ...
```

Nesse caso, a saída é converter o áudio para `mp3` antes de enviar, ou usar
`GOOGLE_API_KEY` só para mídia — mas atenção: preencher `GOOGLE_API_KEY` faz o Gemini
vencer a cadeia **para tudo**, não só para áudio.

**Um teste falha por motivo desconhecido:** `test_find_product_matches_partial_keyword`.
É totalmente mockado, sem dependência de path ou rede. Afeta o casamento parcial de nome
de produto ("mini pc" quando o catálogo diz "Mini Pc Acemagic Ryzen 7"). Vale confirmar
no ambiente Linux antes de confiar no registro automático de vendas.
