#!/usr/bin/env python3
"""Gera o site estático (index + páginas de produto) a partir dos produtos já
postados no pipeline do afiliado-tiktok. Reroda sempre que houver posts novos:

    python3 generate.py
"""
import html
import json
import re
import shutil
from pathlib import Path

AFILIADO_DIR = Path("/home/alex/projetos/afiliado-tiktok")
CHANNELS_DIR = AFILIADO_DIR / "data" / "channels"
SITE_DIR = Path(__file__).resolve().parent
PHOTOS_OUT = SITE_DIR / "assets" / "photos"
PRODUTOS_OUT = SITE_DIR / "produtos"
LOGO_PATH = SITE_DIR / "assets" / "logo.png"

# Canais cujos produtos não devem aparecer no blog (o post no TikTok continua
# normal, só não fica exposto aqui).
EXCLUDED_CHANNELS = {"alexcunhaccb"}

SITE_TITLE = "Achadinhos da Web"
SITE_URL = "https://nshowdebola-ctrl.github.io"

# Ordem fixa de exibição das categorias. Qualquer categoria nova (ou produto
# sem "categoria" definida, que cai em "Outros") aparece depois, em ordem
# alfabética.
CATEGORY_ORDER = [
    "Eletrônicos",
    "Casa & Utilidades",
    "Beleza",
    "Livros",
    "Esportes & Brinquedos",
    "Ofertas",
]


def _load_json(path: Path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _amazon_tag() -> str:
    env_path = AFILIADO_DIR / ".env"
    match = re.search(r"^AMAZON_TAG=(.+)$", env_path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() if match else ""


def _preco_num(preco: str | None) -> float | None:
    if not preco:
        return None
    digits = re.sub(r"[^\d,\.]", "", preco).replace(".", "").replace(",", ".")
    try:
        return float(digits)
    except ValueError:
        return None


def _desconto_pct(preco: str | None, preco_original: str | None) -> int | None:
    atual, original = _preco_num(preco), _preco_num(preco_original)
    if not atual or not original or original <= atual:
        return None
    return round((1 - atual / original) * 100)


def _affiliate_link(url: str, tag: str) -> str:
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["tag"] = tag
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def collect_posted_products(tag: str) -> list[dict]:
    """Reúne o catálogo de todos os canais não-excluídos.

    Antes só listava produtos já postados no TikTok (status "success" no
    posted_log.json). Agora lista qualquer produto cadastrado — o blog não
    depende mais do ritmo de postagem do TikTok pra crescer (decisão do
    usuário em 2026-09-08).
    """
    from datetime import date

    today = date.today().isoformat()
    seen = {}
    for channel_dir in sorted(CHANNELS_DIR.glob("*")):
        if channel_dir.name in EXCLUDED_CHANNELS:
            continue
        catalog_items = _load_json(channel_dir / "products.json") + _load_json(channel_dir / "promocoes.json")

        for product in catalog_items:
            product_id = product["id"]
            if product_id in seen:
                continue
            valido_ate = product.get("valido_ate")
            if valido_ate and today > valido_ate:
                continue
            seen[product_id] = {
                "id": product["id"],
                "titulo": product["titulo"],
                "preco": product.get("preco"),
                "preco_original": product.get("preco_original"),
                "desconto_pct": _desconto_pct(product.get("preco"), product.get("preco_original")),
                "destaque": bool(product.get("destaque")),
                "categoria": product.get("categoria", "Outros"),
                "link": _affiliate_link(product["url_amazon"], tag) if product.get("url_amazon") else None,
                "link_shopee": product.get("url_shopee"),
                "fotos": [AFILIADO_DIR / foto for foto in product["fotos"]],
            }
    return list(seen.values())


def group_by_category(products: list[dict]) -> list[tuple[str, list[dict]]]:
    by_cat: dict[str, list[dict]] = {}
    for p in products:
        by_cat.setdefault(p["categoria"], []).append(p)

    ordered = [c for c in CATEGORY_ORDER if c in by_cat]
    outros = sorted(c for c in by_cat if c not in CATEGORY_ORDER)
    return [(cat, by_cat[cat]) for cat in ordered + outros]


def copy_photos(products: list[dict]) -> None:
    PHOTOS_OUT.mkdir(parents=True, exist_ok=True)
    for product in products:
        src = product["fotos"][0]
        dest = PHOTOS_OUT / f"{product['id']}{src.suffix}"
        if src.exists():
            shutil.copyfile(src, dest)
        product["foto_web"] = f"assets/photos/{dest.name}"


# Crie uma conta grátis em https://cusdis.com, cadastre o site
# (nshowdebola-ctrl.github.io) e cole o App ID gerado aqui:
CUSDIS_APP_ID = "bc04f0f0-fc8f-46cc-83f7-82436325048f"

SOCIAL_LINKS = [
    ("TikTok · @achadinhosmultiuso10", "https://www.tiktok.com/@achadinhosmultiuso10"),
    ("YouTube · Notícias Show de Bola", "https://www.youtube.com/@NoticiasShowdeBola"),
]

CTA_TEXTO = "🛒 Quero esse!"

DISCLOSURE = (
    "Como Associado Amazon, este site pode ganhar comissões por compras qualificadas feitas "
    "através dos links de produtos, sem nenhum custo extra para você."
)

# Fundo claro fixo (não segue tema claro/escuro do sistema). Cabeçalho e
# rodapé em faixa escura full-bleed (edge-to-edge) pra dar identidade de
# marca; conteúdo central limitado a 1080px via .wrap. Fonte Plus Jakarta
# Sans (Google Fonts) no lugar da system-ui genérica.
GOOGLE_FONTS_LINK = '''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">'''

BASE_CSS = """
:root {
  color-scheme: light;
  --accent: #f59e0b;
  --accent-dark: #d97706;
  --accent-shopee: #ee4d2d;
  --bg: #f7f7f8;
  --fg: #16181d;
  --card-bg: #ffffff;
  --border: #e7e8ec;
  --muted: #6b7280;
  --header-bg: #15161b;
  --header-fg: #f4f4f5;
  --radius: 14px;
  --shadow-sm: 0 1px 2px rgba(16,24,40,.05), 0 1px 3px rgba(16,24,40,.06);
  --shadow-md: 0 6px 16px rgba(16,24,40,.10);
  --shadow-lg: 0 16px 32px rgba(16,24,40,.16);
}
* { box-sizing: border-box; }
body { font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif; margin: 0;
  background: var(--bg); color: var(--fg); -webkit-font-smoothing: antialiased; }
.wrap { max-width: 1080px; margin: 0 auto; padding: 0 16px 48px; }
header.topbar { position: sticky; top: 0; z-index: 50; background: var(--header-bg); color: var(--header-fg);
  box-shadow: 0 2px 10px rgba(0,0,0,.18); }
.topbar-inner { max-width: 1080px; margin: 0 auto; padding: 14px 16px; display: flex; align-items: center;
  justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.brand { display: flex; align-items: center; gap: 10px; text-decoration: none; color: inherit; }
.brand .logo-sm { width: 36px; height: 36px; object-fit: contain; border-radius: 8px; }
.brand .brand-name { font-weight: 800; font-size: 1.08rem; letter-spacing: -.01em; }
nav.topnav { display: flex; align-items: center; gap: 22px; }
nav.topnav a { color: rgba(244,244,245,.85); text-decoration: none; font-weight: 600; font-size: 0.88rem;
  transition: color .15s; }
nav.topnav a:hover { color: var(--accent); }
h1.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden;
  clip: rect(0 0 0 0); white-space: nowrap; }
.hero { text-align: center; padding: 36px 0 8px; }
.hero .tagline { color: var(--muted); font-size: 1.02rem; margin: 0 auto; max-width: 540px; line-height: 1.5; }
.hero .kicker { display: inline-block; background: rgba(245,158,11,.12); color: var(--accent-dark);
  font-weight: 700; font-size: .72rem; letter-spacing: .06em; text-transform: uppercase;
  padding: 5px 12px; border-radius: 20px; margin-bottom: 10px; }
nav.lojas { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 24px 0 10px;
  background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 10px;
  box-shadow: var(--shadow-sm); }
nav.lojas button { font: inherit; cursor: pointer; background: transparent; border: 1px solid var(--border);
  color: inherit; font-size: 0.85rem; font-weight: 700; padding: 8px 18px; border-radius: 20px;
  transition: border-color .15s, background .15s, color .15s; }
nav.lojas button:hover { border-color: var(--accent); }
nav.lojas button.active { background: var(--accent); border-color: var(--accent); color: #17130a; }
nav.categorias { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 0 0 24px; }
nav.categorias a { background: var(--card-bg); border: 1px solid var(--border); color: inherit;
  text-decoration: none; font-size: 0.8rem; font-weight: 600; padding: 6px 14px; border-radius: 20px;
  transition: border-color .15s, color .15s; }
nav.categorias a:hover { border-color: var(--accent); color: var(--accent-dark); }
section.categoria { margin: 36px 0; }
section.categoria h2 { font-size: 1.2rem; font-weight: 800; letter-spacing: -.01em;
  border-left: 4px solid var(--accent); padding-left: 12px; margin: 0 0 4px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 18px; margin: 18px 0; }
.card { position: relative; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden;
  text-decoration: none; color: inherit; display: flex; flex-direction: column; background: var(--card-bg);
  box-shadow: var(--shadow-sm); transition: transform .2s ease, box-shadow .2s ease; }
.card:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); }
.card img { width: 100%; aspect-ratio: 1; object-fit: cover; display: block; background: #fafafa;
  transition: transform .35s ease; }
.card:hover img { transform: scale(1.05); }
.card .badge-desconto { position: absolute; top: 10px; left: 10px;
  background: linear-gradient(135deg, #f43f5e, #be123c); color: #fff; font-size: 0.72rem; font-weight: 800;
  padding: 4px 9px; border-radius: 7px; letter-spacing: .01em; box-shadow: 0 3px 8px rgba(190,18,60,.35); }
.card .info { padding: 12px 14px 14px; flex: 1; display: flex; flex-direction: column; gap: 2px; }
.card .titulo { font-size: 0.89rem; font-weight: 600; line-height: 1.35; margin: 0 0 2px; flex: 1; }
.card .preco-original { color: var(--muted); text-decoration: line-through; font-size: 0.78rem; margin: 0; }
.card .preco { color: #c0392b; font-weight: 800; font-size: 1.04rem; margin: 2px 0 10px; }
.card .cta { display: block; text-align: center; background: var(--accent); color: #17130a; font-weight: 700;
  font-size: 0.82rem; padding: 9px 12px; border-radius: 9px; transition: background .15s, color .15s; }
.card:hover .cta { background: var(--accent-dark); color: #fff; }
.ofertas-carousel { display: flex; gap: 16px; overflow-x: auto; scroll-snap-type: x mandatory;
  margin: 20px 0; padding-bottom: 4px; scrollbar-width: none; }
.ofertas-carousel::-webkit-scrollbar { display: none; }
.oferta-dia { flex: 0 0 auto; scroll-snap-align: start; width: min(360px, 88vw);
  display: flex; gap: 16px; align-items: center; background: var(--card-bg);
  border: 2px solid #e11d48; border-radius: var(--radius); padding: 16px; text-decoration: none;
  color: inherit; box-shadow: 0 4px 14px rgba(225,29,72,.18); }
.oferta-dia img { width: 90px; height: 90px; object-fit: cover; border-radius: 9px; flex-shrink: 0; }
.oferta-dia .tag { display: inline-block; background: #e11d48; color: #fff; font-weight: 800;
  font-size: 0.75rem; padding: 3px 10px; border-radius: 6px; margin-bottom: 6px; }
.oferta-dia .titulo { font-weight: 700; margin: 0 0 4px; font-size: 0.9rem; }
.produto-foto { width: 100%; max-width: 420px; border-radius: var(--radius); display: block; margin: 20px auto;
  box-shadow: var(--shadow-md); background: #fafafa; }
.btn-row { display: flex; flex-wrap: wrap; gap: 12px; margin: 20px 0; }
.btn-comprar { display: inline-block; background: var(--accent); color: #17130a; font-weight: 800;
  font-size: .96rem; padding: 13px 26px; border-radius: 11px; text-decoration: none;
  box-shadow: var(--shadow-md); transition: transform .15s ease, box-shadow .15s ease, background .15s; }
.btn-comprar:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); background: var(--accent-dark); }
.btn-comprar.shopee { background: var(--accent-shopee); color: #fff; }
.btn-comprar.shopee:hover { background: #d43f22; }
a.voltar { display: inline-block; margin: 20px 0 4px; color: var(--muted); text-decoration: none; font-weight: 600;
  font-size: .88rem; }
a.voltar:hover { color: var(--accent-dark); }
footer.site-footer { background: var(--header-bg); color: rgba(244,244,245,.75); margin-top: 56px; }
.footer-inner { max-width: 1080px; margin: 0 auto; padding: 32px 16px 24px; text-align: center; }
.footer-inner p { margin: 0 0 14px; font-weight: 600; color: var(--header-fg); }
.social { display: flex; flex-wrap: wrap; gap: 10px; margin: 0 0 18px; justify-content: center; }
.social a { display: inline-block; background: rgba(255,255,255,.08); color: #fff; text-decoration: none;
  font-size: 0.85rem; font-weight: 600; padding: 8px 16px; border-radius: 20px; transition: background .15s; }
.social a:hover { background: rgba(255,255,255,.16); }
.disclosure { font-size: 0.78rem; color: rgba(244,244,245,.55); border-top: 1px solid rgba(255,255,255,.1);
  margin: 0; padding-top: 16px; }
.disclosure a { color: rgba(244,244,245,.8); }
"""

STORE_FILTER_JS = """
function filtrarLoja(loja, btn) {
  document.querySelectorAll('nav.lojas button').forEach(function (b) { b.classList.remove('active'); });
  btn.classList.add('active');
  document.querySelectorAll('.card').forEach(function (card) {
    var lojas = (card.dataset.loja || '').split(' ');
    card.style.display = (loja === 'todos' || lojas.indexOf(loja) !== -1) ? '' : 'none';
  });
  document.querySelectorAll('section.categoria').forEach(function (sec) {
    var temVisivel = Array.prototype.some.call(
      sec.querySelectorAll('.card'), function (c) { return c.style.display !== 'none'; }
    );
    sec.style.display = temVisivel ? '' : 'none';
  });
}

function iniciarCarrosselOfertas() {
  var el = document.getElementById('ofertas-carousel');
  if (!el) return;
  var cards = el.children;
  if (cards.length <= 1) return;
  var i = 0;
  setInterval(function () {
    i = (i + 1) % cards.length;
    el.scrollTo({left: cards[i].offsetLeft, behavior: 'smooth'});
  }, 4000);
}
document.addEventListener('DOMContentLoaded', iniciarCarrosselOfertas);
"""


def render_meta_seo(url: str, title: str, description: str, image_url: str | None = None) -> str:
    """Canonical + Open Graph + Twitter Card. image_url deve ser absoluta (SITE_URL/...)."""
    img_tags = ""
    if image_url:
        img_tags = f'''<meta property="og:image" content="{image_url}">
<meta name="twitter:image" content="{image_url}">'''
    return f'''<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:locale" content="pt_BR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(title)}">
<meta name="twitter:description" content="{html.escape(description)}">
{img_tags}'''


def render_product_jsonld(p: dict, image_url: str) -> str:
    data = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": p["titulo"],
        "image": [image_url],
        "url": f"{SITE_URL}/produtos/{p['id']}.html",
    }
    if p.get("preco"):
        preco_num = _preco_num(p["preco"])
        if preco_num is not None:
            data["offers"] = {
                "@type": "Offer",
                "url": p.get("link") or p.get("link_shopee"),
                "priceCurrency": "BRL",
                "price": f"{preco_num:.2f}",
                "availability": "https://schema.org/InStock",
            }
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


def render_topbar(base_path: str, tem_shopee: bool) -> str:
    logo_html = f'<img class="logo-sm" src="{base_path}assets/logo.png" alt="{SITE_TITLE}">' if LOGO_PATH.exists() else ""
    shopee_link = f'<a href="{base_path}index.html#vitrine">Shopee</a>' if tem_shopee else ""
    return f'''<header class="topbar">
  <div class="topbar-inner">
    <a class="brand" href="{base_path}index.html">
      {logo_html}
      <span class="brand-name">{SITE_TITLE}</span>
    </a>
    <nav class="topnav">
      <a href="{base_path}index.html#vitrine">Amazon</a>
      {shopee_link}
      <a href="{base_path}sobre.html">Sobre</a>
    </nav>
  </div>
</header>'''


def render_social_links() -> str:
    links = "\n".join(
        f'<a href="{url}" target="_blank" rel="noopener">{html.escape(label)}</a>'
        for label, url in SOCIAL_LINKS
    )
    return f'<div class="social">\n{links}\n</div>'


def render_footer(base_path: str) -> str:
    return f'''<footer class="site-footer">
  <div class="footer-inner">
    <p>Segue a gente pra mais achadinhos:</p>
    {render_social_links()}
    <p class="disclosure"><a href="{base_path}sobre.html#aviso">Aviso de afiliado</a></p>
  </div>
</footer>'''


def render_comments(p: dict) -> str:
    if not CUSDIS_APP_ID:
        return ""
    page_url = f"{SITE_URL}/produtos/{p['id']}.html"
    return f'''<h2 style="margin-top:40px;">Comentários</h2>
<div id="cusdis_thread"
  data-host="https://cusdis.com"
  data-app-id="{CUSDIS_APP_ID}"
  data-page-id="{p['id']}"
  data-page-url="{page_url}"
  data-page-title="{html.escape(p['titulo'])}"
></div>
<script async defer src="https://cusdis.com/js/cusdis.es.js"></script>'''


def _slug(texto: str) -> str:
    import unicodedata

    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def render_card(p: dict) -> str:
    lojas = " ".join(loja for loja, tem in (("amazon", p.get("link")), ("shopee", p.get("link_shopee"))) if tem)
    if p.get("desconto_pct"):
        badge = f'<span class="badge-desconto">-{p["desconto_pct"]}%</span>'
    elif p.get("destaque"):
        badge = '<span class="badge-desconto">Oferta</span>'
    else:
        badge = ""
    preco_original_html = (
        f'<p class="preco-original">{html.escape(p["preco_original"])}</p>' if p.get("desconto_pct") else ""
    )
    return f'''<a class="card" data-loja="{lojas}" href="produtos/{p['id']}.html">
  {badge}
  <img src="{p['foto_web']}" alt="{html.escape(p['titulo'])}" loading="lazy">
  <div class="info">
    <p class="titulo">{html.escape(p['titulo'])}</p>
    {preco_original_html}
    {f'<p class="preco">{html.escape(p["preco"])}</p>' if p.get('preco') else ''}
    <span class="cta">{CTA_TEXTO}</span>
  </div>
</a>'''


def _oferta_card_html(p: dict) -> str:
    if p.get("desconto_pct"):
        tag = f"🔥 Oferta · -{p['desconto_pct']}%"
        preco_original_html = f'<p class="preco-original">{html.escape(p["preco_original"])}</p>'
    else:
        tag = "🔥 Oferta · melhor preço"
        preco_original_html = ""

    return f'''<a class="oferta-dia" href="produtos/{p['id']}.html">
  <img src="{p['foto_web']}" alt="{html.escape(p['titulo'])}">
  <div>
    <span class="tag">{tag}</span>
    <p class="titulo">{html.escape(p['titulo'])}</p>
    {preco_original_html}
    <p class="preco" style="font-size:1.1rem;">{html.escape(p['preco'])}</p>
  </div>
</a>'''


def render_ofertas(products: list[dict]) -> str:
    """Reúne todos os produtos com desconto real (ordenados pelo maior %) e,
    na falta desses, os produtos "destaque" (ordenados por menor preço).
    Mais de uma oferta vira carrossel com auto-scroll (ver iniciarCarrosselOfertas
    em STORE_FILTER_JS); com só uma, o carrossel simplesmente não anda sozinho."""
    com_desconto = sorted(
        (p for p in products if p.get("desconto_pct")), key=lambda p: -p["desconto_pct"]
    )
    destaques = sorted(
        (p for p in products if p.get("destaque") and p.get("preco") and not p.get("desconto_pct")),
        key=lambda p: _preco_num(p["preco"]) or float("inf"),
    )
    ofertas = com_desconto + destaques
    if not ofertas:
        return ""

    cards = "\n".join(_oferta_card_html(p) for p in ofertas)
    return f'<div class="ofertas-carousel" id="ofertas-carousel">\n{cards}\n</div>'


def render_store_nav(products: list[dict]) -> str:
    tem_shopee = any(p.get("link_shopee") for p in products)
    botoes = ['<button class="active" onclick="filtrarLoja(\'todos\', this)">Todos</button>',
              '<button onclick="filtrarLoja(\'amazon\', this)">Amazon</button>']
    if tem_shopee:
        botoes.append('<button onclick="filtrarLoja(\'shopee\', this)">Shopee</button>')
    return f'<nav class="lojas" id="vitrine">\n{"".join(botoes)}\n</nav>'


def render_index(products: list[dict]) -> str:
    tem_shopee = any(p.get("link_shopee") for p in products)
    grouped = group_by_category(products)

    nav = "\n".join(f'<a href="#{_slug(cat)}">{html.escape(cat)}</a>' for cat, _ in grouped)
    sections = "\n".join(
        f'''<section class="categoria" id="{_slug(cat)}">
  <h2>{html.escape(cat)}</h2>
  <div class="grid">
    {"".join(render_card(p) for p in items)}
  </div>
</section>'''
        for cat, items in grouped
    )

    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{SITE_TITLE} — achadinhos da Amazon com preço bom</title>
<meta name="description" content="Seleção de achadinhos da Amazon: produtos úteis e baratos, com link direto pra comprar.">
{render_meta_seo(SITE_URL + "/", SITE_TITLE, "Seleção de achadinhos da Amazon: produtos úteis e baratos, com link direto pra comprar.", f"{SITE_URL}/assets/logo.png" if LOGO_PATH.exists() else None)}
{GOOGLE_FONTS_LINK}
<style>{BASE_CSS}</style>
<script>{STORE_FILTER_JS}</script>
</head>
<body>
{render_topbar("", tem_shopee)}
<div class="wrap">
<h1 class="sr-only">{SITE_TITLE}</h1>
<div class="hero">
<span class="kicker">Curadoria diária</span>
<p class="tagline">Selecionamos os melhores achadinhos todos os dias — clique pra ver e comprar.</p>
</div>
{render_ofertas(products)}
{render_store_nav(products)}
<nav class="categorias">
{nav}
</nav>
{sections}
</div>
{render_footer("")}
</body>
</html>
"""


def render_product_page(p: dict, tem_shopee: bool) -> str:
    if p.get("desconto_pct"):
        badge_html = f'<p><span class="badge-desconto" style="position:static;">-{p["desconto_pct"]}% OFF</span></p>'
    elif p.get("destaque"):
        badge_html = '<p><span class="badge-desconto" style="position:static;">Oferta</span></p>'
    else:
        badge_html = ""
    preco_original_html = (
        f'<p class="preco-original" style="font-size:1rem;">{html.escape(p["preco_original"])}</p>'
        if p.get("desconto_pct") else ""
    )
    preco_html = f'<p class="preco" style="font-size:1.3rem;color:#c0392b;font-weight:700;">{html.escape(p["preco"])}</p>' if p.get("preco") else ""
    descricao_seo = f"{p['titulo']}: veja o preço e compre direto na Amazon."
    imagem_absoluta = f"{SITE_URL}/{p['foto_web']}"
    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(p['titulo'])} — {SITE_TITLE}</title>
<meta name="description" content="{html.escape(descricao_seo)}">
{render_meta_seo(f"{SITE_URL}/produtos/{p['id']}.html", p['titulo'], descricao_seo, imagem_absoluta)}
{render_product_jsonld(p, imagem_absoluta)}
{GOOGLE_FONTS_LINK}
<style>{BASE_CSS}</style>
</head>
<body>
{render_topbar("../", tem_shopee)}
<div class="wrap">
<a class="voltar" href="../index.html">&larr; Voltar</a>
<h1>{html.escape(p['titulo'])}</h1>
<img class="produto-foto" src="../{p['foto_web']}" alt="{html.escape(p['titulo'])}">
{badge_html}
{preco_original_html}
{preco_html}
<div class="btn-row">
{f'<a class="btn-comprar" href="{p["link"]}" rel="nofollow sponsored noopener" target="_blank">{CTA_TEXTO} (Amazon)</a>' if p.get('link') else ''}
{f'<a class="btn-comprar shopee" href="{p["link_shopee"]}" rel="nofollow sponsored noopener" target="_blank">{CTA_TEXTO} (Shopee)</a>' if p.get('link_shopee') else ''}
</div>
{render_comments(p)}
</div>
{render_footer("../")}
</body>
</html>
"""


def render_sobre_page(tem_shopee: bool) -> str:
    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sobre — {SITE_TITLE}</title>
<meta name="description" content="Quem somos e como funciona o {SITE_TITLE}.">
{render_meta_seo(f"{SITE_URL}/sobre.html", f"Sobre — {SITE_TITLE}", f"Quem somos e como funciona o {SITE_TITLE}.")}
{GOOGLE_FONTS_LINK}
<style>{BASE_CSS}</style>
</head>
<body>
{render_topbar("", tem_shopee)}
<div class="wrap">
<a class="voltar" href="index.html">&larr; Voltar</a>
<h1>Sobre o {SITE_TITLE}</h1>
<p>O {SITE_TITLE} é um site de curadoria: selecionamos achadinhos da Amazon (e, em breve,
da Shopee) que a gente também divulga no TikTok, e reunimos tudo aqui com o link direto pra
comprar. Não somos Amazon nem Shopee — as compras são feitas diretamente nos sites das lojas
parceiras.</p>
<p class="disclosure" id="aviso" style="color:var(--muted); border-top:1px solid var(--border); padding-top:16px;">{DISCLOSURE}</p>
</div>
{render_footer("")}
</body>
</html>
"""


def render_sitemap(products: list[dict]) -> str:
    from datetime import date

    hoje = date.today().isoformat()
    urls = [f"{SITE_URL}/", f"{SITE_URL}/sobre.html"] + [
        f"{SITE_URL}/produtos/{p['id']}.html" for p in products
    ]
    entries = "\n".join(f"  <url><loc>{u}</loc><lastmod>{hoje}</lastmod></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n'


ROBOTS_TXT = f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""


def main():
    tag = _amazon_tag()
    products = collect_posted_products(tag)
    tem_shopee = any(p.get("link_shopee") for p in products)

    shutil.rmtree(PRODUTOS_OUT, ignore_errors=True)
    shutil.rmtree(PHOTOS_OUT, ignore_errors=True)

    copy_photos(products)

    PRODUTOS_OUT.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "index.html").write_text(render_index(products), encoding="utf-8")
    (SITE_DIR / "sobre.html").write_text(render_sobre_page(tem_shopee), encoding="utf-8")
    for p in products:
        (PRODUTOS_OUT / f"{p['id']}.html").write_text(render_product_page(p, tem_shopee), encoding="utf-8")

    (SITE_DIR / "sitemap.xml").write_text(render_sitemap(products), encoding="utf-8")
    (SITE_DIR / "robots.txt").write_text(ROBOTS_TXT, encoding="utf-8")
    (SITE_DIR / ".nojekyll").touch()

    print(f"{len(products)} produtos publicados em {SITE_DIR}")


if __name__ == "__main__":
    main()
