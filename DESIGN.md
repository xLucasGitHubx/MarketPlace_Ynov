# DESIGN.md — MarketPlace Vision UI

Direction visuelle pour la SPA (`web/`), inspirée de **Replicate** : canvas clair, typographie expressive, UI code-forward. Un seul service (SPA + FastAPI).

## Principes

1. **Composition unique** — le premier viewport est une app-studio, pas un dashboard marketing.
2. **Brand first** — le nom produit « MarketPlace Vision » est le signal héroïque ; les titres ne le dominent pas.
3. **Code-forward** — IDs modèle, latences, coûts `$/M` en mono tabular ; états `ready` / `building` / `space_only` lisibles comme des badges techniques (pas des pills fluorescentes).
4. **Une job par écran** — Studio (prédire), Comparateur (trancher), Garde-fous (comprendre les limites).
5. **Léger** — pas de cards décoratives ; surfaces = fond + bordure 1 px + rythme typographique.

## Anti-patterns (interdits)

- Gradients violet / indigo, glow, ombres multi-couches
- Inter, Roboto, Arial, system-ui comme stack principale
- Fond crème chaud `#F4F1EA` + serif + terracotta
- Dark mode par défaut, emojis UI, `rounded-full` pills en grappe
- Landing marketing surchargée (stats strips, icon rows, floating badges)

## Palette (light canvas)

| Token | Valeur | Usage |
| --- | --- | --- |
| `--bg` | `#F7F7F5` | Canvas (gris pierre très clair, pas crème) |
| `--surface` | `#FFFFFF` | Panneaux interactifs |
| `--ink` | `#121212` | Texte principal / brand |
| `--muted` | `#5C5C57` | Secondaire |
| `--line` | `#E4E4DE` | Bordures |
| `--accent` | `#0F766E` | Accent teal sombre (CTA, focus) — pas de purple |
| `--accent-ink` | `#FFFFFF` | Texte sur accent |
| `--ok` | `#166534` | Statut ready / auto |
| `--warn` | `#A16207` | building / a_confirmer |
| `--danger` | `#B91C1C` | Erreurs / space_only non dispo |
| `--mono-bg` | `#EFEFEA` | Chips code, métriques |

## Typographie

| Rôle | Famille | Notes |
| --- | --- | --- |
| Brand / display | **Syne** (700–800) | Expressif, non-Inter |
| UI / body | **IBM Plex Sans** (400–600) | Technique, lisible |
| Code / métriques | **IBM Plex Mono** (400–500) | `tabular-nums` pour latences et `$/M` |

Chargement : Google Fonts avec `display=swap` + `preconnect`.

## Layout & motion

- Grille max ~1120 px ; gutters 24–32 px ; safe-area insets.
- Nav horizontale : Studio · Comparateur · Garde-fous + zone token.
- Motion : `opacity` / `transform` uniquement ; 180–280 ms ; respecter `prefers-reduced-motion`.
- Focus : anneau `2px` accent (`:focus-visible`), jamais `outline: none` seul.
- Touch : `touch-action: manipulation` ; cibles ≥ 44 px sur mobile.

## Écrans

### Studio (`/`)

Drop zone photo + sélecteur modèle allowlisté + résultat (catégorie, titre, confiance, statut, top propositions, latence, coût estimé). Une composition : brand, une action principale (analyser), un panneau résultat.

### Comparateur (`/comparateur`)

Tableau / colonnes des modèles : accuracy, p50/p95, taille Mo, `$/M`, statut. Permet de choisir le trade-off perf/coût avant le Studio.

### Garde-fous (`/garde-fous`)

État auth (token sessionStorage), limites upload, rate-limit, MIME, RGPD (0 image sur disque), allowlist modèles.

## Auth front

- Bearer `API_TOKEN` stocké en **`sessionStorage`** uniquement (jamais localStorage, jamais dans le repo).
- Header `Authorization: Bearer …` sur `/api/predict`.
- Prefetch `/api/models` et `/api/health` sans token si l’API l’autorise.

## Build & livraison

```bash
cd web && npm install && npm run build
# → web/dist/  (Docker copie vers app/static/)
```

Vite `base: '/'` ; assets sous `/assets/…`. FastAPI monte `app/static` si `index.html` est présent, sans masquer `/api/*`, `/docs`, `/health`, `/predict`, `/models`.
