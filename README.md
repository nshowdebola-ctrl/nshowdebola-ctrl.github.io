# Achadinhos — blog estático

Site estático (sem framework, HTML puro gerado por Python) publicado via GitHub Pages em
https://nshowdebola-ctrl.github.io. Lista os produtos já postados no pipeline
[`afiliado-tiktok`](/home/alex/projetos/afiliado-tiktok), agrupados por categoria, cada um com
uma página própria e o link de afiliado Amazon (e Shopee, quando existir).

Produtos postados só no canal `@alexcunhaccb` ficam de fora de propósito
(ver `EXCLUDED_CHANNELS` em `generate.py`) — o post no TikTok continua normal,
só não aparece publicamente vinculado a esse canal aqui no blog.

## Atualizar o site

Sempre que um novo produto for postado no TikTok, rode:

```bash
python3 generate.py
git add -A && git commit -m "Atualiza produtos" && git push
```

O script lê direto de `../afiliado-tiktok/data/channels/*/posted_log.json` (só produtos com
`status: success` entram no site) e `.env` (tag de afiliado), copia a primeira foto de cada
produto pra `assets/photos/` e gera `index.html` + `produtos/<id>.html`.

## Publicação

GitHub Pages já serve automaticamente a branch `main` deste repositório (nome especial
`nshowdebola-ctrl.github.io` = domínio raiz), sem build step.

## Comentários (Cusdis)

As páginas de produto já têm o widget de comentários pronto, só falta ativar:

1. Crie uma conta grátis em https://cusdis.com.
2. Cadastre um novo site apontando pra `nshowdebola-ctrl.github.io`.
3. Copie o **App ID** gerado e cole em `CUSDIS_APP_ID` no topo de `generate.py`.
4. Rode `python3 generate.py` de novo e faça commit/push.

Enquanto `CUSDIS_APP_ID` estiver vazio, o widget não aparece (sem erro).

## Logo

Coloque o arquivo em `assets/logo.png` e rode `python3 generate.py` de novo — ele aparece
sozinho no topo do site. Sem o arquivo, só o título em texto é exibido (nenhum erro).

## Categorias

Cada produto pode ter um campo `"categoria"` (ex: `"Eletrônicos"`) no `products.json`/`promocoes.json`
do afiliado-tiktok — quando cadastrar um produto novo por lá, use `--categoria "Nome"` no
`add-product`/`add-promo`. Sem categoria definida, o produto cai em "Outros". A ordem de exibição
das categorias é `CATEGORY_ORDER` em `generate.py`.
