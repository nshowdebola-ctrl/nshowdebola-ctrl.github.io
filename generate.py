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

# Canais cujos produtos não devem aparecer no blog (o post no TikTok continua
# normal, só não fica exposto aqui).
EXCLUDED_CHANNELS = {"alexcunhaccb"}
PHOTOS_OUT = SITE_DIR / "assets" / "photos"
PRODUTOS_OUT = SITE_DIR / "produtos"

SITE_TITLE = "Achadinhos"
SITE_URL = "https://nshowdebola-ctrl.github.io"


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
                "link": _affiliate_link(product["url_amazon"], tag),
                # Shopee ainda não tem campo no products.json (afiliação pendente
                # de aprovação) — quando existir, basta adicionar "url_shopee" ao
                # produto que o botão aparece sozinho, sem mexer aqui.
                "link_shopee": product.get("url_shopee"),
                "fotos": [AFILIADO_DIR / foto for foto in product["fotos"]],
            }
    return list(seen.values())


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

DISCLOSURE = (
    "Como Associado Amazon, este site pode ganhar comissões por compras qualificadas feitas "
    "através dos links de produtos, sem nenhum custo extra para você."
)

BASE_CSS = """
:root { color-scheme: light dark; }
body { font-family: system-ui, sans-serif; max-width: 960px; margin: 0 auto; padding: 16px;
  background: #fafafa; color: #1a1a1a; }
@media (prefers-color-scheme: dark) { body { background: #121212; color: #eee; } }
header h1 { font-size: 1.6rem; margin-bottom: 4px; }
header p { color: #777; margin-top: 0; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin: 24px 0; }
.card { border: 1px solid #ddd; border-radius: 10px; overflow: hidden; text-decoration: none;
  color: inherit; display: block; background: white; }
@media (prefers-color-scheme: dark) { .card { background: #1c1c1c; border-color: #333; } }
.card img { width: 100%; aspect-ratio: 1; object-fit: cover; display: block; }
.card .info { padding: 10px 12px; }
.card .titulo { font-size: 0.95rem; font-weight: 600; margin: 0 0 4px; }
.card .preco { color: #c0392b; font-weight: 700; }
.produto-foto { width: 100%; max-width: 420px; border-radius: 10px; display: block; margin: 16px auto; }
.btn-row { display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0; }
.btn-comprar { display: inline-block; background: #ff9900; color: #111; font-weight: 700;
  padding: 12px 24px; border-radius: 8px; text-decoration: none; }
.btn-comprar.shopee { background: #ee4d2d; color: #fff; }
.disclosure { font-size: 0.8rem; color: #888; border-top: 1px solid #ddd; margin-top: 40px; padding-top: 12px; }
a.voltar { display: inline-block; margin-bottom: 16px; }
.social { display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0; }
.social a { display: inline-block; background: #222; color: #fff; text-decoration: none;
  font-size: 0.85rem; font-weight: 600; padding: 8px 14px; border-radius: 20px; }
.social a:hover { background: #444; }
"""


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


def render_index(products: list[dict]) -> str:
    cards = "\n".join(
        f'''<a class="card" href="produtos/{p['id']}.html">
  <img src="{p['foto_web']}" alt="{html.escape(p['titulo'])}" loading="lazy">
  <div class="info">
    <p class="titulo">{html.escape(p['titulo'])}</p>
    {f'<p class="preco">{html.escape(p["preco"])}</p>' if p.get('preco') else ''}
  </div>
</a>'''
        for p in products
    )
    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{SITE_TITLE} — achadinhos da Amazon com preço bom</title>
<meta name="description" content="Seleção de achadinhos da Amazon: produtos úteis e baratos, com link direto pra comprar.">
<style>{BASE_CSS}</style>
</head>
<body>
<header>
<h1>{SITE_TITLE}</h1>
<p>Achadinhos da Amazon selecionados — clique pra ver o produto e o link direto pra comprar.</p>
{render_social_links()}
</header>
<div class="grid">
{cards}
</div>
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
<a class="btn-comprar" href="{p['link']}" rel="nofollow sponsored noopener" target="_blank">Ver oferta na Amazon</a>
{f'<a class="btn-comprar shopee" href="{p["link_shopee"]}" rel="nofollow sponsored noopener" target="_blank">Ver oferta na Shopee</a>' if p.get('link_shopee') else ''}
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
