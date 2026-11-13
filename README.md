# Marketplace Vision API

**Une photo d'objet → une catégorie d'annonce, un titre suggéré et un niveau de confiance.**

Microservice de vision pour une marketplace type Leboncoin, avec catalogue multi-modèles ONNX, garde-fous, et SPA React servie par le même FastAPI. Projet Ynov, module « Industrialisation de l'IA dans le Cloud » (thème B, Marketplace).

**Prod Azure (live)** : [https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io](https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io) — image ONNX-only + SPA, Bearer `API_TOKEN`.

```json
{
  "categorie": "Électronique",
  "titre_suggere": "Ordinateur portable",
  "confiance": 0.9313,
  "statut": "auto",
  "top3": [
    {"label": "notebook", "categorie": "Électronique", "score": 0.3888},
    {"label": "space bar", "categorie": "Électronique", "score": 0.2576},
    {"label": "laptop", "categorie": "Électronique", "score": 0.2576}
  ],
  "propositions": [{"categorie": "Électronique", "score": 0.9313, "titre": "Ordinateur portable"}],
  "modele": "resnet50-onnx-int8",
  "latence_ms": 32.1
}
```

## En chiffres

| | |
| --- | --- |
| Modèle prod | ResNet-50 → ONNX int8 statique (`resnet50-onnx-int8`) |
| Catalogue | EfficientNet-B0, MobileNetV3-Small, student KD (ONNX int8) ; CLIP = Space ZeroGPU `Lulu18` (`space_only`) |
| Accuracy catégorie | 68,5 % (ResNet, 200 photos) ; CLIP bench 76,5–88,5 % |
| Image Docker Azure | **ONNX-only** ≈ **≤ 551 Mo** (python:3.11-slim + onnxruntime + SPA) ; pas de PyTorch / CUDA |
| Charge | 10 req/s × 5 min : p95 51 ms, 0 erreur |
| Coût | 0 $ phase projet (offre gratuite ACA) ; ≈ 25 $/mois à 1 M images — [FINOPS.md](FINOPS.md) |

## Architecture

```
SPA (web/) ──► FastAPI (app/) ──► garde-fous ──► ModelRegistry ──► ONNX int8 locaux
                                      │                              │
                                 Bearer, MIME,                  /models catalogue
                                 rate-limit, CORS                    │
                                                          CLIP / lourds → Space Lulu18
```

```
app/            API FastAPI (/api/predict, /api/models, /api/health) + static SPA
web/            SPA React + Vite (build → app/static/)
artifacts/onnx/ *.onnx int8 catalogue pré-buildés copiés dans l'image Docker
spaces/distill/ Space HF Lulu18 (distillation ZeroGPU, hors image Azure)
scripts/        export_onnx, export_catalog, distill_student, evaluate*, deploy_azure.sh
Dockerfile      multi-stage : node:22-alpine (SPA) + python:3.11-slim (ONNX-only)
```

## Installation et lancement (≈ 10 min)

Prérequis : Python 3.11+, Node 22+ (SPA), ~2 Go disque ; Docker en option.

```bash
git clone https://github.com/xLucasGitHubx/MarketPlace_Ynov.git && cd MarketPlace_Ynov
python -m venv .venv && source .venv/bin/activate     # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -q

cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"   # coller dans API_TOKEN
set -a; source .env; set +a

python scripts/export_onnx.py                          # ResNet → models/onnx/*-int8-static.onnx
MODEL_BACKEND=onnx uvicorn app.main:app                # API : http://localhost:8000/docs

# SPA en dév (proxy /api → uvicorn)
cd web && npm ci && npm run dev                        # http://localhost:5173
# Prod locale SPA : npm run build && cp -r dist ../app/static
```

```bash
curl -H "Authorization: Bearer $API_TOKEN" -F file=@photo.jpg -F modele=resnet50-onnx-int8 \
  http://localhost:8000/api/predict
```

### Docker (image slim Azure)

```bash
# Build prod : SPA + ResNet int8 exporté au build ; torch n'est PAS dans l'image finale
docker build --target runtime-onnx -t marketplace-api:onnx .
docker run -d --read-only --env-file .env -p 8000:8000 marketplace-api:onnx
# SPA : http://localhost:8000/   ·   API : /api/*   ·   Swagger : /docs

# Optionnel — catalogue int8 (KD / student non requis pour Docker ni Azure) :
python scripts/export_catalog.py
cp models/onnx/efficientnet-b0-int8-static.onnx \
   models/onnx/mobilenet-v3-small-int8-static.onnx \
   artifacts/onnx/   # student-kd-*.onnx uniquement si vous avez distillé
docker build --target runtime-onnx -t marketplace-api:onnx .
# ou : --build-arg PREBUILT_ONNX_DIR=models/onnx  (si le contexte inclut ce dossier)

# API + MLflow
docker compose up -d --build
```

Stratégie taille : rester près de **≤ 551 Mo**. Le catalogue n'ajoute que de petits int8 (quelques Mo chacun). CLIP et PyTorch restent hors runtime Azure (export hors image finale / Space).

## API

| Endpoint | Auth | Rôle |
| --- | --- | --- |
| `POST /api/predict` (`file`, `modele`) | Bearer | Catégorise la photo |
| `GET /api/models` | — | Catalogue (accuracy, p95, $/M, statut) |
| `GET /api/health` | — | Santé + modèles chargés |
| `GET /` | — | SPA (si `app/static/index.html` présent) |
| Alias | | `/predict`, `/models`, `/health` |

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `API_TOKEN` | *(vide → 401)* | Token(s), virgules pour rotation |
| `MODEL_BACKEND` | `pytorch` local / `onnx` Docker | Backend |
| `ONNX_MODELS_DIR` | `models/onnx` | Dossier catalogue ONNX |
| `DEFAULT_MODEL_ID` | `resnet50-onnx-int8` | Modèle par défaut |
| `AZURE_RUNTIME` | `false` | Ignore les modèles `space_only` |
| `RATE_LIMIT_PER_MINUTE` | `60` | Rate-limit mémoire |
| `CORS_ORIGINS` | localhost:5173 | Origines SPA dév |
| `MLFLOW_TRACKING_URI` | *(vide)* | Suivi requêtes |

## Distillation (Space Lulu18) — optionnelle

Jobs GPU (KD ResNet → MobileNet, CLIP lourd) : Space Hugging Face **Lulu18** ZeroGPU (40 min/jour). **Pas requis** pour build Docker / déploiement ACA (ResNet int8 suffit). Voir [docs/preuves/it-hf-space.md](docs/preuves/it-hf-space.md) et `spaces/distill/`.

```bash
python scripts/distill_student.py   # local ou Space ; puis copier l'artifact dans artifacts/onnx/ si désiré
```

## Déploiement Azure Container Apps

1. CI sur `main` : tests + build `runtime-onnx` → `ghcr.io/xlucasgithubx/marketplace_ynov`.
2. Cloud Shell :

```bash
export API_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
LOCATION=swedencentral ./scripts/deploy_azure.sh
```

L'env ACA est créé avec `--logs-destination none` ; `API_TOKEN` est un secret Container Apps ; `AZURE_RUNTIME=true`. Preuve : [docs/preuves/it7-azure.md](docs/preuves/it7-azure.md).

## RGPD et sécurité

- Image jamais écrite sur disque ; conteneur `--read-only` ; uploads en mémoire.
- Allowlist des IDs modèle, rate-limit, rejet images non-objet / trop petites.
- Secrets uniquement via l'environnement (jamais dans l'image ni le dépôt).

## Preuves par itération

| It. | Livrable | Preuve |
| --- | --- | --- |
| 1–6, 8–9 | Squelette → sécurité, ONNX, charge, MLflow, FinOps | [docs/preuves/](docs/preuves/) |
| 7. Grand saut | **Azure live** (Sweden Central) | [it7-azure.md](docs/preuves/it7-azure.md) |
| HF Space | Distillation ZeroGPU Lulu18 | [it-hf-space.md](docs/preuves/it-hf-space.md) |

Décisions : [LLM Council](docs/llm-council/) · Specs : [docs/SPECIFICATIONS.md](docs/SPECIFICATIONS.md) · Design SPA : [DESIGN.md](DESIGN.md)
