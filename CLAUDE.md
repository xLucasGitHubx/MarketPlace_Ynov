# CLAUDE.md — MarketPlace_Ynov

Mémoire de travail du projet pour Claude Code. À tenir à jour à chaque itération.

## Le projet en une phrase

API FastAPI qui reçoit la photo d'un objet prise par un vendeur et renvoie une catégorie d'annonce (type Leboncoin), un titre suggéré, une confiance et un statut `auto` / `a_confirmer`. Projet Ynov, module « Industrialisation de l'IA dans le Cloud », 9 itérations. On industrialise un modèle pré-entraîné : pas d'entraînement, pas de front.

Specs de référence : `docs/SPECIFICATIONS.md`. Consignes du sujet : `docs/SUJET.md`.

## Conventions

- Langue : code en anglais (noms de fonctions/variables), messages d'API, docs et commits en français.
- Commits petits et fréquents, format `type(scope): message` (`feat`, `fix`, `test`, `docs`, `chore`, `perf`, `ci`).
- Une branche par itération `feat/itX-nom`, mergée dans `main` en `--no-ff` (ou PR GitHub quand le remote existe).
- Aucun secret dans le code : tout passe par l'environnement (`.env`, jamais committé ; `.env.example` versionné).
- Aucune image écrite sur disque : traitement 100 % en mémoire (`await file.read()`), jamais de log du contenu.
- Les modèles (`models/`, `*.onnx`) ne sont pas versionnés : ils sont régénérés par `scripts/`.

## Commandes

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload                        # Swagger : http://localhost:8000/docs
pytest -q                                            # tests rapides (faux modèle, pas de téléchargement)

python scripts/build_categories.py                   # régénère app/categories.json depuis data/imagenet_mapping.tsv
python scripts/build_test_set.py                     # télécharge le jeu de test proxy (200 photos, non versionnées)
python scripts/evaluate.py --backend pytorch         # accuracy + latence + balayage du seuil
python scripts/export_onnx.py                        # export ONNX fp32 + int8 dynamique + int8 statique (models/onnx/)
python scripts/evaluate.py --backend onnx --onnx-path models/onnx/resnet50-int8-static.onnx
```

Variables utiles : `API_TOKEN` (obligatoire, sinon 401 partout), `MODEL_BACKEND` (pytorch|onnx), `ONNX_MODEL_PATH` (défaut `models/onnx/resnet50-int8-static.onnx`), `MODEL_CACHE_DIR` (cache HF, ex. `models/hf`), `CONFIDENCE_THRESHOLD`, `TOP_K`, `HF_TOKEN`.

## Architecture

```
app/
  main.py          # routes FastAPI (/predict, /health, /docs)
  config.py        # Settings depuis l'environnement
  schemas.py       # modèles Pydantic des réponses
  preprocessing.py # validation (MIME réel, taille, décodage) + RGB
  model.py         # interface Predictor + backends (pytorch, onnx)
  business.py      # mapping ImageNet → catégories, seuil, titre
  security.py      # Bearer token
  categories.json  # mapping des 1000 classes ImageNet vers 10 catégories
scripts/           # export_onnx.py, evaluate.py, load_test.py
tests/             # pytest
docs/llm-council/  # rapports et transcripts des LLM Council (décisions structurantes)
```

## Décisions structurantes

| Date | Décision | Source |
| --- | --- | --- |
| 2026-10-30 | ResNet-50 = chemin de production (it. 1→6). Interface `Predictor` commune pour brancher CLIP plus tard. Seuil de confiance par backend. Accuracy mesurée dès l'it. 2 sur un jeu proxy public. CLIP = benchmark séparé, principal seulement si la mesure le justifie. | `docs/llm-council/council-transcript-2026-10-30-modele.md` |

## Avancement des itérations

Ordre MVP : 1 → 2 → 3 → 6 → 4 → 8 → 5 → 7 → 9.

| It. | Statut | Preuve |
| --- | --- | --- |
| 1. Squelette | ✅ fait | `docs/preuves/it1-squelette.md` |
| 2. Cerveau | ✅ fait | `docs/preuves/it2-cerveau.md` — accuracy 69 % (ResNet-50, 200 photos) |
| 3. Isolement | ✅ fait | `docs/preuves/it3-docker.md` — image PyTorch 2,04 Go |
| 6. Barrière | ✅ fait | `docs/preuves/it6-securite.md` — 401, conteneur `--read-only`, 0 image écrite |
| 4. Optimisation | ✅ fait | `docs/preuves/it4-optimisation.md` — int8 statique : ÷3,9 taille, −80 % latence, −0,5 pt |
| 8. Rétroviseur | à faire | — |
| 5. Flux | à faire | — |
| 7. Grand saut | à faire (si possible) | — |
| 9. Facture | à faire | — |

## Mesures clés

| Date | Modèle | Accuracy (200 photos) | p50 / p95 CPU | Note |
| --- | --- | --- | --- | --- |
| 2026-10-30 | resnet50-pytorch-fp32, mapping v1.1 | 69,0 % | 105 / 142 ms | Jeux et jouets 25 %, Électroménager 55 % (pas de bouilloire dans ImageNet) |
| 2026-10-30 | resnet50-onnx-fp32 | 69,0 % | 56 / 73 ms | export seul : latence ÷2 |
| 2026-10-30 | resnet50-onnx-int8-dynamic | 62,0 % | 359 / 443 ms | piège : ConvInteger lent sur CPU |
| 2026-10-30 | **resnet50-onnx-int8-static** (prod) | 68,5 % | 21,5 / 28,6 ms | 24,9 Mo, image Docker 551 Mo |

## Pièges connus

- Tester l'API sans `with TestClient(app)` : le lifespan (chargement du modèle) ne tourne pas, on injecte `app.state.predictor` (voir `tests/conftest.py`).
- Ne jamais ajuster `data/imagenet_mapping.tsv` en regardant les erreurs du jeu de test (surapprentissage du mapping) : seulement des oublis manifestes, documentés.
- Docker Hub peut renvoyer 429 (rate limit) : tirer `mirror.gcr.io/library/python:3.11-slim` puis `docker tag` en `python:3.11-slim`, ou `--build-arg BASE_IMAGE=...`.
- Derrière un proxy TLS : `docker build --network host --secret id=ca_bundle,src=<ca.crt> ...`.
- Starlette écrit sur disque les uploads > 1 Mo (SpooledTemporaryFile) : réglé par `keep_uploads_in_memory()` dans `app/security.py` ; ne pas retirer.
- Les tests fixent `API_TOKEN` dans `tests/conftest.py` AVANT d'importer l'app (Settings en cache).
- Quantization dynamique = mauvaise idée pour un CNN (ConvInteger) : utiliser la statique QDQ calibrée hors jeu de test.
- ONNX Runtime 1.31 refuse les modèles IR v14 (onnx 1.23 par défaut) : forcer `ir_version=9` si on construit un graphe à la main.
- PyTorch a besoin d'un `/tmp` inscriptible au démarrage : `--read-only` doit s'accompagner de `--tmpfs /tmp`.

## Points ouverts

- Lucas : créer le repo GitHub vide `xLucasGitHubx/MarketPlace_Ynov` pour passer en PR.
- Lucas : mail au formateur pour valider ResNet pré-entraîné sans fine-tuning + CLIP en comparaison.
- Lucas : photos réelles d'objets (vélo, chaise, téléphone…) pour compléter le jeu de test proxy.
