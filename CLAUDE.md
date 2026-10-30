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
python scripts/evaluate.py --backend onnx --onnx-path models/onnx/resnet50-int8-static.onnx --mlflow
python scripts/benchmark_clip.py [--vocab generique] --mlflow   # benchmark CLIP zero-shot
mlflow server --backend-store-uri sqlite:///mlflow.db --port 5000
docker compose up -d --build                         # API (ONNX) + MLflow ; requêtes journalisées
python scripts/load_test.py --mode rate --rate 10 --duration 300   # test de charge (critère spec)
API_TOKEN=... ./scripts/deploy_azure.sh             # déploiement Azure Container Apps (depuis Azure Cloud Shell)
```

Variables utiles : `API_TOKEN` (obligatoire, sinon 401 partout), `MODEL_BACKEND` (pytorch|onnx), `ONNX_MODEL_PATH` (défaut `models/onnx/resnet50-int8-static.onnx`), `MODEL_CACHE_DIR` (cache HF, ex. `models/hf`), `CONFIDENCE_THRESHOLD`, `TOP_K`, `HF_TOKEN`, `MLFLOW_TRACKING_URI` (vide = suivi désactivé ; http(s) = REST sans dépendance).

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
.github/workflows/ci.yml  # tests + build/push image ONNX sur GHCR + smoke test
scripts/deploy_azure.sh   # déploiement Azure Container Apps
```

## Décisions structurantes

| Date | Décision | Source |
| --- | --- | --- |
| 2026-10-30 | Cloud = **Azure Container Apps** (crédit Azure for Students de Lucas) au lieu de Cloud Run. Image construite par GitHub Actions et publiée sur GHCR (ACR Tasks bloqué sur les abonnements étudiants, ACR Basic ≈ 5 $/mois). Dockerfile sans syntaxe BuildKit (portable). | demande de Lucas |
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
| 8. Rétroviseur | ✅ fait | `docs/preuves/it8-mlflow.md` — 6 runs comparés + suivi de chaque requête API |
| 5. Flux | ✅ fait | `docs/preuves/it5-charge.md` — p95 51 ms à 10 req/s / 5 min, 0 erreur ; 23 req/s par vCPU |
| 7. Grand saut | 🟡 script prêt | `scripts/deploy_azure.sh` + CI GHCR — à lancer par Lucas (Azure for Students) |
| 9. Facture | ✅ fait | `FINOPS.md` (Azure : 0 $ en phase projet, ≈ 25 $/mois à 1 M images) + `README.md` final |

## Mesures clés

| Date | Modèle | Accuracy (200 photos) | p50 / p95 CPU | Note |
| --- | --- | --- | --- | --- |
| 2026-10-30 | resnet50-pytorch-fp32, mapping v1.1 | 69,0 % | 105 / 142 ms | Jeux et jouets 25 %, Électroménager 55 % (pas de bouilloire dans ImageNet) |
| 2026-10-30 | resnet50-onnx-fp32 | 69,0 % | 56 / 73 ms | export seul : latence ÷2 |
| 2026-10-30 | resnet50-onnx-int8-dynamic | 62,0 % | 359 / 443 ms | piège : ConvInteger lent sur CPU |
| 2026-10-30 | **resnet50-onnx-int8-static** (prod) | 68,5 % | 21,5 / 28,6 ms | 24,9 Mo, image Docker 551 Mo |
| 2026-10-30 | clip-vit-b32 zero-shot, vocab détaillé | 88,5 % | 88 / 122 ms | 577 Mo ; borne optimiste (vocab écrit en connaissant les classes sources) |
| 2026-10-30 | clip-vit-b32 zero-shot, vocab générique | 76,5 % | 83 / 114 ms | contrôle « aveugle » |

## Pièges connus

- Tester l'API sans `with TestClient(app)` : le lifespan (chargement du modèle) ne tourne pas, on injecte `app.state.predictor` (voir `tests/conftest.py`).
- Ne jamais ajuster `data/imagenet_mapping.tsv` en regardant les erreurs du jeu de test (surapprentissage du mapping) : seulement des oublis manifestes, documentés.
- Docker Hub peut renvoyer 429 (rate limit) : tirer `mirror.gcr.io/library/python:3.11-slim` puis `docker tag` en `python:3.11-slim`, ou `--build-arg BASE_IMAGE=...`.
- Derrière un proxy TLS : `docker build --network host --build-arg EXTRA_CA_CERT_B64="$(base64 -w0 proxy-ca.pem)" ...` (le bundle complet dépasse la limite de 128 Ko d'un argument : ne passer que le CA du proxy).
- Azure for Students : pas d'ACR Tasks (`TasksOperationsNotAllowed`), régions limitées par policy (`RequestDisallowedByPolicy`).
- Container Apps : une réplique à `min=0` reste facturée au tarif actif 300 s après la dernière requête ; à trafic continu, `min=1` (tarif repos) coûte moins cher.
- Starlette écrit sur disque les uploads > 1 Mo (SpooledTemporaryFile) : réglé par `keep_uploads_in_memory()` dans `app/security.py` ; ne pas retirer.
- Les tests fixent `API_TOKEN` dans `tests/conftest.py` AVANT d'importer l'app (Settings en cache).
- Quantization dynamique = mauvaise idée pour un CNN (ConvInteger) : utiliser la statique QDQ calibrée hors jeu de test.
- ONNX Runtime 1.31 refuse les modèles IR v14 (onnx 1.23 par défaut) : forcer `ir_version=9` si on construit un graphe à la main.
- MLflow 3.x : l'UI s'ouvre en mode « GenAI » ; basculer sur « Model training » pour voir les runs. `mlflow server` exige `--allowed-hosts` pour être joint par un autre conteneur.
- `pkill -f "uvicorn app.main"` dans un shell tue aussi le shell (le motif apparaît dans sa ligne de commande) : tuer par PID.
- `.env` : jamais de commentaire en fin de ligne (`docker --env-file` les garde dans la valeur).
- Mesures de latence : ±20 % d'une session à l'autre sur la machine de dev partagée ; comparer des runs d'une même session.
- PyTorch a besoin d'un `/tmp` inscriptible au démarrage : `--read-only` doit s'accompagner de `--tmpfs /tmp`.

## Décision en attente (Lucas)

- **Basculer sur CLIP ?** CLIP zero-shot dépasse 80 % avec le vocabulaire détaillé (88,5 %) mais ce chiffre est optimiste ; le contrôle « aveugle » donne 76,5 %. Avant de basculer : mesurer sur ~100 photos réelles indépendantes (`data/test_set/real/`), puis exporter l'encodeur image CLIP en ONNX int8. Tant que ce n'est pas tranché, ResNet-50 int8 reste en production.

## Points ouverts

- Lucas : créer le repo GitHub vide `xLucasGitHubx/MarketPlace_Ynov` → pousser `main` + branches, passer en PR pour la suite.
- Lucas : lancer `scripts/deploy_azure.sh` depuis Azure Cloud Shell (it. 7), puis ajouter l'URL publique au README et à `docs/preuves/it7-azure.md`.
- Lucas : mail au formateur pour valider ResNet pré-entraîné sans fine-tuning + CLIP en comparaison.
- Lucas : photos réelles d'objets (vélo, chaise, téléphone…) pour compléter le jeu de test proxy.
