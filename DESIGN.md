# DESIGN.md — MarketPlace Vision UI

Direction visuelle pour la SPA (`web/`). Un seul service (SPA + FastAPI). La soutenance se lit dans le premier écran : une photo d’objet devient une annonce.

## Principes

1. **Le produit d’abord** — le premier viewport énonce la transformation : photo → catégorie, titre, confiance, statut `auto` ou `a_confirmer`. Le jeton Bearer reste (sessionStorage), dans l’en-tête, jamais en héros.
2. **Une idée par écran** — Studio (la photo devient l’annonce), Parcours (l’oral, une étape à la fois), Comparateur (mesuré contre estimé), Garde-fous (la photo est lue puis oubliée).
3. **Le chiffre qui compte** — un nombre porte l’écran quand il le faut : `0` fichier sur les garde-fous, 68,5 % et les deux latences au studio, 76,5 % seulement avec sa réserve. Premium = une métaphore, un nombre, une hiérarchie. Pas de décor.
4. **Les sources restent** — liens Hugging Face, preuves, manifeste. Visibles, en second, sous l’idée.
5. **Code-forward** — IDs, latences et `$/M` en mono tabular. Les statuts `ready` / `building` / `space_only` et les preuves `mesuré` / `estimé` sont des badges lisibles, pas des pastilles fluorescentes.

## Anti-patterns (interdits)

- Gradients violet / indigo, glow, ombres multi-couches
- Inter, Roboto, Arial, system-ui comme stack principale
- Fond crème chaud `#F4F1EA` + serif + terracotta
- Dark mode par défaut, emojis UI, `rounded-full` pills en grappe
- Landing marketing (bandes de stats, rangées d’icônes, badges flottants)
- Un flash de 200 ms sur la chaîne de requête : l’œil doit pouvoir suivre

## Palette (light canvas)

| Token | Valeur | Usage |
| --- | --- | --- |
| `--bg` | `#F7F7F5` | Canvas (gris pierre très clair, pas crème) |
| `--surface` | `#FFFFFF` | Panneaux interactifs |
| `--ink` | `#121212` | Texte principal / brand |
| `--muted` | `#5C5C57` | Secondaire |
| `--line` | `#E4E4DE` | Bordures |
| `--accent` | `#0F766E` | Accent teal sombre (CTA, focus, chiffre héros) |
| `--accent-ink` | `#FFFFFF` | Texte sur accent |
| `--ok` | `#166534` | ready / auto / mesuré |
| `--warn` | `#A16207` | building / a_confirmer / estimé |
| `--danger` | `#B91C1C` | Erreurs / space_only |
| `--mono-bg` | `#EFEFEA` | Chips code, métriques |

## Typographie

| Rôle | Famille | Notes |
| --- | --- | --- |
| Brand / display | **Syne** (700–800) | Titre d’écran, étape en cours, mot « Photos différentes », le `0` |
| UI / body | **IBM Plex Sans** (400–600) | Lignes courtes |
| Code / métriques | **IBM Plex Mono** (400–500) | `tabular-nums` pour latences, `$/M`, `auto` / `a_confirmer` |

Chargement : Google Fonts avec `display=swap` + `preconnect`.

## Layout & motion

- Grille max ~1120 px ; gutters 24 px ; safe-area insets.
- En-tête : nom, navigation, jeton sur une même bande. Le titre de page est plus grand que la marque.
- **Film de la requête** (Réception → Jeton → Format → 224×224 → Modèle → Catégorie → Phrase → Oubli de la photo) : une étape toutes les ~720 ms, transition 480 ms (`background`, `transform`, largeur du rail). On reste sur « Modèle » tant que la réponse n’est pas là, puis on finit le film avant d’afficher l’annonce. `prefers-reduced-motion` : pas de délai, pas de translation, résultat dès la réponse.
- Entrée de page : fondu court (~220 ms). Le film est le seul mouvement long.
- Le retour « Photos différentes » est une ligne Syne sous le schéma, pas une étiquette SVG de 14 px.
- Focus : anneau `2px` accent (`:focus-visible`), jamais `outline: none` seul.
- Touch : `touch-action: manipulation` ; cibles ≥ 44 px.

## Écrans

### Studio (`/`)

Titre : « Une photo devient une annonce. » Équation visible (catégorie, titre, confiance, statut) avant toute prédiction. Zone photo, sélecteur allowlisté, film, panneau annonce. La description suggérée est légendée comme une règle sur le titre et la catégorie. Deux latences distinctes : inférence de la requête, et la référence it. 4 (p50 21,5 ms / p95 28,6 ms) à côté de la requête conteneur it. 5 (~68 ms p50, chiffre de la facture).

### Parcours (`/parcours`)

Oral guidé : Précédent / Suivant, une idée courte par étape du cycle. Rail des 9 itérations (squelette, cerveau, docker, onnx, charge, sécurité, azure, mlflow, facture) qui ouvre l’étape où le correcteur les trouve. Données et préparation n’ont pas de numéro : elles servent le cerveau et l’ONNX.

### Comparateur (`/comparateur`)

Badge `mesuré` ou `estimé` impossible à manquer. CLIP 76,5 % porte la réserve : zero-shot, vocabulaire générique, Space, pas Azure, ~577 Mo, pas le modèle de prod. EfficientNet, MobileNet et le student restent `estimé`.

### Garde-fous (`/garde-fous`)

Titre : « La photo est lue en mémoire puis oubliée. » Le chiffre est `0` fichier. Auth, MIME, taille, rate-limit et allowlist restent sous ce titre.

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
