# CLAUDE.md — MarketPlace_Ynov

Mémoire de travail du projet pour Claude Code. À tenir à jour à chaque itération.

## Le projet en une phrase

API FastAPI (+ SPA React) qui reçoit la photo d'un objet et renvoie une catégorie d'annonce (type Leboncoin), un titre, une confiance et un statut `auto` / `a_confirmer`, via un **catalogue multi-modèles ONNX** (ResNet prod, EfficientNet, MobileNet, student KD ; CLIP = Space only). Projet Ynov, industrialisation d'un modèle pré-entraîné : pas d'entraînement lourd sur Azure.

Specs : `docs/SPECIFICATIONS.md`. Sujet : `docs/SUJET.md`. Plan multi-modèles : catalogue HF + distillation Space `Lulu18` + SPA premium.

**Prod live** : `https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io`

## Conventions

- Langue : code en anglais ; messages d'API, docs et commits en français.
- Commits petits, format `type(scope): message`.
- Branche par itération `feat/itX-nom`, merge `--no-ff` / PR.
- Aucun secret dans le code (`.env` ignoré ; `.env.example` versionné).
- Aucune image écrite sur disque : `await file.read()`, pas de log du contenu.
- Modèles `models/**/*.onnx` non versionnés (régénérés par `scripts/`) ; pour Docker, copier les int8 catalogue dans `artifacts/onnx/`.

## Commandes

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload                        # API + SPA si app/static présent
cd web && npm ci && npm run dev                      # SPA dév (proxy /api)
cd web && npm run build && cp -r dist ../app/static  # SPA prod locale
pytest -q

python scripts/build_categories.py
python scripts/build_test_set.py
python scripts/export_onnx.py                        # ResNet → models/onnx/
python scripts/export_catalog.py                     # EfficientNet + MobileNet int8
python scripts/distill_student.py                    # KD teacher→student (ou Space Lulu18)
python scripts/evaluate.py --backend onnx --onnx-path models/onnx/resnet50-int8-static.onnx --mlflow
python scripts/evaluate_catalog.py --mlflow
python scripts/benchmark_clip.py [--vocab generique] --mlflow
docker compose up -d --build                         # API ONNX+SPA + MLflow
# Image slim Azure (cible ≤ 551 Mo) :
docker build --target runtime-onnx -t marketplace-api:onnx .
API_TOKEN=... LOCATION=swedencentral ./scripts/deploy_azure.sh
```

Variables utiles : `API_TOKEN`, `MODEL_BACKEND`, `ONNX_MODEL_PATH`, `ONNX_MODELS_DIR`, `DEFAULT_MODEL_ID`, `ENABLED_MODELS`, `HF_MODEL_ALLOWLIST`, `AZURE_RUNTIME`, `RATE_LIMIT_PER_MINUTE`, `CORS_ORIGINS`, `CONFIDENCE_THRESHOLD`, `TOP_K`, `HF_TOKEN`, `MLFLOW_TRACKING_URI`.

## Architecture

```
app/
  main.py          # /api/* + aliases + SPA static
  registry.py      # ModelRegistry + catalogue + métriques
  model.py         # Predictor pytorch | onnx
  security.py      # Bearer, rate-limit, uploads mémoire
  preprocessing.py # MIME, taille, heuristiques non-objet
  static/          # build Vite (généré, non source)
web/               # SPA React+Vite (DESIGN.md)
artifacts/onnx/    # int8 pré-buildés pour COPY Docker
spaces/marketplace-ynov/  # Space Gradio+ZeroGPU Lulu18/MarketPlaceYnov
spaces/distill/    # legacy Docker Space (pas ZeroGPU)
scripts/           # export_*, distill_*, evaluate*, deploy_azure.sh
Dockerfile         # web-build (node:22-alpine) → runtime-onnx (python:3.11-slim, ONNX-only)
```

## Docker / taille image

| Stage | Base | Rôle |
| --- | --- | --- |
| `web-build` | `node:22-alpine` | `npm ci` + Vite → `dist/` seulement |
| `model-onnx` | (torch build) | Export ResNet int8 ; **torch n'entre pas dans le runtime** |
| `onnx-collect` | slim | ResNet exporté + `artifacts/onnx/*.onnx` |
| `runtime-onnx` | `python:3.11-slim` | onnxruntime + app + SPA + `/models/*.onnx` |

Interdit dans l'image Azure : PyTorch, transformers, CUDA, CLIP. Catalogue = COPY de petits int8. Critère : rester ≈ **≤ 551 Mo**.

## Décisions structurantes

| Date | Décision | Source |
| --- | --- | --- |
| 2026-10-30 | Cloud = **Azure Container Apps** ; image GHCR ; Dockerfile sans BuildKit. | Lucas |
| 2026-10-30 | ResNet-50 chemin prod ; CLIP = bench / Space. | LLM Council modèle |
| 2026-11-13 | Multi-modèles ONNX + SPA mono-service ; Space `Lulu18` ZeroGPU pour KD / CLIP ; image Azure ONNX-only slim. | plan multi-model HF UI |

## Avancement des itérations

Ordre MVP : 1 → 2 → 3 → 6 → 4 → 8 → 5 → 7 → 9.

| It. | Statut | Preuve |
| --- | --- | --- |
| 1. Squelette | ✅ | `docs/preuves/it1-squelette.md` |
| 2. Cerveau | ✅ | `docs/preuves/it2-cerveau.md` — 69 % |
| 3. Isolement | ✅ | `docs/preuves/it3-docker.md` — PyTorch 2,04 Go (référence) |
| 6. Barrière | ✅ | `docs/preuves/it6-securite.md` |
| 4. Optimisation | ✅ | `docs/preuves/it4-optimisation.md` — int8, image ≈ 551 Mo |
| 8. Rétroviseur | ✅ | `docs/preuves/it8-mlflow.md` |
| 5. Flux | ✅ | `docs/preuves/it5-charge.md` |
| 7. Grand saut | ✅ **déployé** | `docs/preuves/it7-azure.md` — URL Sweden Central |
| 9. Facture | ✅ | `FINOPS.md` + README |
| HF Space / KD | ✅ script + Gradio ZeroGPU | `docs/preuves/it-hf-space.md`, `spaces/marketplace-ynov/` (legacy Docker : `spaces/distill/`) |

## Mesures clés

| Date | Modèle | Accuracy | p50 / p95 CPU | Note |
| --- | --- | --- | --- | --- |
| 2026-10-30 | resnet50-onnx-int8-static (prod) | 68,5 % | 21,5 / 28,6 ms | 24,9 Mo, image Docker ≈ 551 Mo |
| 2026-10-30 | clip-vit-b32 vocab générique | 76,5 % | 83 / 114 ms | Space / bench, pas ACA |
| 2026-11-13 | catalogue EfficientNet / MobileNet | estimé | voir `catalog_metrics.json` | int8 dans `artifacts/onnx/` pour Docker |

## Pièges connus

- Tests API : injecter `app.state.predictor` (lifespan) — `tests/conftest.py`.
- Ne pas sur-ajuster `data/imagenet_mapping.tsv` sur le jeu de test.
- Docker Hub 429 : `BASE_IMAGE=mirror.gcr.io/library/python:3.11-slim`.
- Proxy TLS : `--build-arg EXTRA_CA_CERT_B64=…` (CA proxy seul).
- Azure Students : pas d'ACR Tasks ; régions limitées ; env ACA avec `--logs-destination none`.
- Starlette SpooledTemporaryFile > 1 Mo : `keep_uploads_in_memory()` — ne pas retirer.
- Quantization dynamique CNN = lent ; utiliser int8 statique QDQ.
- ONNX Runtime 1.31 : IR ≤ 9 si graphe manuel.
- `.env` : pas de commentaire en fin de ligne.
- PyTorch + `--read-only` → `--tmpfs /tmp` (cible `runtime-pytorch` seulement).
- `AZURE_RUNTIME=true` : ne charge jamais `space_only` (CLIP).

## Points ouverts

- Confirmer CLIP / student sur ~100 photos réelles (`data/test_set/real/`) avant bascule prod.
- Exporter encodeur CLIP ONNX int8 seulement si la mesure le justifie (reste Space sinon).
- Mail formateur : ResNet pré-entraîné + CLIP en comparaison + KD légère.
