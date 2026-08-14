---
name: research-sources
description: "Busca em YouTube, web (Brave Search) e Reddit — sem dependências externas, tudo via urllib."
category: research
---

# Research Sources — YouTube, Brave Search e Reddit

Esta skill ensina o agente a buscar informações em fontes externas usando as credenciais já disponíveis na stack.

---

## Quando usar

| Pedido do usuário | Fonte recomendada |
|---|---|
| "tutorial de...", "como fazer...", "vídeo sobre..." | YouTube |
| "pesquisa sobre...", "o que é...", "últimas notícias de..." | Brave Search |
| "opinião sobre...", "experiência com...", "comunidade..." | Reddit |
| "lê esse link para mim", "resumo desse artigo..." | Jina Reader |

---

## Credenciais necessárias

| Variável | Uso | Obter em |
|---|---|---|
| `GOOGLE_API_KEY` | YouTube Data API v3 | Já está na stack |
| `BRAVE_API_KEY` | Brave Search API | https://api.search.brave.com/app/keys (grátis 2000/mês) |
| *(nenhuma)* | Reddit + Jina | Não precisa de auth |

---

## YouTube — buscar vídeos

```bash
python3 - <<'EOF'
import os, urllib.request, urllib.parse, json

api_key = os.getenv("GOOGLE_API_KEY", "")
if not api_key:
    print("❌ GOOGLE_API_KEY não configurada.")
    exit(1)

# ← Substituir pelo termo de busca
QUERY = "n8n tutorial automação"

params = urllib.parse.urlencode({
    "key": api_key,
    "q": QUERY,
    "part": "snippet",
    "type": "video",
    "maxResults": 5,
    "relevanceLanguage": "pt",
    "order": "relevance",
})

url = f"https://www.googleapis.com/youtube/v3/search?{params}"
with urllib.request.urlopen(url) as resp:
    data = json.loads(resp.read().decode())

for item in data.get("items", []):
    vid = item["id"].get("videoId", "")
    title = item["snippet"]["title"]
    channel = item["snippet"]["channelTitle"]
    print(f"▶ {title}")
    print(f"  Canal: {channel}")
    print(f"  URL: https://www.youtube.com/watch?v={vid}")
    print()
EOF
```

---

## Brave Search — busca web geral

```bash
python3 - <<'EOF'
import os, urllib.request, urllib.parse, json

api_key = os.getenv("BRAVE_API_KEY", "")
if not api_key:
    print("❌ BRAVE_API_KEY não configurada. Cadastre em: https://api.search.brave.com/app/keys")
    exit(1)

# ← Substituir pelo termo de busca
QUERY = "n8n automação workflow"

params = urllib.parse.urlencode({
    "q": QUERY,
    "count": 5,
    "country": "BR",
    "search_lang": "pt",
    "ui_lang": "pt-BR",
})

url = f"https://api.search.brave.com/res/v1/web/search?{params}"
req = urllib.request.Request(url, headers={
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "X-Subscription-Token": api_key,
})

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

results = data.get("web", {}).get("results", [])
for r in results:
    print(f"🔍 {r.get('title')}")
    print(f"   {r.get('url')}")
    print(f"   {r.get('description', '')[:120]}...")
    print()
EOF
```

---

## Reddit — buscar posts e discussões

```bash
python3 - <<'EOF'
import urllib.request, urllib.parse, json

# ← Substituir pelo termo e subreddit (deixe subreddit="" para busca global)
QUERY = "n8n automação"
SUBREDDIT = ""   # Ex: "n8n", "artificial", "brasil" — ou "" para toda a web

if SUBREDDIT:
    url = f"https://www.reddit.com/r/{SUBREDDIT}/search.json"
    restrict = "true"
else:
    url = "https://www.reddit.com/search.json"
    restrict = "false"

params = urllib.parse.urlencode({
    "q": QUERY,
    "restrict_sr": restrict,
    "sort": "relevance",
    "limit": 5,
    "t": "year",
})

req = urllib.request.Request(
    f"{url}?{params}",
    headers={"User-Agent": "hermes-research-bot/1.0"}
)

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

posts = data.get("data", {}).get("children", [])
for post in posts:
    p = post["data"]
    score = p.get("score", 0)
    comments = p.get("num_comments", 0)
    print(f"📌 {p.get('title')}")
    print(f"   r/{p.get('subreddit')} | ⬆ {score} | 💬 {comments} comentários")
    print(f"   https://reddit.com{p.get('permalink')}")
    print()
EOF
```

---

## Jina Reader — ler conteúdo de qualquer URL

Útil para o agente ler o artigo/post completo após encontrar nos resultados:

```bash
python3 - <<'EOF'
import urllib.request

# ← Substituir pela URL a ser lida
TARGET_URL = "https://www.reddit.com/r/n8n/comments/xxx/"

jina_url = f"https://r.jina.ai/{TARGET_URL}"
req = urllib.request.Request(jina_url, headers={"User-Agent": "hermes/1.0"})

with urllib.request.urlopen(req, timeout=15) as resp:
    content = resp.read().decode("utf-8", errors="replace")

# Limitar para os primeiros 3000 caracteres (suficiente para resumo)
print(content[:3000])
EOF
```

---

## Fluxo completo recomendado

Quando o usuário pede pesquisa, o agente deve:

1. **Identificar a fonte** com base no tipo de pedido (tabela no topo)
2. **Executar o script** correspondente com o termo de busca
3. **Apresentar os resultados** de forma resumida (título + URL + descrição curta)
4. **Oferecer aprofundar**: "Quer que eu leia o conteúdo de algum desses links?"
5. **Usar Jina Reader** se o usuário quiser o conteúdo completo de um link

---

## Notas

- YouTube: **10.000 unidades/dia grátis** (cada busca = 100 unidades → ~100 buscas/dia)
- Brave: **2.000 buscas/mês grátis** no plano free
- Reddit: **sem limite** para leitura pública
- Jina Reader: **sem limite** declarado para uso normal
