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
python scripts/build_test_thumbnails.py            # vignettes WebP → web/public/jeu/
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
| 2026-11-13 | Parcours MLOps dans la SPA (`/parcours`) ; `description_suggeree` est une règle, pas un second modèle. | assemblage front |
| 2026-11-20 | UI soutenance : premier écran = photo → catégorie, titre, confiance, statut. Film de requête ~720 ms/étape. Parcours oral (précédent/suivant) mappé sur les 9 itérations. Badge mesuré/estimé. Titre garde-fous = photo lue en mémoire puis oubliée. | refonte jury |
| 2026-11-20 | Diagnostic du notebook formateur intégré à l’étape Mesure du parcours (parties guidées). Chiffres issus des preuves it. 4 / it. 5. Lots 1–16, p99 d’inférence, prétraitement seul, pic CUDA : non mesurés, affichés comme tels. | notebook diagnostiquer_performances |
| 2026-11-20 | EfficientNet-B0 int8 statique dans `artifacts/onnx/` (ready). Session ONNX = `ORT_ENABLE_BASIC` : `ENABLE_ALL` écrase le QDQ en classe constante. MobileNet et student restent `building`. | catalogue ready |
| 2026-11-20 | Étape Données : vignettes WebP (~0,5 Mo) des 200 lignes de `data/test_set/manifest.csv`. Les JPEG d’origine restent hors git et hors image. | galerie proxy |
| 2026-11-24 | Deux protocoles distincts (proxy 200 et jeu focal 100+100). EfficientNet int8 mesuré. Student id timm, toujours `building`. CLIP reste `space_only`. | `docs/preuves/it-eval-jury.md` |

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
| 7. Grand saut | ✅ **déployé** + CD OIDC | `docs/preuves/it7-azure.md` — URL Sweden Central ; job `deploy` après `image` sur `main` |
| 9. Facture | ✅ | `FINOPS.md` + README |
| HF Space / KD | ✅ script + Gradio ZeroGPU | `docs/preuves/it-hf-space.md`, `spaces/marketplace-ynov/` (legacy Docker : `spaces/distill/`) |

## Mesures clés

| Date | Modèle | Accuracy | p50 / p95 CPU | Note |
| --- | --- | --- | --- | --- |
| 2026-10-30 | resnet50-onnx-int8-static (prod) | 68,5 % | 21,5 / 28,6 ms | 24,9 Mo, image Docker ≈ 551 Mo |
| 2026-10-30 | clip-vit-b32 vocab générique | 76,5 % | 83 / 114 ms | bench local, pas ACA. Relance du 24 nov. : même accuracy, p50 82,6 ms |
| 2026-11-13 | catalogue EfficientNet / MobileNet / student | graines | voir `catalog_metrics.json` | EfficientNet mesuré le 24 nov. MobileNet (60 %) et student (64 %) restent estimés |
| 2026-11-20 | efficientnet-b0-int8-static | graine 0,66 (périmée) | non mesurée ce jour-là | sonde top-1 7/8 vs fp32, non rejouée. MobileNet int8 non livré (0/8). Le 0,66 n’est plus le chiffre |
| 2026-11-24 | efficientnet-b0-int8, proxy 200 | 63,5 % | 103,8 / 120,7 ms | mesuré, CPU Windows, `ORT_ENABLE_BASIC`. Autre banc que le 21,5 ms ResNet |
| 2026-11-24 | clip-vit-b32 vocab générique, proxy 200 | 76,5 % | 82,6 / 90,0 ms | relance locale, 24 textes. Le catalogue garde le p50 historique 83,0 ms |
| 2026-11-24 | efficientnet-b0-int8, jeu focal 100+100 | 52,5 % | 23,0 / 26,2 ms | Véhicules 88 %, Jeux 17 %. p50 non comparable au 103,8 ms |
| 2026-11-24 | clip-vit-b32 générique, jeu focal 100+100 | 62,5 % | 53,3 / 82,6 ms | Véhicules 44 %, Jeux 81 %. Accord EfficientNet 30,5 %. ResNet absent. Le 82,6 ms est le p95 |

## Pièges connus

- Tests API : injecter `app.state.predictor` (lifespan) — `tests/conftest.py`.
- Ne pas sur-ajuster `data/imagenet_mapping.tsv` sur le jeu de test.
- Docker Hub 429 : `BASE_IMAGE=mirror.gcr.io/library/python:3.11-slim`.
- Proxy TLS : `--build-arg EXTRA_CA_CERT_B64=…` (CA proxy seul).
- Azure Students : pas d'ACR Tasks ; régions limitées ; env ACA avec `--logs-destination none`.
- Starlette SpooledTemporaryFile > 1 Mo : `keep_uploads_in_memory()` — ne pas retirer.
- Quantization dynamique CNN = lent ; utiliser int8 statique QDQ.
- `ORT_ENABLE_ALL` sur un QDQ EfficientNet renvoie une classe constante. `OnnxPredictor` reste en `ORT_ENABLE_BASIC`.
- MobileNetV3 : le QDQ statique et l’int8 dynamique ORT 1.32 donnent 0/8 top-1 vs le fp32 (HardSwish). Ne pas copier ce fichier dans `artifacts/onnx/`.
- ONNX Runtime 1.31 : IR ≤ 9 si graphe manuel.
- `.env` : pas de commentaire en fin de ligne.
- PyTorch + `--read-only` → `--tmpfs /tmp` (cible `runtime-pytorch` seulement).
- `AZURE_RUNTIME=true` : ne charge jamais `space_only` (CLIP).
- Deux latences EfficientNet int8 : p50 103,8 ms sur les 200 (CPU Windows) et p50 23,0 ms sur le jeu focal. Ne pas les rapprocher du 21,5 ms ResNet (it. 4). CLIP générique : p50 82,6 ms sur les 200 ; sur le focal, p50 53,3 ms et p95 82,6 ms.
- `python:3.11-slim` ne connaît pas `.webp` : `mimetypes.add_type("image/webp", ".webp")` dans `app/main.py`, sinon les vignettes partent en `text/plain`.

## Diagnostic à l’oral

Notebook formateur « Diagnostiquer les performances ». On ne le colle pas dans une page à part.

Chemin : **Parcours** → rail it. 4 (ONNX) ou it. 5 (Charge) → étape **Mesure** → rail « Parties du diagnostic », ou l’URL `/parcours?etape=mesure&partie=<id>`.

| Partie | Id | Cours | Où cliquer |
| --- | --- | --- | --- |
| Qualité | `qualite` | hors notebook | Mesure, partie 1. Accuracy 68,5 %, seuil 0,6, deux latences |
| Question | `question` | intro, §12 | Mesure |
| Modèle et CPU | `modele` | §1, §2, §2.1 | Mesure, rappel aussi à l’étape Modèle |
| Contrôle visuel | `controle` | §2 figure | Mesure, puis Studio |
| Entrées | `entrees` | §3 | Mesure, rappel à Données |
| Indicateurs | `indicateurs` | §4 | Mesure |
| Protocole | `protocole` | §5 | Mesure |
| Percentiles | `percentiles` | §5.1 | Mesure |
| Débit | `debit` | §6 | Mesure |
| Charge | `charge` | §6.1 | Mesure. Courbe HTTP 1 vCPU, pas les lots du cours |
| Mémoire | `memoire` | §7, §7.1 | Mesure |
| Chaîne | `chaine` | §8, §8.1 | Mesure, rappel à Préparation |
| Référence | `reference` | §9 | Mesure. Lien vers `/comparateur#jury-eval`. Preuve `docs/preuves/it-eval-jury.md` |
| Trace | `trace` | §9.1 | Mesure, puis Fiche |
| À retenir | `retenir` | §10 | Mesure |
| Questions | `questions` | §11 | Mesure |

Non mesuré, et marqué ainsi : top 5 de la photo COCO, tenseurs aléatoires, lots 1–16, p99 d’inférence, durée du préchauffage, prétraitement seul, pic d’allocations CPU, CSV du cours. Non applicable : synchro CUDA et pic mémoire GPU (prod CPU).

Ne pas confondre p50 inférence 21,5 ms (it. 4, 2 vCPU, `predict_proba`) et p50 requête 67,9 ms (it. 5, 1 vCPU), arrondi ~68 ms sur le studio. Ce dernier est le chiffre de facture.

## Points ouverts

- CLIP ViT-B/32 reste `space_only`. L’app du Space est une distillation ; CLIP n’y a jamais été un endpoint. L’entraînement n’a pas démarré (ancien id student en 401). Ne pas le passer à `ready`. Discours : `docs/preuves/it-eval-jury.md`.
- Student KD : id corrigé `timm/mobilenetv3_small_100.lamb_in1k` (`scripts/distill_student.py` et la copie Space). Dry-run seulement. Pas de checkpoint, pas d’ONNX. Reste `building`. La graine 64 % n’est pas un résultat.
- MobileNetV3-Small reste `building` : int8 ORT 0/8 top-1 (HardSwish), fichier écarté, pas d’accuracy int8. La graine 60 % n’est pas une mesure. Le fp32 timm fait 57,5 % (115/200) sur le proxy.
- EfficientNet-B0 int8 est mesuré : 63,5 % sur les 200 (p50 103,8 ms, CPU Windows) et 52,5 % sur le jeu focal (Véhicules 88 %, Jeux 17 %, p50 23,0 ms, autre run). Manifeste `data/test_set/focus_manifest.csv`. Sonde top-1 7/8 du 20 nov. non rejouée. Preuve : `docs/preuves/it-eval-jury.md`.
- Confirmer le student KD sur ~100 photos réelles (`data/test_set/real/`) avant d’en faire un modèle de prod. CLIP n’entre pas dans cette bascule tant que le point ci-dessus n’est pas clos.
- Exporter encodeur CLIP ONNX int8 seulement si la mesure le justifie (reste Space sinon).
- Mail formateur : ResNet pré-entraîné + CLIP en comparaison + KD légère.
