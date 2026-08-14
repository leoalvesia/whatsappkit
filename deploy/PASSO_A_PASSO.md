# 📋 Guia Passo a Passo - Configuração do Hermes Agent (Modo Misto)

Este guia prático foi criado para guiar você, aluno da **Comunidade Empreendedor Serial**, na configuração completa do seu robô do zero até ele estar atendendo seus clientes com o Gemini 3.5 Flash e atuando como seu assistente pessoal!

Usaremos um método super moderno: **você editará seus dados visualmente no seu GitHub** e o seu servidor importará tudo de forma automática. Siga os **5 passos simples** abaixo:

---

## 🎨 PASSO 1: Fazer um Fork e Customizar no seu GitHub

Todo o treinamento do robô e alteração de regras é feito de forma visual diretamente na interface do seu GitHub!

1. Na página do repositório oficial (`github.com/empreendedorserial/hermes-whatsapp-mixed`), clique no botão **Fork** (canto superior direito) para criar uma cópia dele na sua própria conta do GitHub.
2. No seu repositório pessoal recém-criado, edite os arquivos diretamente pelo seu navegador (clicando no ícone de lápis ✏️):
   * 📄 **`support_rules.md`**: Coloque as informações da sua empresa, preços, links de checkout (Kiwify, Hotmart, etc.) e formas de suporte. Clique em **Commit changes** para salvar.
   * 📄 **`SOUL.md`**: Personalize o tom e o comportamento do robô se desejar. Clique em **Commit changes** para salvar.

---

## 🛠️ PASSO 2: Subir a Stack e Chaves no Portainer

Todo o gerenciamento de chaves e domínios é feito de forma visual na interface do Portainer!

1. Acesse o painel do seu **Portainer**.
2. Vá no menu lateral em **Stacks** e clique em **Add stack**.
3. Escolha um nome para a stack (ex: `hermes-agent`).
4. Cole o conteúdo do arquivo `docker-compose.yml` (disponível no repositório) no editor de texto.
5. Em **Environment variables** (Variáveis de ambiente) do Portainer, preencha seus domínios e chaves:
   * **`HERMES_DASH_HOST`** = O domínio do seu painel visual (ex: `hermes.seu-dominio.com`).
   * **`HERMES_API_HOST`** = O subdomínio da API (ex: `hermes-api.seu-dominio.com`).
   * **`GOOGLE_API_KEY`** = Cole aqui sua chave do Gemini.
   * **`API_SERVER_KEY`** = Crie uma senha forte para proteger sua API.
   * *Opcional:* Preencha `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` se for usar suporte por e-mail (Gmail).
6. Clique no botão azul **Deploy the stack** na parte inferior da tela e aguarde o status mudar para `running`.

> 🔒 **SSL Automático:** O Traefik integrado na Stack configurará os certificados SSL seguros (HTTPS) para você de forma totalmente transparente e imediata!

---

## ⚡ PASSO 3: Rodar a Sincronização Automatizada (1 Clique)

Agora faremos seu servidor puxar as regras que você salvou no seu GitHub no Passo 1!

> **QR do WhatsApp sem Telegram:** o container único do Hermes executa a ponte internamente (`127.0.0.1:3000`) e o QR fica acessível no próprio domínio do dashboard em `https://SEU-DOMINIO/whatsapp/qr` e `https://SEU-DOMINIO/whatsapp/status`.
> Você também pode pedir `?format=png` ou `?format=svg`.
> Após subir o container, aguarde alguns segundos para a ponte interna inicializar antes de abrir a URL.

1. No painel do Portainer, clique em **Containers** e encontre o container `hermes-agent`.
2. Clique no ícone de **Console** (`>_`) correspondente a ele.
3. Clique em **Connect** para abrir o terminal integrado.
4. **Substitua `SEU_USUARIO_GITHUB` pelo seu usuário real do GitHub** no comando abaixo, cole-o no terminal e aperte **Enter**:

```bash
curl -sSL https://raw.githubusercontent.com/SEU_USUARIO_GITHUB/hermes-whatsapp-mixed/main/deploy/setup.sh | bash -s SEU_USUARIO_GITHUB
```

> **Sincronização Ativa:** O seu servidor baixou a persona (`SOUL.md`) e regras de vendas (`support_rules.md`) direto do seu GitHub pessoal, configurou o `config.yaml` e corrigiu a ponte do WhatsApp. Plugins ficam para o dashboard do Hermes.
> 
> 💡 **Automação Ativa:** O robô agora puxa e aplica atualizações do seu GitHub automaticamente a cada **1 hora**. Caso precise aplicar uma alteração imediatamente de forma instantânea, você pode rodar o comando acima.

---

### 🔒 Opção A: Sincronização Segura com Repositório Privado (Para Contatos Pessoais e Configurações Privadas)

Se você quer salvar seus contatos pessoais (`personal_contacts.json`) ou suas personas (`SOUL.md`, etc.) de forma totalmente privada e segura (para não expor em repositórios públicos), siga estes passos:

1. Crie um repositório **privado** no seu GitHub (ex: `hermes-config-privado`).
2. Adicione nele os arquivos que deseja manter seguros:
   * 📄 **`personal_contacts.json`** (Use o modelo de exemplo disponível em [personal_contacts.json.example](file:///Users/andrealencar/GoogleAntigravity/hermes-whatsapp-mixed/deploy/personal_contacts.json.example) como base).
   * 📄 **`SOUL.md`**, **`SOUL_WHATSAPP.md`**, **`SOUL_EMAIL.md`**, **`support_rules.md`** (opcionais, se você preferir não deixá-los expostos no seu fork público).
3. Gere um **Personal Access Token (PAT)** no GitHub com permissão de leitura de repositório (`repo`).
4. Diferenciamos as chaves do **Cliente** (configuradas visualmente na Stack do Portainer) das chaves do **Desenvolvedor** (mantidas no arquivo `.env` local por segurança):
   * **Na Stack do Portainer (Cliente):**
     * `CLIENT_GITHUB_USER` = Usuário do GitHub do cliente (dono do WhatsApp).
     * `CLIENT_CONFIG_REPO` = Nome do repositório privado de configurações (ex: `usuario-cliente/hermes-config-privado`).
     * `CLIENT_CONFIG_GITHUB_TOKEN` = PAT Token do cliente para acessar seu repositório privado de configs.
   * **No arquivo `.env` em `/opt/data/.env` ou `/opt/data/.hermes/.env` (Desenvolvedor):**
     * `DEV_GITHUB_USER` = Usuário do repositório de código base do Hermes.
     * `DEV_GITHUB_TOKEN` = Token do desenvolvedor (caso o repositório de código base seja privado).
5. Conecte-se ao console do container no Portainer e execute a sincronização de 1 clique. Como as variáveis já estão configuradas no painel da Stack e no `.env`, basta rodar:

```bash
curl -sSL https://raw.githubusercontent.com/SEU_USUARIO_GITHUB/hermes-whatsapp-mixed/main/deploy/setup.sh | bash -s SEU_USUARIO_GITHUB
```

O script baixará os arquivos de código público do seu fork e puxará automaticamente as configurações e contatos do repositório privado do cliente de forma isolada e segura.



---

## 🎨 PASSO BÔNUS: Ajustes Rápidos via Web UI (Dashboard Visual)

Se você precisar fazer uma mudança rápida e pontual e não quiser acessar o GitHub:

1. Abra no seu navegador o endereço do seu painel visual: `https://hermes.seu-dominio.com`
2. No menu lateral, utilize o **Gerenciador de Arquivos Visual**.
3. Clique para editar diretamente na Web os arquivos **`support_rules.md`** ou **`SOUL.md`** localizados na pasta `/opt/data/`.
4. Salve as alterações e o Hermes atualizará as regras no mesmo instante!

---

## 📲 PASSO 4: Conectar o WhatsApp e Ativar

1. Volte ao **Console** do container `hermes-agent` no Portainer (ou abra no Terminal Web do seu Dashboard).
2. Digite o comando abaixo para iniciar o Hermes e gerar o QR Code de pareamento:
   ```bash
   hermes
   ```
3. Um **QR Code** será exibido na tela do terminal. 
4. Abra o WhatsApp no seu celular, vá em **Aparelhos conectados** -> **Conectar um aparelho** e escaneie o código da tela.
5. Assim que a conexão for concluída, você poderá fechar o terminal interativo digitando `/exit`.
6. Para que as novas diretrizes da persona sincronizadas no Passo 3 entrem em vigor na ponte do WhatsApp de forma 100% limpa e estável:
   * Vá ao painel do seu **Portainer**, entre na sua Stack do `hermes-agent` e clique em **Restart** (Reiniciar) no container para recarregar o robô de forma limpa e segura!

---

## 🧪 PASSO 5: O Diagnóstico de Sucesso!

Abra a conversa do seu WhatsApp com **você mesmo (Self-Chat)** e envie a seguinte mensagem para testar a integridade do robô:

> *"Hermes, faça um teste de diagnóstico do meu sistema. Verifique se a minha persona SOUL.md e as regras do support_rules.md foram carregadas, me diga qual modelo de IA você está usando e liste os nossos caminhos persistentes."*

### ✅ Resposta Esperada de Sucesso:
* Ele deve se apresentar como o *Hermes Agent - Edição Especial Empreendedor Serial*.
* Confirmar que está rodando com o **Gemini 3.5 Flash**.
* Confirmar que encontrou e leu seu arquivo `/opt/data/support_rules.md`.
* Listar seus caminhos sob `/opt/data/`.

---

## 🕹️ Comandos de Controle (WhatsApp)

Você agora tem superpoderes! Diretamente do seu chat privado, envie os seguintes comandos para o robô para controlar o atendimento comercial de clientes:

* 🚫 **`stop_bot`** - Pausa imediatamente o chatbot comercial para clientes (enquanto você continua podendo usar o assistente pessoal normalmente).
* 🟢 **`start_bot`** - Reativa o chatbot comercial para responder seus clientes no piloto automático.

---

## 👥 PASSO EXTRA: Configurando Múltiplos Perfis Separados (Profiles Nativo) 🚀

Se você deseja ter **agentes totalmente independentes** rodando ao mesmo tempo (um perfil focado em ser seu Assistente Técnico Pessoal, outro focado 100% no Atendimento ao Cliente no WhatsApp, e um terceiro focado em Suporte por E-mail), você pode usar o sistema de **Perfis (Profiles)** do Hermes:

1. Abra o **Console** do seu container `hermes-agent` no Portainer.
2. Crie os novos perfis herdando as suas chaves base de API rodando os comandos:
   * **Perfil WhatsApp:**
     ```bash
     /opt/hermes/.venv/bin/hermes profile create whatsapp --clone
     ```
   * **Perfil E-mail:**
     ```bash
     /opt/hermes/.venv/bin/hermes profile create email --clone
     ```
3. Abra sua Dashboard Web e clique na aba **PROFILES** (`https://hermes.seu-dominio.com/profiles`). Você verá que agora existem os perfis listados de forma visual!
4. **Isolamento de Prompts (SOULs de cada canal):**
   * **`default` (Admin):** Mantém o `/opt/data/.hermes/SOUL.md` (regras do dono).
   * **`whatsapp` (WhatsApp):** Terá seu próprio arquivo em `/opt/data/.hermes/profiles/whatsapp/SOUL.md` (onde você cola o tom de chat do `SOUL_WHATSAPP.md`).
   * **`email` (E-mail):** Terá seu próprio arquivo em `/opt/data/.hermes/profiles/email/SOUL.md` (onde você cola o tom formal do `SOUL_EMAIL.md`).
5. **WhatsApp e E-mail Independentes:**
   Cada perfil possui seu próprio pareamento e chaves de forma independente. Você pode parear um número exclusivo para o suporte do WhatsApp de clientes e manter seu assistente no seu número privado, além de gerenciar a caixa do suporte do Gmail no perfil de e-mail!

---
*Bons negócios e automações!*  
*Comunidade Empreendedor Serial (André Alencar).*
