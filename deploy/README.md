# 🤖 Hermes Agent - Modo Misto Híbrido (WhatsApp + Gmail)

Este repositório contém os arquivos de configuração, templates e scripts necessários para implantar o **Hermes Agent** em modo híbrido (Dual-Mode) via **Portainer** ou **Easypanel**. 

Esse modo permite que seu agente desempenhe duas funções ao mesmo tempo:
1. **Assistente Pessoal do Dono:** Quando você fala com o robô no chat privado (ou envia mensagens para si mesmo no WhatsApp/Telegram), ele age como seu assistente técnico e de infraestrutura com permissões para rodar comandos do terminal.
2. **Chatbot Comercial de Suporte:** Quando clientes ou outras pessoas entram em contato por **WhatsApp, Telegram ou e-mail (Gmail)**, ele atua como o atendente comercial dos seus produtos, consultando suas regras de negócio e sem parecer um robô chato.
3. **Controle por Comandos:** Você pode pausar ou retomar o atendimento a clientes enviando `stop_bot` ou `start_bot` na sua conversa privada!

---

## 📂 O que está incluído neste repositório:
* 🐋 **`docker-compose.yml`**: Arquivo de produção otimizado para Portainer Stack (Single-Container `nousresearch/hermes-agent`), pré-configurado com suporte ao **Traefik** e rotas WebSockets seguras.
* 🟣 **`docker-compose.easypanel.yml`**: Arquivo adaptado para implantação no Easypanel (Single-Container — SSL e proxy gerenciados automaticamente).
* ⚡ **`setup.sh`**: Script de configuração e sincronização de 1 clique que vincula seu servidor ao seu repositório pessoal no GitHub.
* 🐍 **`patch_whatsapp.py`**: Script de automação universal que reconfigura a ponte do WhatsApp (filtro de assinaturas inteligente e novos comandos).
* 🔄 **Sincronização automática no deploy**: a stack executa o `setup.sh` ao subir o container principal, mantendo as personas, regras e configurações sincronizadas com o GitHub. Os plugins são gerenciados pelo dashboard do Hermes.
* ⚙️ **`config.yaml.example`**: Configuração pré-otimizada para alta performance, ativação de memória persistente e prevenção de spam em grupos de WhatsApp.
* 🔑 **`.env.example`**: Modelo de exemplo para as variáveis de ambiente necessárias (ignorado por segurança pelo `.gitignore` para evitar vazamentos).
* 👤 **`SOUL.md`**: Persona pré-configurada para o funcionamento do Modo Duplo (Dono vs Clientes).
* 👤 **`SOUL_WHATSAPP.md`**: Persona específica e otimizada para o WhatsApp de Clientes (diálogos amigáveis, saudações curtas, regras de abordagem humana).
* 👤 **`SOUL_EMAIL.md`**: Persona específica e estruturada para Suporte por E-mail (tom formal, com quebra de parágrafos e assinatura oficial).
* 📖 **`support_rules.md`**: Modelo estruturado de base de conhecimento com as diretrizes e FAQs do seu negócio.

---

## 🚀 Como Implantar pelo Portainer (Passo a Passo)

### Passo 1: Fazer um Fork deste Repositório e Personalizar 🎨

Em vez de editar arquivos complexos no terminal do seu servidor, você vai usar o próprio **GitHub como seu gerenciador visual (CMS)**!

1. Na parte superior desta página, clique no botão **Fork** para criar uma cópia deste repositório na sua própria conta do GitHub (ex: `github.com/SEU_USUARIO_GITHUB/hermes-whatsapp-mixed`).
2. Dentro do seu repositório pessoal recém-criado, edite os arquivos diretamente pelo seu navegador:
   * **`support_rules.md`**: Preencha o documento com as informações do seu negócio, preços, links de checkout (Kiwify, Hotmart, etc.) e formas de suporte. Clique em **Commit changes** para salvar.
   * **`SOUL_WHATSAPP.md`**: Ajuste os exemplos práticos de saudação ou personalize a abordagem humana do suporte de WhatsApp. Salve.
   * **`SOUL_EMAIL.md`**: Mude a assinatura padrão de e-mail ou ajuste as regrinhas formais de atendimento. Salve.
3. Pronto! Seus arquivos de persona e regras de negócio agora estão guardados com segurança e com histórico no seu próprio GitHub.

---

### Passo 2: Criar a Stack e Definir as Credenciais no Portainer

Toda a infraestrutura de rede, domínios SSL e chaves de API é gerenciada de forma visual na interface gráfica do Portainer:

1. Acesse seu painel do **Portainer** -> **Stacks** -> **Add stack**.
2. Dê um nome à stack (ex: `hermes-agent`).
3. No campo **Web editor**, cole o conteúdo do arquivo `docker-compose.yml` deste repositório.
4. Em **Environment variables** (Variáveis de ambiente) na interface do Portainer, configure os seus domínios e chaves:
   * **`HERMES_DASH_HOST`**: O domínio do seu painel visual (ex: `hermes.seu-dominio.com`).
   * **`HERMES_API_HOST`**: O subdomínio para a API (ex: `hermes-api.seu-dominio.com`).
   * **`GOOGLE_API_KEY`**: Sua chave da API do Gemini (usada para pensar).
   * **`API_SERVER_KEY`**: Uma senha secreta para proteger a API do seu robô.
   * **`WHATSAPP_FIRST_RESPONSE_DELAY_S`**: (Opcional) Tempo de delay humano em segundos para a primeiríssima resposta do bot ao cliente. Padrão: `30` (30 segundos). Defina como `0` para desativar.
5. Clique em **Deploy the stack** para criar seu container.

> 🔒 **Traefik Integrado:** O arquivo `docker-compose.yml` já possui todas as `labels` de produção do Traefik mapeadas. Ele cuida da geração e renovação de certificados SSL da Let's Encrypt de forma 100% nativa e automática!

---

### Passo 3: Sincronização e Instalação de 1 Clique ⚡

Agora, vamos fazer com que o seu servidor baixe automaticamente os arquivos que você personalizou no seu repositório pessoal do GitHub:

> **QR do WhatsApp sem Telegram:** o container único do Hermes executa a ponte internamente (`127.0.0.1:3000`) e o QR fica acessível no próprio domínio do dashboard em `https://SEU-DOMINIO/whatsapp/qr` e `https://SEU-DOMINIO/whatsapp/status`.
> O QR também pode ser retornado como `?format=png` ou `?format=svg`.
> Após subir o container, aguarde alguns segundos para a ponte interna inicializar antes de abrir a URL.

1. No Portainer, clique em **Containers** e clique no ícone de **Console** (`>_`) do container `hermes-agent`.
2. Clique em **Connect** para abrir o terminal integrado.
3. Substitua `SEU_USUARIO_GITHUB` pelo seu usuário real do GitHub no comando abaixo, cole-o no console e aperte Enter:

```bash
curl -sSL https://raw.githubusercontent.com/SEU_USUARIO_GITHUB/hermes-whatsapp-mixed/main/deploy/setup.sh | bash -s SEU_USUARIO_GITHUB
```

> **O que o script fez por você?** Ele baixou a persona global (`SOUL.md`), as personas isoladas (`SOUL_WHATSAPP.md` e `SOUL_EMAIL.md`), a base de conhecimento (`support_rules.md`) diretamente do seu GitHub Fork pessoal, configurou as otimizações no `config.yaml` e aplicou a inteligência do WhatsApp. Os plugins ficam para o dashboard do Hermes.

💡 **Dica de Sincronização:** Toda vez que você quiser alterar as regras do seu negócio ou atualizar sua persona, basta editá-las no seu GitHub e rodar este mesmo comando de novo. Seu servidor atualizará tudo em segundos!

#### 🔒 Opção A: Sincronização de Contatos Pessoais e Personas via Repositório Privado (Seguro)

Para manter seus contatos pessoais (`personal_contacts.json`) ou suas personas totalmente privados (sem expor em repositórios públicos):
1. Crie um repositório **privado** no GitHub (ex: `hermes-config-privado`).
2. Adicione nele o arquivo `personal_contacts.json` (veja o formato em [personal_contacts.json.example](file:///Users/andrealencar/GoogleAntigravity/hermes-whatsapp-mixed/deploy/personal_contacts.json.example)). Você também pode mover seus arquivos `.md` (personas/regras) para lá se quiser mantê-los privados.
3. Crie um **Personal Access Token (PAT)** no GitHub com permissão de leitura de repositório (`repo`).
4. Configure as chaves diferenciadas:
   * **Na Stack do Portainer (Cliente):**
     * `CLIENT_GITHUB_USER` = Usuário do GitHub do cliente (dono do WhatsApp).
     * `CLIENT_CONFIG_REPO` = Nome do repositório privado de configurações (ex: `usuario-cliente/hermes-config-privado`).
     * `CLIENT_CONFIG_GITHUB_TOKEN` = PAT Token do cliente para acessar seu repositório privado de configs.
   * **No arquivo `.env` local em `/opt/data/.env` ou `/opt/data/.hermes/.env` (Desenvolvedor):**
     * `DEV_GITHUB_USER` = Usuário do repositório de código base do Hermes.
     * `DEV_GITHUB_TOKEN` = Token do desenvolvedor (caso o repositório de código base seja privado).
5. Execute o setup no console do container:
   ```bash
   curl -sSL https://raw.githubusercontent.com/SEU_USUARIO_GITHUB/hermes-whatsapp-mixed/main/deploy/setup.sh | bash -s SEU_USUARIO_GITHUB
   ```



---

### Passo Extra: Ajustes Rápidos pela Web UI (Dashboard do Hermes) 🎨

Se você precisar fazer um ajuste rápido de última hora (mudar um preço, corrigir uma palavra na sua Persona) e não quiser usar o GitHub naquele momento, você pode editar tudo de forma visual:

1. Acesse o painel visual do Hermes direto no seu navegador:
   👉 `https://hermes.seu-dominio.com` *(Graças ao Traefik, já com HTTPS/SSL ativo!)*
2. No menu lateral, acesse o **gerenciador de arquivos visual** integrado.
3. Você pode clicar para abrir e **editar diretamente pela interface Web** os arquivos:
   * 📄 **`support_rules.md`** (Regras de Suporte e FAQ).
   * 📄 **`SOUL_WHATSAPP.md`** (Persona específica do WhatsApp).
   * 📄 **`SOUL_EMAIL.md`** (Persona específica do E-mail).
4. Basta clicar em **Salvar** e o Hermes assumirá as alterações no mesmo instante!

*⚠️ Nota: Lembre-se de que se você rodar o setup.sh novamente com o parâmetro do seu GitHub, ele baixará as versões do seu repositório. Por isso, para alterações definitivas, o recomendado é atualizar sempre o seu GitHub Fork!*

---

## 🟣 Como Implantar pelo Easypanel (Passo a Passo)

> O Easypanel gerencia automaticamente o proxy reverso (Traefik), SSL via Let's Encrypt e os volumes — sem configurações manuais de rede.

### Passo 1: Criar o Projeto no Easypanel

1. Acesse o painel do seu **Easypanel**.
2. Clique em **+ Create Project**.
3. Dê um nome ao projeto (ex: `hermes`).
4. Clique em **Create**.

---

### Passo 2: Criar o Serviço Compose

1. Dentro do projeto, clique em **+ Create Service**.
2. Selecione o tipo **Compose**.
3. Dê o nome `hermes` ao serviço.
4. No campo de conteúdo, cole o conteúdo do arquivo **`docker-compose.easypanel.yml`** deste repositório.
5. Clique em **Save** para salvar a configuração.

---

### Passo 3: Configurar as Variáveis de Ambiente

1. Na tela do serviço, clique na aba **Environment**.
2. Cole o conteúdo abaixo e preencha os valores:

```env
# OBRIGATÓRIA
API_SERVER_KEY=sua_chave_secreta_aqui

# Provedores de IA (pelo menos uma com sua chave)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
OPENROUTER_API_KEY=
AISA_API_KEY=

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=
GATEWAY_ALLOW_ALL_USERS=false

# WhatsApp
WHATSAPP_ENABLED=false
WHATSAPP_OWNER_NUMBER=
WHATSAPP_MODE=bot
WHATSAPP_ALLOWED_USERS=*
# Delay em segundos para a primeira resposta do bot ao cliente
WHATSAPP_FIRST_RESPONSE_DELAY_S=30

# Google OAuth (opcional para Gmail)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Configurações gerais
TZ=America/Sao_Paulo
HERMES_API_TIMEOUT=1800
HERMES_API_CALL_STALE_TIMEOUT=300
API_SERVER_CORS_ORIGINS=*
```

3. Clique em **Save**.

---

### Passo 4: Configurar os Subdomínios (Domains & Proxy)

O Hermes expõe **duas portas** que precisam de subdomínios separados:

| Porta | Finalidade | Subdomínio sugerido |
|---|---|---|
| `9119` | Dashboard Web + WebSocket (PTY, eventos) | `hermes.seu-dominio.com` |
| `8642` | API REST (integrações externas) | `hermes-api.seu-dominio.com` |

> ⚠️ **Antes de adicionar os domínios**, certifique-se de que o DNS de ambos os subdomínios já aponta para o IP do seu servidor. O Easypanel gera o SSL automaticamente via Let's Encrypt assim que o domínio resolver corretamente.

**Para configurar o domínio do Dashboard (principal):**

1. Na tela do serviço, clique na aba **Domains**.
2. Clique em **+ Add Domain**:
   - **Domain:** `hermes.seu-dominio.com`
   - **Port:** `9119`
   - Marque como **Primary Domain** (clique na estrela ⭐)
3. Clique em **Save**.

**Para configurar o domínio da API:**

1. Clique em **+ Add Domain novamente**:
   - **Domain:** `hermes-api.seu-dominio.com`
   - **Port:** `8642`
2. Clique em **Save**.

> 💡 O Easypanel suporta WebSocket nativamente — os caminhos `/api/ws`, `/api/events` e `/api/pty` funcionarão automaticamente no domínio do Dashboard sem configuração adicional.

---

### Passo 5: Fazer o Deploy

1. Clique em **Deploy** para iniciar o container.
2. Aguarde o status ficar verde (**Running**).
3. Acesse `https://hermes.seu-dominio.com` para verificar o Dashboard.

---

### Passo 6: Setup Inicial de 1 Clique ⚡

1. Na tela do serviço, clique na aba **Console**.
2. Clique em **Connect** para abrir o terminal integrado.
3. Cole o comando abaixo e pressione Enter (substitua `SEU_USUARIO_GITHUB` pelo seu usuário):

```bash
curl -sSL https://raw.githubusercontent.com/SEU_USUARIO_GITHUB/hermes-whatsapp-mixed/main/deploy/setup.sh | bash -s SEU_USUARIO_GITHUB
```

> 🔒 **Dica de Sincronização Privada (Opção A):** Caso queira utilizar um repositório privado para contatos e personas (para mantê-los seguros), passe o seu token do GitHub e o repositório como argumentos adicionais:
> ```bash
> curl -sSL https://raw.githubusercontent.com/SEU_USUARIO_GITHUB/hermes-whatsapp-mixed/main/deploy/setup.sh | bash -s SEU_USUARIO_GITHUB <SEU_TOKEN_PAT_GITHUB> <SEU_USUARIO_GITHUB/NOME_DO_REPO_PRIVADO>
> ```

**O setup irá:**
* Configurar a persona (`SOUL.md`) em `/opt/data/SOUL.md`
* Configurar as personas isoladas (`SOUL_WHATSAPP.md` e `SOUL_EMAIL.md`) em `/opt/data/`
* Criar as regras de suporte (`support_rules.md`) em `/opt/data/support_rules.md`
* Criar o `config.yaml` em `/opt/data/.hermes/config.yaml`
* Criar o `.env` em `/opt/data/.hermes/.env`
* Deixar o plugin `whatsapp-manager` ser instalado/atualizado pelo dashboard do Hermes
* Aplicar o patch do WhatsApp

> Todos os arquivos são salvos em volumes persistentes — sobrevivem a restarts e atualizações de imagem.

---

### Passo 6.5: Instalação do Provedor AISA (AISA CLI) 🤖

Para utilizar o provedor de IA AISA (aisa.one), você pode solicitar diretamente ao Hermes que instale a CLI. Envie o prompt abaixo no chat do Dashboard, Telegram ou WhatsApp (conversa privada com o dono):

---

```
Hermes, preciso que você instale a AISA CLI no container.
Siga os passos abaixo usando suas ferramentas de terminal:

A chave de API já está configurada e disponível nas variáveis de ambiente do container (variável `AISA_API_KEY` vinda da stack do Portainer / Easypanel).

1. Instale a AISA CLI utilizando um prefixo persistente em `/opt/data/.local` para evitar erros de permissão ao tentar instalar globalmente:
   npm install -g @aisa-one/cli --prefix /opt/data/.local

2. Configure o PATH para incluir o diretório de binários local (`/opt/data/.local/bin`) tanto na sessão atual quanto garantindo sua persistência no ambiente.

3. Valide se a instalação funcionou executando os seguintes comandos e me retorne o output:
   aisa --version
   aisa whoami
```

---

### Como Usar a AISA CLI 🛠️

Para usar as APIs da AIsa no container, garanta que o `/opt/data/.local/bin` está no seu `PATH` e utilize os comandos principais:

- **Buscas gerais:** `aisa web-search --type smart "termo"`
- **Buscas no YouTube:** `aisa web-search --type youtube "termo"`
- **Consultas de criptomoedas:** `aisa crypto BTC`
- **Gerenciamento de Skills:**
  - Listar skills: `aisa skills list`
  - Instalar uma skill: `aisa skills install <skill>`
  - Exibir detalhes de uma skill: `aisa skills show <skill>`
- **Chat com o modelo:** `aisa chat "mensagem"`

*Dica:* Se o comando `npm install -g` apresentar erro de permissão, lembre-se de que a instalação correta é com `--prefix /opt/data/.local`.

---

### Passo 7: Personalizar as Regras de Negócio

> ✅ **As chaves de API já estão configuradas** via variáveis de ambiente da stack (Passo 3) — não é necessário editar nenhum arquivo manualmente para isso.

Acesse o gerenciador de arquivos visual do Dashboard (`https://hermes.seu-dominio.com`) ou o Console do Easypanel e edite:

* 📄 **`/opt/data/support_rules.md`** — regras do negócio, preços, links de checkout, instruções de suporte.
* 📄 **`/opt/data/SOUL_WHATSAPP.md`** — persona e exemplos práticos rápidos de chat do WhatsApp.
* 📄 **`/opt/data/SOUL_EMAIL.md`** — persona e regras formais do e-mail.

---

### 💾 Mapa de Persistência no Easypanel

| Nome do Volume | Caminho Interno | Conteúdo |
|---|---|---|
| `hermes_root` | `/opt/data/.hermes` | config.yaml (criado pelo setup.sh) |
| `hermes_data` | `/opt/data` | SOUL.md, support_rules.md e workspace, chaves de pareamento |

> Os volumes ficam em `/etc/easypanel/projects/<projeto>/hermes/volumes/` no servidor.

---

## 🤖 Setup Via Conversa com o Hermes (Universal — Portainer, Easypanel e Hostinger)

> Em vez de rodar o `setup.sh` pelo terminal do painel, você pode pedir diretamente ao Hermes para fazer o setup do sistema. Funciona em **qualquer instalação** porque o Hermes descobre os seus próprios caminhos automaticamente.

Envie o prompt abaixo para o Hermes pelo **Dashboard Web**, **Telegram** ou **WhatsApp** (na sua conversa privada de dono):

---

```
Hermes, preciso que você execute o setup inicial do modo misto.
Siga os passos abaixo usando suas ferramentas de terminal:

**PASSO 0 — Escolha do repositório de origem**
Antes de começar, me pergunte:

> "Para baixar os arquivos do setup, você prefere usar:
> **(1) Repositório oficial** → https://github.com/empreendedorserial/hermes-whatsapp-mixed
> **(2) Meu próprio fork** → me informe a URL do seu repositório no GitHub (ex: https://github.com/SEU_USUARIO/hermes-whatsapp-mixed)"

Aguarde minha resposta antes de continuar.
- Se eu escolher **(1)**, use `REPO_BASE=https://raw.githubusercontent.com/empreendedorserial/hermes-whatsapp-mixed/main` em todos os comandos curl dos próximos passos.
- Se eu escolher **(2)**, extraia o usuário e repositório da URL que eu informar e monte o `REPO_BASE` correspondente (ex: `https://raw.githubusercontent.com/MEU_USUARIO/hermes-whatsapp-mixed/main`).

**PASSO 1 — Auto-descoberta de caminhos**
Execute e me mostre os resultados:
echo "HOME=$HOME"
echo "HERMES_HOME=$HERMES_HOME"
echo "WORKSPACE=$WORKSPACE"

Use os valores descobertos nas etapas seguintes.
Sempre que eu mencionar $HERMES_HOME, use o valor real encontrado.
Para $DATA_DIR, use o diretório pai do $WORKSPACE (ex: se WORKSPACE=/opt/data/workspace, então DATA_DIR=/opt/data).
Se /opt/data existir, use-o como DATA_DIR. Caso contrário, use $HOME.

**PASSO 2 — Criar estrutura de diretórios**
mkdir -p $HERMES_HOME $DATA_DIR
mkdir -p $HERMES_HOME/plugins/whatsapp-manager

**PASSO 3 — Baixar SOUL.md (persona principal)**
Se o arquivo $DATA_DIR/SOUL.md NÃO existir:
  curl -sSL $REPO_BASE/SOUL.md -o $DATA_DIR/SOUL.md
  cp $DATA_DIR/SOUL.md $HERMES_HOME/SOUL.md
Se já existir, apenas copie a versão persistente para $HERMES_HOME/SOUL.md

**PASSO 4 — Baixar Personas de Suporte (WhatsApp e E-mail)**
Se o arquivo $DATA_DIR/SOUL_WHATSAPP.md NÃO existir:
  curl -sSL $REPO_BASE/SOUL_WHATSAPP.md -o $DATA_DIR/SOUL_WHATSAPP.md
Se o arquivo $DATA_DIR/SOUL_EMAIL.md NÃO existir:
  curl -sSL $REPO_BASE/SOUL_EMAIL.md -o $DATA_DIR/SOUL_EMAIL.md

**PASSO 5 — Baixar support_rules.md**
Se o arquivo $DATA_DIR/support_rules.md NÃO existir:
  curl -sSL $REPO_BASE/support_rules.md -o $DATA_DIR/support_rules.md

**PASSO 6 — Plugin whatsapp-manager pelo dashboard do Hermes**
O plugin `whatsapp-manager` deve ser instalado/atualizado no dashboard do Hermes. O `setup.sh` não baixa mais os arquivos do plugin automaticamente.

**PASSO 7 — Baixar config.yaml inicial**
Se o arquivo $HERMES_HOME/config.yaml NÃO existir:
  curl -sSL $REPO_BASE/config.yaml.example -o $HERMES_HOME/config.yaml

**PASSO 8 — Aplicar patch do WhatsApp**
curl -sSL $REPO_BASE/patch_whatsapp.py -o /tmp/patch_whatsapp.py && python3 /tmp/patch_whatsapp.py

**PASSO 8.5 — Instalar dependências de ponte e geração de imagem do QR Code**
Este passo garante que o pareamento do WhatsApp funcione e que o QR Code possa ser enviado como imagem PNG diretamente pelo Telegram.

1. Instalar dependências Node.js da ponte do WhatsApp:
   cd /opt/hermes/scripts/whatsapp-bridge && npm install --no-fund --no-audit

2. Instalar dependências Python de renderização de imagem no ambiente virtual do Hermes:
   uv pip install --python /opt/hermes/.venv/bin/python qrcode pillow

**PASSO 9 — Criar os perfis separados (whatsapp e email)**
Execute os comandos abaixo para criar os perfis clonando as configurações base:
/opt/hermes/.venv/bin/hermes profile create whatsapp --clone
/opt/hermes/.venv/bin/hermes profile create email --clone

Após criar, confirme com:
/opt/hermes/.venv/bin/hermes profile list

**PASSO 10 — Copiar personas isoladas para cada perfil**
Copie a persona do WhatsApp para o perfil whatsapp:
  cp $DATA_DIR/SOUL_WHATSAPP.md $HERMES_HOME/profiles/whatsapp/SOUL.md

Copie a persona do E-mail para o perfil email:
  cp $DATA_DIR/SOUL_EMAIL.md $HERMES_HOME/profiles/email/SOUL.md

Se os diretórios dos perfis ainda não existirem, crie-os antes:
  mkdir -p $HERMES_HOME/profiles/whatsapp
  mkdir -p $HERMES_HOME/profiles/email

**PASSO 11 — Confirmar resultado**
Me mostre a lista de arquivos criados em $HERMES_HOME, em $HERMES_HOME/plugins/whatsapp-manager, em $HERMES_HOME/profiles e em $DATA_DIR.

Execute cada passo em sequência, pare se houver erro e me explique o que aconteceu.
```

> 💡 **No PASSO 0**, o Hermes vai perguntar se você quer usar o repositório oficial (`empreendedorserial`) ou o seu próprio fork. Basta responder com **(1)** ou colar a URL do seu fork — sem precisar editar nenhum comando manualmente.

### Por que funciona em qualquer ambiente?

O **Passo 1** faz o Hermes ler suas próprias variáveis de ambiente antes de agir. Assim ele descobre os caminhos corretos independente de onde está instalado:

| Variável | Portainer / Easypanel | Hostinger VPS |
|---|---|---|
| `$HERMES_HOME` | `/opt/data/.hermes` | descoberto automaticamente |
| `$DATA_DIR` | `/opt/data` | `/root` ou `/home/hermes` |
| `$WORKSPACE` | `/opt/data/workspace` | descoberto automaticamente |

---

## 🎙️ Como Receber Áudio e Imagem (Transcrição e Visão Integradas)
O plugin `whatsapp-manager` agora transcreve áudios e descreve imagens de forma **nativa e integrada** usando o **Google Gemini API** (`gemini-3.5-flash`), sem necessidade de chaves adicionais de terceiros (como OpenAI/Whisper ou Groq) ou configurações de rede complexas.

### 📸 Recebimento de Imagens (Visão do Bot):
* Quando um cliente envia um print de tela, comprovante ou foto, o plugin envia a imagem para o Gemini analisar em tempo real. Ele gera uma descrição literal e textual da imagem em português (ex: `[Imagem: Uma caneca personalizada com o logo do cérebro]`) que é registrada diretamente na conversa e no banco de dados SQLite `whatsapp_messages.db`. Dessa forma, o agente consegue "enxergar" e responder contextualmente à imagem recebida!

### 🎙️ Recebimento de Áudios (Transcrição Integrada):
* Quando um contato envia uma mensagem de voz, o plugin captura o áudio temporário, envia para a API do Gemini e transcreve a fala textualmente em milissegundos.
* A transcrição é gravada no banco de dados com o prefixo `[Áudio: "conteúdo transcrito..."]` e substitui o texto do evento em tempo real no gateway. O bot responderá em texto de forma imediata e coerente com a mensagem falada!

> 💡 **Privacidade e Descarte**: Os arquivos físicos de fotos e mensagens de voz baixados temporariamente pelo bridge são **excluídos de forma imediata** do disco do servidor logo após serem carregados em memória para análise do Gemini, economizando espaço de armazenamento permanentemente.


---

## 📧 Como Conectar e Ativar o Suporte via Gmail (OAuth Conversacional)

Em vez de digitar códigos no terminal ou usar senhas manuais, você pode autenticar sua conta de e-mail de suporte conversando com o seu Hermes diretamente pelo **console (chat do terminal) ou pelo Telegram**!

### 1. Garantir as Credenciais do Google na Stack
Certifique-se de que as credenciais do seu cliente Google Web estejam definidas nas variáveis da sua Stack do Portainer (como explicado no Passo 2):
* `GOOGLE_CLIENT_ID`
* `GOOGLE_CLIENT_SECRET`
* *Nota: No Google Cloud Console, a URI de redirecionamento autorizada deve ser configurada como: `http://localhost:1`.*

### 2. Pedir o Link ao Bot (No Console do Hermes ou no Telegram)
1. Abra o chat com o seu Hermes (digite `hermes` no console do container, ou envie uma mensagem direta no seu Telegram/WhatsApp do bot pareado).
2. Envie a seguinte instrução para o bot:
   > *"Hermes, inicie o fluxo de login do Gmail de suporte da minha empresa."*
3. O robô vai iniciar o processo em segundo plano e responderá diretamente no chat com um **Link de Consentimento da Google**.
4. Clique no link, faça login com a conta de e-mail de suporte da sua empresa e conceda as permissões de acesso ao Gmail.

### 3. Entregar o Link de Retorno ao Bot
1. Após permitir o acesso, o navegador tentará redirecionar para uma página em branco que começará com:
   👉 `http://localhost:1/?code=***`
2. Copie essa **URL completa diretamente da barra de endereços** do seu navegador.
3. Volte ao seu chat com o Hermes (Console ou Telegram) e apenas envie a URL copiada para ele.

> **Pronto!** O Hermes processará a URL automaticamente, salvará suas credenciais criptografadas e responderá confirmando o sucesso da autenticação. A partir deste momento, ele começará a responder e-mails de suporte de forma 100% autônoma baseando-se nas suas `support_rules.md`!

---

## 💾 Persistência de Dados e Caminhos

Como o Hermes Agent roda containerizado, qualquer arquivo criado fora dos caminhos mapeados no seu volume persistente (`/opt/data`) **será perdido permanentemente** toda vez que o container for atualizado, reiniciado ou recriado.

### 📍 Caminhos Persistentes (SEMPRE SALVE AQUI):
* **Configurações e Chaves:** `HERMES_HOME=/opt/data/.hermes`
* **Área de Trabalho:** `WORKSPACE=/opt/data/workspace`
* **Scripts e Automações:** `/opt/data/scripts`
* **Projetos de Código:** `/opt/data/projects`
* **Arquivos e Bancos:** `/opt/data/files`

---

## 🕹️ Como Usar os Comandos no WhatsApp

Depois de parear o seu WhatsApp no Hermes Agent, você pode controlá-lo enviando mensagens na sua própria conversa de **Self-Chat (você com você mesmo)**:

* **Para desativar temporariamente o atendimento a clientes:** envie `stop_bot`. O robô entrará em modo de pausa apenas para terceiros.
* **Para reativar o atendimento comercial a clientes:** envie `start_bot`. Ele voltará a responder de forma automática.
* **Seu assistente técnico pessoal continuará funcionando o tempo todo!**

---

## 🤖 Estado do Bot (bot_paused) e Silenciamento

O sistema possui duas formas inteligentes de pausar e silenciar o bot comercial para clientes:

### 1. Pausa Global (`stop_bot` / `start_bot`)
Mantém o estado de pausa do bot **mesmo após reinicializações**:
* **Arquivo de estado:** `/opt/data/.hermes/whatsapp/session/bot_state.json`
* **Endpoint HTTP:** `GET /bot-status` — retorna `{ botPaused, uptime }`
* O plugin `whatsapp-manager` consulta `/bot-status` e ignora mensagens de clientes se estiver pausado.

### 2. Silenciamento Temporário Automático (10 minutos)
Quando você (o proprietário) entra em uma conversa com um cliente, o bot é **silenciado especificamente naquela conversa por 10 minutos**. Isso ocorre de forma totalmente automática quando o sistema detecta que:
1. Você leu/abriu a conversa no seu celular ou WhatsApp Web (disparando confirmação de leitura).
2. Você respondeu manualmente ao cliente.
* **Endpoint HTTP:** `GET /chat-status/:chatId` — retorna se a conversa está silenciada e quanto tempo falta.
* **Endpoint HTTP:** `POST /chat-unsilence` — limpa o silêncio da conversa manualmente se desejar reativar o bot antes dos 10 minutos.

### 3. Testes de Regressão (Automatizados)
Para testar e garantir a estabilidade de todas as regras de pausa global e silenciamento temporário por conversa, a stack possui uma suite de testes de regressão automatizados. 

Você pode rodar os testes localmente a partir da raiz do repositório:
```bash
npm install
npm test
```
Esses testes validam automaticamente:
* Ativação e desativação da pausa global via Self-Chat.
* Prevenção de execução de comandos em chats de clientes comerciais.
* Ativação do silêncio de exatamente 10 minutos (600.000 ms) via leitura (`chats.update`) ou resposta manual.
* Isenção de comandos e mensagens iniciadas por `!` do silenciamento automático.
* Prevenção de silenciamento no Self-Chat.

---

## 🤖 Automação Completa & Auto-Update (Zero Intervenção)

Para garantir que o robô seja 100% autossuficiente e livre de manutenção para clientes leigos (mesmo que o contêiner Docker fique em execução ininterrupta por 1 ano), implementamos as seguintes rotinas automatizadas no plugin:

### 1. Sincronização Periódica e Inteligente (GitHub ➔ Servidor)
* **Puxada de Configurações (A cada 1 hora):** O contêiner baixa do seu repositório privado do GitHub as últimas versões de `SOUL.md`, `SOUL_WHATSAPP.md`, `SOUL_EMAIL.md`, `support_rules.md` e `personal_contacts.json`.
* **Sincronização de Contatos do Banco (A cada 24 horas):** Para otimizar o uso de chaves da API de IA com grandes listas de contatos, a varredura e classificação automática em lote a partir do banco de dados local SQLite (`whatsapp_messages.db`) executa a cada 24 horas (no boot e em background).
* **Merge Inteligente:** No caso do `personal_contacts.json`, o plugin mescla os dados locais com as modificações que você fez no GitHub, garantindo que as edições manuais persistam de forma estável.

### 2. Auto-Update de Código com Reinício Automático
* **Como funciona:** A cada **24 horas** (e a cada inicialização), o plugin checa o repositório de código fonte do desenvolvedor em busca de correções de bug ou novos recursos.
* **Reinício Seguro:** Se houver novas atualizações de arquivos críticos (como `whatsapp_manager.py` ou `bridge.js`), o plugin baixa as novidades e encerra o processo de forma limpa. O Docker Compose, configurado com política de restart, reinicia o contêiner automaticamente em segundos para aplicar o novo código.

### 3. Classificação Dinâmica e Blindagem de Contatos
O robô estende o arquivo `personal_contacts.json` para mapear de forma inteligente e manual os contatos individuais:
* **Perfis de Classificação Expandidos:** O contato é automaticamente categorizado pela IA (ou manualmente por você) em uma destas categorias: `Vendedor`, `Cliente`, `Amigo`, `AmigoProximo`, `Parente` ou `Filho`.
* **Bloqueio Manual (`manual_relationship`):** Para travar uma categoria de relacionamento específica (ex: definir um contato como `Filho` ou `Parente`) e impedir que a IA reclassifique o contato no futuro, basta definir esse valor no campo `manual_relationship` (ou na propriedade `relationship`). O sincronizador migra e blinda automaticamente classificações específicas para que não sejam sobrescritas pela IA.
* **Comportamento Direcionado por Notas (`notes`):** Permite adicionar observações personalizadas sobre o contato (ex: *"Sempre agradeça e informe que não tenho interesse no momento"*). Estas diretrizes são injetadas como **Guideline de Alta Prioridade** no contexto do bot, fazendo com que a IA se comporte exatamente conforme as instruções inseridas.
* **Produto Comercializado (`product`):** Para contatos categorizados como `Vendedor`, o bot extrai da conversa ou permite definir manualmente o produto/serviço que está sendo oferecido, ajudando na tomada de decisões.
* **Classificação em Tempo Real (On-Demand) e Segurança de Cota:**
  * Se um novo contato mandar mensagem, ele é classificado **imediatamente na primeira interação** (se tiver $\ge 3$ mensagens no histórico).
  * Para evitar estourar limites de chamadas da API de IA durante sincronizações volumosas, os contatos que excederem o limite padrão são salvos como `"Pendente de classificação."` e adicionados à lista, sendo então classificados automaticamente em tempo real assim que interagirem com o bot.

---

## 👥 Configuração Avançada de Múltiplos Perfis (Profiles Nativo) 🚀

Se você deseja ter **agentes totalmente independentes** rodando ao mesmo tempo (por exemplo: um perfil focado em ser seu Assistente Técnico Pessoal, outro focado 100% no Atendimento de Clientes no WhatsApp, e um terceiro focado exclusivamente em Suporte por E-mail), você pode usar o sistema nativo de **Perfis (Profiles)** do Hermes!

Cada perfil ganha seu próprio painel, chaves de API, banco de dados, memórias e arquivos de persona (`SOUL.md`).

### Como criar e configurar seus perfis separados:

1. Acesse o **Console** do container do `hermes-agent` no seu Portainer.
2. Rode os comandos para criar os perfis clonando as suas configurações base:
   * **Perfil WhatsApp de Suporte:**
     ```bash
     /opt/hermes/.venv/bin/hermes profile create whatsapp --clone
     ```
   * **Perfil E-mail de Suporte:**
     ```bash
     /opt/hermes/.venv/bin/hermes profile create email --clone
     ```
3. Acesse a aba **PROFILES** na sua Dashboard Web (`https://hermes.seu-dominio.com/profiles`) e você verá que agora aparecem os três perfis (`default`, `whatsapp` e `email`).
4. **Isolando as Personas (Arquivos de SOUL separados):**
   * **Seu Assistente Admin (`default`):** Continuará usando o `/opt/data/.hermes/SOUL.md` (onde você deixa apenas as regras de Admin e infraestrutura).
   * **Seu Atendente do WhatsApp (`whatsapp`):** Usará `/opt/data/.hermes/profiles/whatsapp/SOUL.md` (onde você pode colocar as regras de conversa rápida e estilo chat do `SOUL_WHATSAPP.md`).
   * **Seu Atendente do E-mail (`email`):** Usará `/opt/data/.hermes/profiles/email/SOUL.md` (onde você pode colocar o tom formal de e-mail e assinaturas do `SOUL_EMAIL.md`).
5. **Pareando de forma independente:**
   Você pode parear números de WhatsApp ou contas de e-mail diferentes para cada perfil de forma totalmente isolada! Basta acessar o painel de cada perfil de forma independente.

---

## 🚀 Como Atualizar / Fazer Deploy do Plugin

Se você fez modificações no código-fonte do plugin (como regras no `bridge.js` ou novas lógicas), o fluxo de atualização segue estas etapas:

1. **Commit e Push no GitHub (Máquina Local):**
   ```bash
   git status
   git add -A
   git commit -m "MENSAGEM_DO_COMMIT"
   git push origin main
   ```
2. **Pull no Dashboard do Hermes (Painel Web):**
   - Acesse o painel do seu **Hermes Dashboard** -> aba **Plugins**.
   - Localize `whatsapp-manager` e clique em **Pull / Atualizar**.
3. **Reinicialização do Contêiner (Portainer ou Easypanel):**
   - Vá até a tela de contêineres e reinicie o contêiner `hermes-agent` para que o novo código do plugin seja lido e a nova versão do `bridge.js` seja copiada automaticamente.

---

## 🔄 Como Reiniciar a Ponte do WhatsApp de Forma Segura

Toda vez que você rodar o script de setup para sincronizar novas regras ou atualizar sua persona, a ponte do WhatsApp precisa ser recarregada para carregar as novas instruções de forma limpa.

**A forma mais segura, robusta e recomendada de fazer isso em ambiente Docker/Portainer é:**
1. Acesse o seu painel do **Portainer**.
2. Vá em **Stacks** e clique na sua stack `hermes-agent`.
3. Clique em **Restart** (Reiniciar) ou em **Update the stack** para atualizar o container de forma limpa e segura.

*💡 Dica técnica: Evite usar comandos de kill (como pkill -f bridge.js) diretamente de dentro do console do container. Deixar o Portainer gerenciar o ciclo de vida do container previne o travamento de portas e a criação de processos zumbis de Node.js no seu servidor!*

---
*Desenvolvido e disponibilizado pela Comunidade Empreendedor Serial (André Alencar).*
