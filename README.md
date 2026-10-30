# Marketplace Vision API

**Une photo d'objet → une catégorie d'annonce, un titre suggéré et un niveau de confiance.**

Microservice de vision pour une marketplace type Leboncoin. Le vendeur prend une photo, l'API renvoie la catégorie de l'annonce en quelques dizaines de millisecondes. Quand la confiance est faible, elle propose 3 catégories au vendeur au lieu d'en imposer une. Projet Ynov, module « Industrialisation de l'IA dans le Cloud » (thème B, Marketplace).

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
  "modele": "resnet50-onnx-int8-static",
  "latence_ms": 32.1
}
```

## En chiffres

| | |
| --- | --- |
| Modèle en production | ResNet-50 (Hugging Face) exporté en ONNX, quantifié en int8 statique |
| Accuracy catégorie | 68,5 % sur 200 photos étiquetées par des tiers ; benchmark CLIP zero-shot : 76,5 à 88,5 % ([détail](docs/preuves/it8-mlflow.md)) |
| Optimisation | modèle ÷ 3,9 (97,7 → 24,9 Mo), latence p50 −80 %, −0,5 point d'accuracy |
| Image Docker | 551 Mo (contre 2,04 Go en PyTorch), prête en 1,6 s, tourne en lecture seule |
| Charge | 10 req/s pendant 5 min : p95 de 51 ms, 0 erreur ; saturation ≈ 48 req/s sur 2 vCPU |
| Coût | 1,55 à 3,05 $ pour 1 M d'images/mois sur Cloud Run, 0 $ avec l'offre gratuite ([FINOPS.md](FINOPS.md)) |

## Architecture

```
photo ─► 1 Réception ─► 2 Auth Bearer ─► 3 Validation ──────────► 4 Prétraitement ─► 5 Inférence
         multipart      vérifiée avant   type réel, ≤ 5 Mo,         224×224 (numpy)    ONNX int8
         en mémoire     lecture du corps décodable (413/415/422)                          │
                                                                                          ▼
   9 Log MLflow ◄── 8 Purge mémoire ◄── 7 Réponse JSON ◄── 6 Logique métier : 1000 classes ImageNet
   métriques seules    rien sur disque                       → 10 catégories, seuil 0,6 → auto / a_confirmer
```

```
app/
  main.py           routes FastAPI : POST /predict, GET /health, /docs
  config.py         configuration par variables d'environnement
  security.py       Bearer token + middleware de rejet avant lecture du corps (401/411/413)
  preprocessing.py  validation de l'image (type réel, taille, décodage) + prétraitement numpy
  model.py          interface Predictor : backends PyTorch (référence) et ONNX Runtime (prod)
  business.py       mapping ImageNet → catégories, score cumulé, seuil, titre, propositions
  monitoring.py     métriques de chaque requête vers MLflow (REST, asynchrone)
  categories.json   1000 classes ImageNet → 10 catégories + titres FR (généré)
scripts/
  build_categories.py  data/imagenet_mapping.tsv → app/categories.json
  build_test_set.py    jeu de test : 200 photos étiquetées (Stanford Online Products + Caltech-256)
  download_model.py    téléchargement Hugging Face (build Docker)
  export_onnx.py       export ONNX + quantization int8 dynamique et statique
  evaluate.py          accuracy, latence, balayage du seuil → MLflow
  benchmark_clip.py    benchmark CLIP zero-shot (comparaison)
  load_test.py         test de charge asyncio + httpx (paliers ou débit constant)
  deploy_cloudrun.sh   déploiement Google Cloud Run
tests/              48 tests pytest (aucun téléchargement de modèle nécessaire)
docs/               spécifications, sujet, preuves par itération, LLM Council
Dockerfile          multi-stage, cibles runtime-onnx (défaut) et runtime-pytorch
docker-compose.yml  API + serveur MLflow
FINOPS.md           estimation budgétaire
```

## Installation et lancement (≈ 10 min)

Prérequis : Python 3.11+, ~2 Go d'espace disque ; Docker en option.

```bash
git clone https://github.com/xLucasGitHubx/MarketPlace_Ynov.git && cd MarketPlace_Ynov
python -m venv .venv && source .venv/bin/activate     # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -q                                              # 48 tests, sans téléchargement

cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"   # coller la valeur dans API_TOKEN du .env
set -a; source .env; set +a                            # PowerShell : Get-Content .env | % { if ($_ -match '^(\w+)=(.*)$') { Set-Item "env:$($matches[1])" $matches[2] } }

python scripts/export_onnx.py                          # télécharge ResNet-50, exporte et quantifie (≈ 1 min)
MODEL_BACKEND=onnx uvicorn app.main:app                # Swagger : http://localhost:8000/docs
```

Dans Swagger : bouton **Authorize**, coller le token, puis `POST /predict` → *Try it out* → choisir une photo.

```bash
curl -H "Authorization: Bearer $API_TOKEN" -F file=@photo.jpg http://localhost:8000/predict
```

### Avec Docker

```bash
# Image optimisée (défaut) : ONNX Runtime int8, sans PyTorch ; le modèle est exporté au build
docker build --target runtime-onnx -t marketplace-api:onnx .
docker run -d --read-only --env-file .env -p 8000:8000 marketplace-api:onnx

# Image de référence : PyTorch fp32
docker build --target runtime-pytorch -t marketplace-api:pytorch .
docker run -d --read-only --tmpfs /tmp --env-file .env -p 8000:8000 marketplace-api:pytorch

# API + MLflow (chaque requête est journalisée) : API sur :8000, MLflow sur :5000
docker compose up -d --build
```

## API

| Endpoint | Auth | Rôle |
| --- | --- | --- |
| `POST /predict` (multipart, champ `file`) | Bearer | Catégorise la photo |
| `GET /health` | — | API et modèle chargés |
| `GET /docs` | — | Swagger |

Formats acceptés : JPEG, PNG, WebP, 5 Mo maximum. Codes d'erreur : `401` token absent ou invalide · `411` Content-Length manquant · `413` fichier trop lourd · `415` format non supporté (y compris un PDF renommé en .jpg) · `422` image illisible · `500` erreur d'inférence (sans stack trace).

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `API_TOKEN` | *(vide : tout est refusé)* | Token(s) d'accès, séparés par des virgules pour permettre une rotation |
| `MODEL_BACKEND` | `pytorch` en local, `onnx` en Docker | Modèle de référence ou optimisé |
| `ONNX_MODEL_PATH` | `models/onnx/resnet50-int8-static.onnx` | Variante ONNX (la version fp32 sert de repli) |
| `CONFIDENCE_THRESHOLD` | `0.6` | Seuil `auto` / `a_confirmer` |
| `TOP_K` | `5` | Nombre de classes cumulées pour le score de catégorie |
| `MAX_UPLOAD_MB` | `5` | Taille maximale d'une photo |
| `MLFLOW_TRACKING_URI` | *(vide : désactivé)* | Suivi des requêtes dans MLflow |
| `MODEL_CACHE_DIR`, `HF_TOKEN` | — | Cache et token Hugging Face (backend PyTorch) |

## Évaluation, MLOps et charge

```bash
python scripts/build_test_set.py                       # 200 photos étiquetées (non versionnées)
python scripts/evaluate.py --backend pytorch --mlflow
python scripts/evaluate.py --backend onnx --onnx-path models/onnx/resnet50-int8-static.onnx --mlflow
python scripts/benchmark_clip.py --mlflow
mlflow server --backend-store-uri sqlite:///mlflow.db --port 5000

python scripts/load_test.py --mode ramp --users 1,2,5,10,20,40 --step 30
python scripts/load_test.py --mode rate --rate 10 --duration 300
```

## Déploiement cloud (Google Cloud Run)

```bash
export PROJECT_ID=mon-projet-gcp
export API_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
./scripts/deploy_cloudrun.sh      # Artifact Registry + Secret Manager + Cloud Run (1 vCPU, 1 Gio, scale à zéro)
```

Le token est stocké dans Secret Manager et injecté en variable d'environnement ; il n'est jamais dans l'image. Pour la soutenance, `MIN_INSTANCES=1` supprime le démarrage à froid (≈ 13 $/mois, voir [FINOPS.md](FINOPS.md)).

## RGPD et sécurité

- L'image n'est jamais écrite sur disque : traitement en mémoire, conteneur en lecture seule, et un test vérifie qu'aucun fichier temporaire n'est créé.
- Les logs et MLflow ne contiennent rien de personnel : ni l'image, ni le nom du fichier, uniquement des métriques.
- Une requête sans token ou trop lourde est refusée avant d'être lue, ce qui protège les ressources.
- Les secrets passent par des variables d'environnement, Secret Manager ou des secrets de build Docker ; `.env` est ignoré par Git.

## Preuves par itération

| It. | Livrable | Preuve |
| --- | --- | --- |
| 1. Squelette | FastAPI + Swagger | [it1-squelette.md](docs/preuves/it1-squelette.md) |
| 2. Cerveau | ResNet-50 + logique métier | [it2-cerveau.md](docs/preuves/it2-cerveau.md) |
| 3. Isolement | Dockerfile multi-stage | [it3-docker.md](docs/preuves/it3-docker.md) |
| 4. Optimisation | ONNX int8 | [it4-optimisation.md](docs/preuves/it4-optimisation.md) |
| 5. Flux | Test de charge | [it5-charge.md](docs/preuves/it5-charge.md) |
| 6. Barrière | Token + aucune image conservée | [it6-securite.md](docs/preuves/it6-securite.md) |
| 7. Grand saut | Script Cloud Run (déploiement à lancer avec un compte GCP) | [deploy_cloudrun.sh](scripts/deploy_cloudrun.sh) |
| 8. Rétroviseur | Dashboard MLflow | [it8-mlflow.md](docs/preuves/it8-mlflow.md) |
| 9. Facture | FinOps + README | [FINOPS.md](FINOPS.md) |

Décisions d'architecture : [LLM Council](docs/llm-council/) · Spécifications : [docs/SPECIFICATIONS.md](docs/SPECIFICATIONS.md) · Sujet : [docs/SUJET.md](docs/SUJET.md)

## Limites connues

- ResNet-50 ImageNet plafonne à ~69 %, sous la cible de 80 %, car ImageNet n'a ni bouilloire électrique, ni dés, ni cartes à jouer. CLIP zero-shot fait mieux (76,5 à 88,5 % selon le vocabulaire), mais il faut le confirmer sur de vraies photos de vendeurs avant de basculer.
- Le jeu de test est un proxy public (photos eBay + Caltech-256), pas des photos Leboncoin.
- Une seule photo et un seul objet par requête (pas de détection multi-objets).
