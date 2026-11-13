# MarketPlace Vision — SPA

React + Vite + TypeScript. Build statique servi ensuite par FastAPI (`app/static`).

## Commandes

```bash
cd web
npm install
npm run dev      # http://localhost:5173 (proxy /api → :8000)
npm run build    # → web/dist/
npm run preview  # sert web/dist
```

### Docker / FastAPI

Copier le build vers le dossier monté par l’API :

```bash
npm run build
rm -rf ../app/static/*
cp -r dist/* ../app/static/
```

Puis `uvicorn app.main:app --reload` — la SPA est sur `/`, l’API sous `/api/*`.

Variable optionnelle : `VITE_API_BASE` (URL absolue de l’API). Vide = same-origin.

## Routes UI

| Path | Écran |
| --- | --- |
| `/` | Studio — upload + modèle + résultat |
| `/comparateur` | Comparateur perf / coût / taille |
| `/garde-fous` | Auth, limites, RGPD |

Token Bearer : champ en tête d’app → `sessionStorage` (`marketplace_api_token`).

## QA Playwright (optionnel)

```bash
npm install
npx playwright install chromium   # une fois
npm run qa:screenshots            # 1440 + 390, API mockée
```

Pas besoin d’Azure live : les tests interceptent `/api/models`, `/api/health`, `/api/predict`.
