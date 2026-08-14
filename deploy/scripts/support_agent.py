#!/usr/bin/env python3
import os
import sys
import time
from datetime import datetime
from email.utils import parseaddr

# Configurar timezone para o horário de Brasília
os.environ['TZ'] = 'America/Sao_Paulo'
time.tzset()

import json
import base64
import logging
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Configurar diretório de trabalho e carregar variáveis de ambiente do .env persistente
PERSISTENT_DATA_DIR = "/opt/data"
dotenv_path = os.path.join(PERSISTENT_DATA_DIR, ".env")
load_dotenv(dotenv_path)

# Configurar logging (salvando apenas no arquivo de log de forma silenciosa)
log_file = os.path.join(PERSISTENT_DATA_DIR, "support_agent.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)

# Adicionar o diretório de scripts do google-workspace ao path de importação do Python
HERMES_HOME = "/opt/data/.hermes"
WORKSPACE_SCRIPTS_DIR = os.path.join(HERMES_HOME, "skills/productivity/google-workspace/scripts")
if WORKSPACE_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_SCRIPTS_DIR)

# Lista para acumular mensagens de sucesso a serem impressas no stdout (enviadas por Telegram)
output_notifications = []

try:
    from google_api import build_service, _headers_dict, _extract_message_body
except ImportError as e:
    logging.critical(f"Erro ao importar dependências do google-workspace: {e}")
    print(f"❌ Erro crítico no Agente de Suporte: {e}")
    sys.exit(1)

# Carregar configuração do modelo do gateway (para seguir a stack dinamicamente)
GATEWAY_CONFIG_PATH = "/opt/data/.hermes/config.yaml"

def load_gateway_model_config():
    """Lê o modelo e provider configurados no gateway (config.yaml)."""
    try:
        import yaml
        with open(GATEWAY_CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        model_cfg = config.get("model", {})
        provider = model_cfg.get("provider", "minimax")
        default_model = model_cfg.get("default", "MiniMax-M2.7")
        return provider, default_model
    except Exception as e:
        logging.warning(f"Não foi possível ler config.yaml, usando defaults: {e}")
        return "minimax", "MiniMax-M2.7"

PROVIDER, MODEL_NAME = load_gateway_model_config()
logging.info(f"Modelo configurado: {PROVIDER}/{MODEL_NAME}")

# Obter credenciais do MiniMax via auth.json
def get_minimax_credentials():
    """Busca credenciais do MiniMax no auth.json do gateway."""
    import json
    auth_path = "/opt/data/.hermes/auth.json"
    try:
        with open(auth_path, "r") as f:
            auth = json.load(f)
        creds = auth.get("credential_pool", {}).get("minimax", [])
        if creds:
            c = creds[0]
            return c.get("access_token"), c.get("base_url")
    except Exception as e:
        logging.error(f"Erro ao ler credenciais MiniMax: {e}")
    return None, None

MINIMAX_API_KEY, MINIMAX_BASE_URL = get_minimax_credentials()

# Inicializar cliente HTTP para MiniMax (OpenAI-compatible com base_url customizada)
import http.client
import urllib.parse
import json as json_lib

def llm_chat_completion(model: str, system: str, user: str, temperature: float = 0.3) -> str:
    """Envia requisição ao LLM configurado no gateway (suporta MiniMax/OpenAI/etc)."""
    if not MINIMAX_API_KEY or not MINIMAX_BASE_URL:
        raise RuntimeError("Credenciais MiniMax não encontradas em auth.json")

    # Determinar endpoint conforme provider
    if PROVIDER == "minimax":
        base = MINIMAX_BASE_URL.rstrip("/")
        # O base_url já contém /anthropic, então o path é /anthropic/v1/messages
        endpoint = f"{base}/v1/messages"
        headers = {
            "Authorization": f"Bearer {MINIMAX_API_KEY}",
            "Content-Type": "application/json",
            "x-api-key": MINIMAX_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": MODEL_NAME,
            "max_tokens": 2048,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        }
    else:
        # Fallback OpenAI-compatible (para outros providers)
        base = MINIMAX_BASE_URL.rstrip("/") if MINIMAX_BASE_URL else "https://api.minimax.io/anthropic"
        endpoint = f"{base}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {MINIMAX_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL_NAME,
            "temperature": temperature,
            "max_tokens": 2048,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        }

    from urllib.parse import urlparse
    parsed = urlparse(base)
    conn_host = parsed.netloc or parsed.path.split("/")[0]  # fallback para compat
    # O base_url do MiniMax contém /anthropic no path, então extrair o path completo do endpoint
    full_path = urlparse(endpoint).path if '//' in endpoint else endpoint
    conn = http.client.HTTPSConnection(conn_host)
    conn.request("POST", full_path, json_lib.dumps(payload), headers)
    resp = conn.getresponse()
    raw_body = resp.read().decode("utf-8", errors="replace").strip()

    if resp.status != 200:
        logging.error(f"Erro na API: {resp.status} - {raw_body}")
        raise RuntimeError(f"Erro na API do modelo ({resp.status}): {raw_body}")

    data = None
    try:
        data = json_lib.loads(raw_body)
    except json_lib.JSONDecodeError:
        # Alguns proxies/model gateways prefixam a resposta com texto extra
        # ou embrulham o JSON em lixo de transporte. Tentamos extrair o
        # primeiro objeto/array JSON válido do corpo bruto antes de falhar.
        candidate = None
        for start_char, end_char in (("{", "}"), ("[", "]")):
            start = raw_body.find(start_char)
            end = raw_body.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                candidate = raw_body[start:end + 1]
                try:
                    data = json_lib.loads(candidate)
                    break
                except json_lib.JSONDecodeError:
                    candidate = None
        if data is None:
            logging.error(f"Resposta não-JSON do modelo: {raw_body!r}")
            raise RuntimeError(f"Resposta inválida do modelo: {raw_body[:400]}")

    # Parsear resposta conforme formato (SUPORTE A TIPOS MÚLTIPLOS)
    if PROVIDER == "minimax":
        content = data.get("content", [])
        if content and isinstance(content, list):
            # Prioridade: text > thinking (thinking é reasoning, não resposta final)
            for block in content:
                if block.get("type") == "text":
                    return block.get("text", "")
            # Fallback: thinking (apenas se não houver text)
            for block in content:
                if block.get("type") == "thinking":
                    return block.get("thinking", "")
        return ""
    else:
        return data["choices"][0]["message"]["content"]

# Carregar regras de suporte (Base de Conhecimento)
rules_path = os.path.join(PERSISTENT_DATA_DIR, "support_rules.md")
if os.path.exists(rules_path):
    with open(rules_path, "r", encoding="utf-8") as f:
        rules_content = f.read()
else:
    rules_content = "Não há diretrizes específicas. Responda de forma extremamente profissional e polida."
    logging.warning("Diretrizes de suporte (support_rules.md) não encontradas. Usando comportamento genérico.")

# Carregar persona de e-mail. Preferimos o perfil de e-mail quando existir,
# mas mantemos SOUL_EMAIL.md como fonte de verdade compartilhada.
profile_email_soul = os.path.join(PERSISTENT_DATA_DIR, ".hermes/profiles/email/SOUL.md")
soul_email_path = os.path.join(PERSISTENT_DATA_DIR, "SOUL_EMAIL.md")

if os.path.exists(profile_email_soul):
    with open(profile_email_soul, "r", encoding="utf-8") as f:
        email_soul = f.read()
    logging.info("Carregada persona de e-mail do perfil (profiles/email/SOUL.md).")
elif os.path.exists(soul_email_path):
    with open(soul_email_path, "r", encoding="utf-8") as f:
        email_soul = f.read()
    logging.info("Carregada persona de e-mail oficial (SOUL_EMAIL.md).")
else:
    email_soul = "Você é o assistente automático de suporte por e-mail oficial do André Alencar (suporte@aalencar.com.br)."
    logging.warning("SOUL_EMAIL.md não encontrado; usando persona mínima padrão.")

def is_out_of_hours(dt: datetime) -> bool:
    """Verifica se o horário de chegada do e-mail é fora do horário comercial de Brasília."""
    # 1. Finais de semana (Sábado = 5, Domingo = 6)
    if dt.weekday() >= 5:
        return True
        
    # 2. Fora do horário (antes das 8h ou após as 18h)
    if dt.hour < 8 or dt.hour >= 18:
        return True
        
    # 3. Feriados Nacionais Brasileiros (Mapeados para 2026)
    year = dt.year
    month = dt.month
    day = dt.day
    
    feriados_fixos = [
        (1, 1),   # Ano Novo
        (4, 21),  # Tiradentes
        (5, 1),   # Dia do Trabalho
        (9, 7),   # Independência do Brasil
        (10, 12), # Nossa Senhora Aparecida
        (11, 2),  # Finados
        (11, 15), # Proclamação da República
        (11, 20), # Dia da Consciência Negra
        (12, 25), # Natal
    ]
    
    feriados_moveis_2026 = [
        (2, 17),  # Terça-feira de Carnaval (17/02/2026)
        (4, 3),   # Sexta-feira Santa (03/04/2026)
        (6, 4),   # Corpus Christi (04/06/2026)
    ]
    
    if (month, day) in feriados_fixos:
        return True
        
    if year == 2026 and (month, day) in feriados_moveis_2026:
        return True
        
    return False

def is_auto_reply(headers: dict[str, str], subject: str) -> bool:
    """Verifica de forma minuciosa se o e-mail é uma resposta automática para evitar loops infinitos."""
    headers_lower = {k.lower(): v.lower().strip() for k, v in headers.items()}
    
    # 1. Verificar header Auto-Submitted
    auto_submitted = headers_lower.get("auto-submitted", "")
    if auto_submitted and auto_submitted != "no":
        logging.info(f"Auto-reply detectado via Auto-Submitted: {auto_submitted}")
        return True
        
    # 2. Verificar header Precedence (comum em robôs e listas de e-mail)
    precedence = headers_lower.get("precedence", "")
    if precedence in ["bulk", "junk", "list"]:
        logging.info(f"Auto-reply detectado via Precedence: {precedence}")
        return True
        
    # 3. Verificar outros headers específicos de auto-reply
    x_autoreply = headers_lower.get("x-autoreply", "")
    if x_autoreply in ["yes", "true"]:
        logging.info(f"Auto-reply detectado via X-Autoreply: {x_autoreply}")
        return True
        
    x_auto_response_suppress = headers_lower.get("x-auto-response-suppress", "")
    if x_auto_response_suppress and any(k in x_auto_response_suppress for k in ["oof", "dr", "rn", "nrn", "all"]):
        logging.info(f"Auto-reply detectado via X-Auto-Response-Suppress: {x_auto_response_suppress}")
        return True
        
    # 4. Verificar assunto (subject) por palavras-chave em português e inglês
    subject_lower = subject.lower()
    auto_keywords = [
        "resposta automática", "resposta automatica",
        "respondedor automático", "respondedor automatico",
        "auto-reply", "auto reply", "autoresponse", "auto response",
        "ausência", "ausencia", "out of office", "automatic reply",
        "notificação automática", "notificacao automatica"
    ]
    
    for kw in auto_keywords:
        if kw in subject_lower:
            logging.info(f"Auto-reply detectado via palavra-chave no assunto: '{kw}'")
            return True
            
    return False

def has_human_participated(service, thread_id: str) -> bool:
    """Verifica se um humano já respondeu ou participou desta thread de e-mail."""
    try:
        thread = service.users().threads().get(userId="me", id=thread_id).execute()
        messages = thread.get("messages", [])
    except Exception as e:
        logging.error(f"Erro ao buscar thread {thread_id}: {e}")
        # Por segurança, se der erro, assume participação humana para não interferir
        return True

    for msg in messages:
        # Extrair headers com chaves em minúsculo
        msg_headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        sender = msg_headers.get("from", "").lower()
        
        # 1. Se o remetente for e-mail pessoal do André ou outros conhecidos
        if "andre@aalencar.com.br" in sender or "andre@zigg.com.br" in sender:
            logging.info(f"Thread {thread_id} possui participação humana direta de: {sender}")
            return True
            
        # 2. Se o remetente for a própria conta de suporte
        if "suporte@aalencar.com.br" in sender:
            # Verificar se foi o robô que enviou esta mensagem
            # Se NÃO tiver o header customizado, significa que um humano respondeu usando a conta de suporte!
            is_bot = msg_headers.get("x-processed-by", "") == "hermes-ia-support"
            if not is_bot:
                logging.info(f"Thread {thread_id} foi respondida manualmente por um humano através do e-mail de suporte.")
                return True
                
    return False

def has_been_answered_by_us(service, thread_id: str) -> bool:
    """Verifica se a última mensagem da thread foi enviada pelo suporte (bot ou humano)."""
    try:
        thread = service.users().threads().get(userId="me", id=thread_id).execute()
        messages = thread.get("messages", [])
        if not messages:
            return False
        
        # Pegar a última mensagem da thread
        last_msg = messages[-1]
        
        # Obter cabeçalhos da última mensagem
        last_headers = {h["name"].lower(): h["value"] for h in last_msg.get("payload", {}).get("headers", [])}
        last_sender = last_headers.get("from", "").lower()
        
        # Endereços do suporte (EXCLUI endereços pessoais do André que não são usado para envio de suporte)
        support_addresses = ["suporte@aalencar.com.br", "andre@aalencar.com.br"]
        # Não incluir andre.zigg@gmail.com nem andre@zigg.com.br — são emails pessoais do cliente, não emails de suporte
        for addr in support_addresses:
            if addr in last_sender:
                logging.info(f"Thread {thread_id} já respondida por nós na última mensagem ({last_sender}).")
                return True
                
        return False
    except Exception as e:
        logging.error(f"Erro ao verificar se thread {thread_id} foi respondida por nós: {e}")
        return True # Por segurança, assume que foi respondida para evitar loop em caso de erro

def is_promotional_or_system_email(headers: dict[str, str], sender: str, subject: str) -> bool:
    """Detecta se o e-mail é promocional, newsletter, e-mail em massa ou transacional automático."""
    headers_lower = {k.lower(): v.lower().strip() for k, v in headers.items()}
    sender_lower = sender.lower()
    subject_lower = subject.lower()
    
    # 1. Newsletters e Marketing em Massa quase SEMPRE têm o header List-Unsubscribe
    if "list-unsubscribe" in headers_lower:
        logging.info(f"E-mail de {sender} identificado como marketing/newsletter via List-Unsubscribe.")
        return True
        
    # 2. Verificar Precedence
    precedence = headers_lower.get("precedence", "")
    if precedence in ["bulk", "junk", "list"]:
        logging.info(f"E-mail de {sender} identificado como e-mail em massa via Precedence: {precedence}")
        return True
        
    # 3. Termos comuns em remetentes automáticos ou de marketing
    marketing_keywords = [
        "noreply@", "no-reply@", "dontreply@", "dont-reply@", "mailer-daemon@", "mailer@",
        "notification@", "notifications@", "alert@", "alerts@", "comunicacoes@", "comunicacao@",
        "marketing@", "news@", "newsletter@", "promo@", "promocoes@", "ofertas@", "offers@",
        "vagas@", "bounce@", "info@mercadopago.com", "info@mercadolivre.com"
    ]
    for kw in marketing_keywords:
        if kw in sender_lower:
            logging.info(f"E-mail de {sender} identificado como transacional/marketing via remetente: '{kw}'")
            return True
            
    # 4. Assuntos que indicam e-mail transacional de sistema
    system_subject_keywords = [
        "seu pix foi enviado", "recebemos seu pagamento", "confirmação de pagamento", 
        "seu pedido foi", "sua compra", "fatura disponível", "extrato", "boleto", 
        "código de segurança", "redefinir sua senha", "security code", "password reset"
    ]
    for kw in system_subject_keywords:
        if kw in subject_lower:
            logging.info(f"E-mail de {sender} identificado como transacional/sistema via assunto: '{kw}'")
            return True
            
    return False

def run_agent():
    logging.info("Iniciando verificação de e-mails...")
    try:
        service = build_service("gmail", "v1")
    except Exception as e:
        logging.error(f"Erro ao conectar com a API do Gmail: {e}")
        print(f"❌ Erro de conexão com o Gmail: {e}")
        return

    # Buscar e-mails recentes na Inbox (últimas 24 horas)
    try:
        query = "label:INBOX newer_than:1d"
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
    except Exception as e:
        logging.error(f"Erro ao buscar mensagens: {e}")
        print(f"❌ Erro ao listar mensagens do Gmail: {e}")
        return

    if not messages:
        logging.info("Nenhum e-mail recente encontrado para processar.")
        return

    logging.info(f"Encontrados {len(messages)} e-mail(s) recente(s). Processando...")

    for msg_meta in messages:
        msg_id = msg_meta["id"]
        thread_id = msg_meta["threadId"]
        
        try:
            # Buscar conteúdo completo da mensagem
            original = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
            
            headers = _headers_dict(original)
            # _headers_dict já normaliza as chaves para lowercase.
            sender = headers.get("from", "") or headers.get("reply-to", "") or headers.get("return-path", "") or ""
            subject = headers.get("subject", "") or "(sem assunto)"
            message_id_header = headers.get("message-id", "") or headers.get("message_id", "") or ""
            if not sender:
                logging.warning(f"Headers sem remetente para msg={msg_id}: keys={list(headers.keys())[:20]}")
            

            # 1. Evitar loops de auto-resposta (não responder a nós mesmos)
            if "suporte@aalencar.com.br" in sender.lower() or "noreply" in sender.lower():
                logging.info(f"Ignorando e-mail de {sender} para evitar loop.")
                service.users().messages().modify(
                    userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
                ).execute()
                continue
                
            # 2. Evitar loops contra auto-respostas/out-of-office de clientes
            if is_auto_reply(headers, subject):
                logging.info(f"E-mail de {sender} identificado como Auto-Reply. Ignorando resposta e marcando como lido.")
                service.users().messages().modify(
                    userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
                ).execute()
                continue
                
            # 3. Evitar interferir em conversas que o atendimento humano já respondeu
            if has_human_participated(service, thread_id):
                logging.info(f"Thread {thread_id} já possui atendimento ou participação humana. O robô NÃO vai interferir.")
                # NÃO removemos o label UNREAD para que o humano ainda veja que há uma mensagem nova não lida do cliente!
                continue
                
            # NOVO: Evitar responder threads onde a última mensagem já é nossa (bot ou humano)
            if has_been_answered_by_us(service, thread_id):
                logging.info(f"Thread {thread_id} já está respondida por nós (última mensagem). Pulando.")
                continue
                
            logging.info(f"Processando e-mail de: {sender} | Assunto: {subject}")
            
            # Extrair corpo do e-mail
            body = _extract_message_body(original)
            if not body:
                body = original.get("snippet", "")

            # Detectar se é um formulário de contato do Shopify e tratar e-mail real do cliente
            is_shopify_contact = False
            customer_email = None
            customer_name = None
            
            if "mailer@shopify.com" in sender.lower() or "Nova mensagem de cliente" in subject:
                import re
                is_shopify_contact = True
                
                # Buscar o e-mail real do cliente no corpo da mensagem (suporta quebras de linha e espaços)
                email_match = re.search(r"E-mail:\s*\n*\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", body, re.IGNORECASE)
                if email_match:
                    customer_email = email_match.group(1).strip()
                    
                # Buscar o nome real do cliente no corpo da mensagem
                name_match = re.search(r"Nome:\s*\n*\s*([^\n\r]+)", body, re.IGNORECASE)
                if name_match:
                    customer_name = name_match.group(1).strip()
                    
                if customer_email:
                    logging.info(f"Formulário do Shopify detectado. Redirecionando resposta para o cliente real: {customer_name} <{customer_email}>")
                else:
                    logging.warning("Formulário do Shopify detectado, mas não foi possível extrair o e-mail do cliente real.")
                    # Marcar como lido e ignorar para evitar responder mailer@shopify.com
                    service.users().messages().modify(
                        userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
                    ).execute()
                    continue
                
            # 2.5 Evitar responder e-mails promocionais, newsletters, automáticos ou transacionais (exceto Shopify contato)
            if not is_shopify_contact and is_promotional_or_system_email(headers, sender, subject):
                logging.info(f"E-mail de {sender} identificado como promocional ou transacional de sistema. Ignorando resposta.")
                # Marcar como lido para que não apareça mais como unread
                try:
                    service.users().messages().modify(
                        userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
                    ).execute()
                except Exception as e:
                    logging.error(f"Erro ao remover UNREAD de e-mail promocional: {e}")
                continue
                
            # Calcular o horário exato de chegada do e-mail (internalDate está em ms)
            internal_date_ms = int(original.get("internalDate", 0))
            if internal_date_ms > 0:
                arrival_dt = datetime.fromtimestamp(internal_date_ms / 1000.0)
            else:
                arrival_dt = datetime.now()
                
            out_of_hours = is_out_of_hours(arrival_dt)
            logging.info(f"E-mail recebido em: {arrival_dt.strftime('%d/%m/%Y %H:%M:%S')} | Fora do horário comercial: {out_of_hours}")
            
            # 4. Chamar IA para formular a resposta com base nas diretrizes
            # Injetamos instrução adicional caso o e-mail tenha chegado fora do horário comercial
            additional_instructions = ""
            if out_of_hours and not is_sponsorship_request:
                additional_instructions = """
⚠️ ATENÇÃO: Este e-mail foi recebido FORA do horário comercial brasileiro de atendimento ou em finais de semana/feriados.
Você DEVE seguir estritamente as diretrizes da seção "🕒 Atendimento Fora do Horário Comercial (Noite, Fins de Semana e Feriados)" do arquivo de regras:
1. Explique com muita simpatia e educação que o suporte está fechado no momento.
2. Mencione que o horário normal de atendimento é de Segunda a Sexta, das 8h às 18h.
3. Sugira os canais alternativos fornecidos (comunidade.aalencar.com.br e o bot do Instagram).
4. Assegure que retornaremos com prioridade total logo no início do próximo dia útil.
"""

            system_prompt = f"""### IDIOMA: APENAS PORTUGUÊS BRASILEIRO ###
NUNCA use caracteres em chinês, mandarim, japonês ou qualquer outro idioma. O bot deve responder EXCLUSIVAMENTE em português brasileiro.

{email_soul}

Abaixo estão as diretrizes de negócios, FAQs e regras que você DEVE seguir rigorosamente:

{rules_content}
{additional_instructions}

Instruções adicionais:
- Responda no mesmo idioma do cliente de forma muito amigável, educada e prestativa.
- Retorne APENAS o texto completo do corpo do e-mail que será enviado como resposta (com saudação, conteúdo e a assinatura exata exigida pelas diretrizes).
- Não adicione prefixos como "Suporte:" ou cabeçalhos adicionais. Retorne apenas o texto puro da mensagem."""

            if is_shopify_contact and customer_email:
                user_prompt = f"REMETENTE: {customer_name} <{customer_email}>\nASSUNTO: {subject}\n\nMENSAGEM RECEBIDA:\n{body}"
            else:
                user_prompt = f"REMETENTE: {sender}\nASSUNTO: {subject}\n\nMENSAGEM RECEBIDA:\n{body}"
            
            logging.info(f"Solicitando resposta da IA ({PROVIDER}/{MODEL_NAME})...")
            try:
                reply_text = llm_chat_completion(
                    model=MODEL_NAME,
                    system=system_prompt,
                    user=user_prompt,
                    temperature=0.3
                )
            except Exception as llm_error:
                logging.error(
                    f"Falha ao gerar resposta da IA para msg={msg_id} thread={thread_id} sender={sender!r} subject={subject!r}: {llm_error}",
                    exc_info=True,
                )
                # Mantém o e-mail como não lido para reprocessar depois, mas evita derrubar a rodada inteira.
                continue
            
            # 5. Preparar e enviar a resposta
            if is_shopify_contact and customer_email:
                to_email = customer_email
                target_name_log = f"{customer_name} <{customer_email}>"
            else:
                _, to_email = parseaddr(sender)
                if not to_email and headers.get("Reply-To"):
                    _, to_email = parseaddr(headers.get("Reply-To", ""))
                if not to_email and headers.get("From"):
                    _, to_email = parseaddr(headers.get("From", ""))
                target_name_log = sender or headers.get("Reply-To", "") or headers.get("From", "") or "Desconhecido"

            if not to_email:
                logging.warning(
                    f"Pulando e-mail {msg_id} / thread {thread_id}: não foi possível resolver o destinatário de resposta. sender={sender!r}, reply_to={headers.get('Reply-To', '')!r}, from={headers.get('From', '')!r}"
                )
                continue

            logging.info(f"Enviando resposta em thread {thread_id} para {target_name_log}...")
            
            reply_subject = subject if subject.startswith("Re:") else f"Re: {subject}"
            message = MIMEText(reply_text, "plain", "utf-8")
            
            message["to"] = to_email
            message["subject"] = reply_subject
            message["from"] = "suporte@aalencar.com.br"
            message["X-Processed-By"] = "hermes-ia-support"  # Header exclusivo para rastreamento de IA
            
            if message_id_header:
                message["In-Reply-To"] = message_id_header
                message["References"] = message_id_header
                
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_body = {
                "raw": raw_message,
                "threadId": thread_id
            }
            
            send_result = service.users().messages().send(userId="me", body=send_body).execute()
            logging.info(f"Resposta enviada com sucesso! ID da resposta: {send_result['id']}")
            
            # 6. Marcar mensagem original como lida (remover UNREAD)
            service.users().messages().modify(
                userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            logging.info(f"Mensagem {msg_id} marcada como lida.")
            
            # Registrar sucesso para notificar no Telegram
            status_tag = "🕒 fora do horário" if out_of_hours else "💼 horário comercial"
            display_sender = f"{customer_name} <{customer_email}> (via Shopify)" if is_shopify_contact else sender
            output_notifications.append(
                f"📬 *Novo e-mail de suporte respondido!* ({status_tag})\n"
                f"• *Remetente:* {display_sender}\n"
                f"• *Assunto:* {subject}\n"
                f"• *Chegada:* {arrival_dt.strftime('%d/%m/%Y às %H:%M:%S')}\n"
                f"• *Thread ID:* `{thread_id}`"
            )
            
        except Exception as e:
            logging.error(f"Erro ao processar e-mail {msg_id}: {e}", exc_info=True)
            output_notifications.append(f"⚠️ *Erro ao processar e-mail de {sender or 'Desconhecido'}:* {e}")

if __name__ == "__main__":
    run_agent()
    # Imprime no stdout apenas se houver notificações reais (envia mensagem ao Telegram)
    if output_notifications:
        print("\n\n---\n\n".join(output_notifications))
