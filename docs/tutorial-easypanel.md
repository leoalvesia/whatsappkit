# Como instalar o Hermes WhatsApp no Easypanel (do zero ao bot funcionando)

> **Nível:** iniciante · **Tempo estimado:** 20–30 minutos  
> **O que você vai ter no final:** um assistente pessoal no WhatsApp que atende clientes, transcreve áudios, aprende o seu estilo e obedece instruções por contato.

---

## O que é o Hermes WhatsApp?

O **Hermes** é um agente de IA que vive no seu servidor e conecta ao seu WhatsApp. Ele funciona em dois modos ao mesmo tempo:

- **Assistente pessoal** — quando você manda mensagem para si mesmo, ele busca histórico de conversas, atualiza contatos e responde como um assistente
- **Atendente autônomo** — para seus clientes e contatos, ele atende com base nas suas regras, tom personalizado por contato e transcrição automática de áudios

O plugin `whatsapp-manager` roda dentro do [Hermes Agent](https://github.com/nousresearch/hermes) e é instalado em menos de 30 minutos no Easypanel.

---

## Pré-requisitos

Antes de começar, você precisa ter:

- **Easypanel** instalado em um VPS (Ubuntu 22.04+ recomendado, mínimo 2GB RAM)
- **Domínio** com DNS apontado para o seu servidor
- **Chave da Google AI Studio** — [crie aqui gratuitamente](https://aistudio.google.com) (usada pelo Gemini, que é o modelo padrão)
- **Token GitHub (PAT)** com leitura a um repositório privado onde ficam seus contatos e persona
- **Número do WhatsApp** que será conectado ao bot

---

## Passo 1 — Criar o serviço no Easypanel

No Easypanel, acesse seu projeto e clique em **+ Serviço → Compose**.

Cole o conteúdo do arquivo [`deploy/docker-compose.easypanel.yml`](../deploy/docker-compose.easypanel.yml) do repositório.

> Dica: acesse o arquivo no GitHub, clique em **Raw** e copie tudo.

---

## Passo 2 — Configurar as variáveis de ambiente

Na aba **Ambiente**, adicione as variáveis abaixo.

> ⚠️ **ATENÇÃO CRÍTICA:** antes de salvar, marque a opção **"Criar arquivo .env"**. Sem isso o container ignora todas as variáveis e falha ao iniciar. É o erro mais comum na instalação pelo Easypanel.

### Variáveis obrigatórias

| Variável | Valor | Como obter |
|---|---|---|
| `API_SERVER_KEY` | Chave secreta aleatória | `openssl rand -hex 32` no terminal |
| `GOOGLE_API_KEY` | Chave do Gemini | [aistudio.google.com](https://aistudio.google.com) → Get API Key |
| `WHATSAPP_OWNER_NUMBER` | Seu número sem `+` | Ex: `5511999999999` |
| `WHATSAPP_OWNER_NAME` | Seu nome | Ex: `André` |
| `CONFIG_GITHUB_TOKEN` | PAT do GitHub | GitHub → Settings → Developer settings → Personal access tokens |
| `WHATSAPP_ENABLED` | `false` | **Deixe `false` agora** — vamos mudar depois de parear |

### Variáveis opcionais úteis

| Variável | Valor padrão | Descrição |
|---|---|---|
| `WHATSAPP_CONNECTION_NAME` | `EmpreendedorSerial` | Nome exibido no Dashboard |
| `TZ` | `America/Sao_Paulo` | Fuso horário |
| `MAX_TURNS` | `8` | Máximo de passos por resposta (controla custo) |

---

## Passo 3 — Configurar os domínios

Na aba **Domains & Proxy**, adicione dois domínios apontando para o serviço `hermes`:

| Porta | Domínio sugerido | Função |
|---|---|---|
| `9119` | `hermes.seu-dominio.com` | Dashboard + WebSocket + QR do WhatsApp |
| `8642` | `hermes-api.seu-dominio.com` | API REST |

---

## Passo 4 — Primeiro deploy

Clique em **Implantar**. O Easypanel vai baixar a imagem e subir o container.

Aguarde o container ficar verde. Nos logs você deve ver algo como:

```
hermes-1 | ⚕ Hermes Gateway Starting...
hermes-1 | WARNING: WhatsApp is enabled but not paired
```

O warning é esperado — ainda não pareamos o WhatsApp.

---

## Passo 5 — Rodar o setup inicial

Abra o **Console** do serviço `hermes` no Easypanel e execute:

```bash
curl -sSL https://raw.githubusercontent.com/empreendedorserial/hermes-whatsapp-mixed/main/deploy/setup.sh | bash -s empreendedorserial
```

O script vai:
- Clonar o workspace com o plugin
- Baixar os arquivos de persona e regras de suporte
- Instalar as dependências do Node.js para a bridge WhatsApp
- Copiar o plugin para o caminho ativo do Hermes

Aguarde terminar. Você verá `✓` em cada etapa concluída.

---

## Passo 6 — Instalar o plugin pelo Dashboard

Acesse `https://hermes.seu-dominio.com` → **Plugins** → localize `whatsapp-manager` → clique em **Instalar**.

---

## Passo 7 — Parear o WhatsApp

Este é o único passo que exige interação manual no terminal.

No **Console** do serviço `hermes`, execute:

```bash
hermes whatsapp
```

Um QR Code vai aparecer no terminal. Abra o WhatsApp no celular:

**WhatsApp → ⋮ → Aparelhos Conectados → Conectar um aparelho**

Escaneie o QR. Quando aparecer `✓ Connected`, o pareamento está feito. Pressione `Ctrl+C` para sair.

---

## Passo 8 — Ativar o WhatsApp e reiniciar

Agora que o pareamento foi feito, ative o WhatsApp definitivamente:

1. Vá em **Ambiente**
2. Mude `WHATSAPP_ENABLED` de `false` para `true`
3. Clique em **Implantar**

Aguarde o container reiniciar. Nos logs você deve ver:

```
hermes-1 | ✓ whatsapp connected
```

O bot está ativo. 🎉

---

## Passo 9 — Verificar se está funcionando

Mande uma mensagem para **você mesmo** no WhatsApp (a conversa com o seu próprio número).

Digite:

```
ajuda
```

O bot deve responder listando todos os comandos disponíveis. Se respondeu, a instalação está completa.

---

## URL do QR Code (para reconexões futuras)

Após o primeiro pareamento, se a conexão cair, você pode reparear pela URL — sem precisar acessar o console:

| URL | Descrição |
|---|---|
| `https://hermes.seu-dominio.com/whatsapp/qr` | QR interativo no navegador |
| `https://hermes.seu-dominio.com/whatsapp/qr?format=png` | Imagem PNG do QR |
| `https://hermes.seu-dominio.com/whatsapp/status` | Status JSON da conexão |

> ⚠️ Essa URL **não funciona** no primeiro pareamento — só após a sessão já ter sido criada pelo menos uma vez.

---

## Comandos disponíveis no WhatsApp

Envie para **você mesmo** (self-chat). Todos os comandos funcionam exclusivamente para o dono.

| Comando | Ação |
|---|---|
| `stop_bot` | Pausa o atendimento a clientes |
| `start_bot` | Reativa o atendimento |
| `sincronizar contatos` | Sincroniza contatos e persona do GitHub |
| `ajuda` ou `help` | Lista todos os comandos |
| *"quais comandos posso usar?"* | Mesmo que acima (linguagem natural) |

---

## Atualizar o plugin após mudanças

Quando houver uma nova versão do plugin, atualize assim no console do container:

```bash
cd /opt/data/workspace/hermes-whatsapp-mixed && git pull origin main
cp whatsapp_manager.py /opt/data/.hermes/plugins/whatsapp-manager/whatsapp_manager.py
```

Depois reinicie o container pelo Easypanel.

---

## Problemas comuns

**Container não sobe e as variáveis parecem ignoradas**
→ Você esqueceu de marcar **"Criar arquivo .env"** na aba Ambiente. Marque, salve e reimplante.

**`WhatsApp is enabled but not paired` e o container cai**
→ Defina `WHATSAPP_ENABLED=false`, reimplante, rode `hermes whatsapp` no console, pareie, volte para `true` e reimplante.

**`git: dubious ownership`**
→ Não se preocupe — o compose já corrige isso automaticamente no startup do container.

**`Cannot find package '@whiskeysockets/baileys'`**
→ O setup.sh não foi executado ainda, ou falhou. Rode o comando do Passo 5 novamente.

**O bot não responde a clientes mas responde ao dono**
→ O atendimento pode estar pausado. Envie `start_bot` para você mesmo.

---

## Estrutura dos arquivos de configuração

Após o setup, seus arquivos ficam em `/opt/data/` (volume persistido):

| Arquivo | Função |
|---|---|
| `personal_contacts.json` | Perfis, resumos e instruções por contato |
| `support_rules.md` | Produtos, preços e FAQs para atendimento a clientes |
| `SOUL_WHATSAPP.md` | Persona, estilo de escrita e exemplos de conversa |

Edite diretamente no GitHub (no seu repositório privado de configuração) e rode `sincronizar contatos` no WhatsApp para aplicar as mudanças.

---

*Desenvolvido por [André Alencar](https://aalencar.com.br) — [Repositório no GitHub](https://github.com/empreendedorserial/hermes-whatsapp-mixed)*
