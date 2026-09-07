# Achadinhos — blog estático

Site estático (sem framework, HTML puro gerado por Python) publicado via GitHub Pages em
https://nshowdebola-ctrl.github.io. Lista os produtos já postados no pipeline
[`afiliado-tiktok`](/home/alex/projetos/afiliado-tiktok) (`@achadinhosmultiuso10` e `@alexcunhaccb`),
cada um com uma página própria e o link de afiliado Amazon.

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
