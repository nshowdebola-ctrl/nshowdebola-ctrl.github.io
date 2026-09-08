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


def _affiliate_link(url: str, tag: str) -> str:
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["tag"] = tag
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def collect_posted_products(tag: str) -> list[dict]:
    seen = {}
    for channel_dir in sorted(CHANNELS_DIR.glob("*")):
        if channel_dir.name in EXCLUDED_CHANNELS:
            continue
        log = _load_json(channel_dir / "posted_log.json")
        posted_ids = [e["id"] for e in log if e.get("status") == "success"]
        catalog = {p["id"]: p for p in _load_json(channel_dir / "products.json")}
        catalog.update({p["id"]: p for p in _load_json(channel_dir / "promocoes.json")})

        for product_id in posted_ids:
            if product_id in seen:
                continue
            product = catalog.get(product_id)
            if not product:
                continue
            seen[product_id] = {
                "id": product["id"],
                "titulo": product["titulo"],
                "preco": product.get("preco"),
                "categoria": product.get("categoria", "Outros"),
                "link": _affiliate_link(product["url_amazon"], tag),
                # Shopee ainda não tem campo no products.json (afiliação pendente
                # de aprovação) — quando existir, basta adicionar "url_shopee" ao
                # produto que o botão aparece sozinho, sem mexer aqui.
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

# Fundo claro fixo (não segue tema claro/escuro do sistema), inspirado no
# visual do achadinhosexpress.com.br: página em cinza bem claro, cards
# brancos com sombra suave, menu de lojas no topo.
BASE_CSS = """
:root {
  color-scheme: light;
  --accent: #ff9900;
  --accent-shopee: #ee4d2d;
  --bg: #f3f4f6;
  --fg: #1a1a1a;
  --card-bg: #ffffff;
  --border: #e5e7eb;
  --muted: #6b7280;
}
body { font-family: system-ui, sans-serif; max-width: 1080px; margin: 0 auto; padding: 16px;
  background: var(--bg); color: var(--fg); }
header { text-align: center; padding: 12px 0 4px; }
header img.logo { width: min(220px, 60vw); height: auto; margin-bottom: 4px; }
header h1 { font-size: 1.8rem; margin: 4px 0; }
header h1.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden;
  clip: rect(0 0 0 0); white-space: nowrap; }
header p.tagline { color: var(--muted); margin-top: 0; }
nav.lojas { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 20px 0 8px;
  background: var(--card-bg); border-radius: 12px; padding: 10px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
nav.lojas button { font: inherit; cursor: pointer; background: transparent; border: 1px solid var(--border);
  color: inherit; font-size: 0.85rem; font-weight: 700; padding: 8px 16px; border-radius: 20px; }
nav.lojas button:hover { border-color: var(--accent); }
nav.lojas button.active { background: var(--accent); border-color: var(--accent); color: #111; }
nav.categorias { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 0 0 20px; }
nav.categorias a { background: var(--card-bg); border: 1px solid var(--border); color: inherit;
  text-decoration: none; font-size: 0.8rem; font-weight: 600; padding: 5px 12px; border-radius: 20px; }
nav.categorias a:hover { border-color: var(--accent); color: var(--accent); }
section.categoria { margin: 32px 0; }
section.categoria h2 { font-size: 1.2rem; border-left: 4px solid var(--accent); padding-left: 10px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 16px; margin: 16px 0; }
.card { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; text-decoration: none;
  color: inherit; display: flex; flex-direction: column; background: var(--card-bg);
  box-shadow: 0 1px 3px rgba(0,0,0,.06); transition: transform .15s, box-shadow .15s; }
.card:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,.12); }
.card img { width: 100%; aspect-ratio: 1; object-fit: cover; display: block; }
.card .info { padding: 10px 12px; flex: 1; display: flex; flex-direction: column; }
.card .titulo { font-size: 0.9rem; font-weight: 600; margin: 0 0 4px; flex: 1; }
.card .preco { color: #c0392b; font-weight: 700; margin: 0 0 8px; }
.card .cta { align-self: flex-start; background: var(--accent); color: #111; font-weight: 700;
  font-size: 0.8rem; padding: 6px 12px; border-radius: 6px; }
.produto-foto { width: 100%; max-width: 420px; border-radius: 10px; display: block; margin: 16px auto;
  box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.btn-row { display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0; }
.btn-comprar { display: inline-block; background: var(--accent); color: #111; font-weight: 700;
  padding: 12px 24px; border-radius: 8px; text-decoration: none; }
.btn-comprar.shopee { background: var(--accent-shopee); color: #fff; }
.disclosure { font-size: 0.8rem; color: var(--muted); border-top: 1px solid var(--border); margin-top: 40px; padding-top: 12px; }
a.voltar { display: inline-block; margin-bottom: 16px; }
.social { display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0; justify-content: center; }
.social a { display: inline-block; background: #222; color: #fff; text-decoration: none;
  font-size: 0.85rem; font-weight: 600; padding: 8px 14px; border-radius: 20px; }
.social a:hover { background: #444; }
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
"""


def render_logo() -> str:
    if LOGO_PATH.exists():
        return f'<img class="logo" src="assets/logo.png" alt="{SITE_TITLE}">'
    return ""


def render_social_links() -> str:
    links = "\n".join(
        f'<a href="{url}" target="_blank" rel="noopener">{html.escape(label)}</a>'
        for label, url in SOCIAL_LINKS
    )
    return f'<div class="social">\n{links}\n</div>'


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
    lojas = "amazon" + (" shopee" if p.get("link_shopee") else "")
    return f'''<a class="card" data-loja="{lojas}" href="produtos/{p['id']}.html">
  <img src="{p['foto_web']}" alt="{html.escape(p['titulo'])}" loading="lazy">
  <div class="info">
    <p class="titulo">{html.escape(p['titulo'])}</p>
    {f'<p class="preco">{html.escape(p["preco"])}</p>' if p.get('preco') else ''}
    <span class="cta">{CTA_TEXTO}</span>
  </div>
</a>'''


def render_store_nav(products: list[dict]) -> str:
    tem_shopee = any(p.get("link_shopee") for p in products)
    botoes = ['<button class="active" onclick="filtrarLoja(\'todos\', this)">Todos</button>',
              '<button onclick="filtrarLoja(\'amazon\', this)">Amazon</button>']
    if tem_shopee:
        botoes.append('<button onclick="filtrarLoja(\'shopee\', this)">Shopee</button>')
    return f'<nav class="lojas">\n{"".join(botoes)}\n</nav>'


def render_index(products: list[dict]) -> str:
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
<style>{BASE_CSS}</style>
<script>{STORE_FILTER_JS}</script>
</head>
<body>
<header>
{render_logo()}
<h1{' class="sr-only"' if LOGO_PATH.exists() else ''}>{SITE_TITLE}</h1>
<p class="tagline">Selecionamos os melhores achadinhos todos os dias — clique pra ver e comprar.</p>
{render_social_links()}
</header>
{render_store_nav(products)}
<nav class="categorias">
{nav}
</nav>
{sections}
<p class="disclosure">{DISCLOSURE}</p>
</body>
</html>
"""


def render_product_page(p: dict) -> str:
    preco_html = f'<p class="preco" style="font-size:1.3rem;color:#c0392b;font-weight:700;">{html.escape(p["preco"])}</p>' if p.get("preco") else ""
    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(p['titulo'])} — {SITE_TITLE}</title>
<meta name="description" content="{html.escape(p['titulo'])}: veja o preço e compre direto na Amazon.">
<style>{BASE_CSS}</style>
</head>
<body>
<a class="voltar" href="../index.html">&larr; Voltar</a>
<h1>{html.escape(p['titulo'])}</h1>
<img class="produto-foto" src="../{p['foto_web']}" alt="{html.escape(p['titulo'])}">
{preco_html}
<div class="btn-row">
<a class="btn-comprar" href="{p['link']}" rel="nofollow sponsored noopener" target="_blank">{CTA_TEXTO} (Amazon)</a>
{f'<a class="btn-comprar shopee" href="{p["link_shopee"]}" rel="nofollow sponsored noopener" target="_blank">{CTA_TEXTO} (Shopee)</a>' if p.get('link_shopee') else ''}
</div>
<p>Segue a gente pra mais achadinhos:</p>
{render_social_links()}
{render_comments(p)}
<p class="disclosure">{DISCLOSURE}</p>
</body>
</html>
"""


def main():
    tag = _amazon_tag()
    products = collect_posted_products(tag)

    shutil.rmtree(PRODUTOS_OUT, ignore_errors=True)
    shutil.rmtree(PHOTOS_OUT, ignore_errors=True)

    copy_photos(products)

    PRODUTOS_OUT.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "index.html").write_text(render_index(products), encoding="utf-8")
    for p in products:
        (PRODUTOS_OUT / f"{p['id']}.html").write_text(render_product_page(p), encoding="utf-8")

    (SITE_DIR / ".nojekyll").touch()

    print(f"{len(products)} produtos publicados em {SITE_DIR}")


if __name__ == "__main__":
    main()
