# Marketplace Vision API

Une photo d'objet → une catégorie d'annonce, un titre suggéré et un niveau de confiance. Projet Ynov « Industrialisation de l'IA dans le Cloud » (thème Marketplace).

> README en construction : il est complété à chaque itération (preuves, commandes, chiffres).

## Démarrage rapide

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env        # puis mettre un vrai API_TOKEN
export $(grep -v '^#' .env | xargs)   # ou : set -a; source .env; set +a
uvicorn app.main:app --reload
```

Swagger : http://localhost:8000/docs (bouton « Authorize » → coller le token).

```bash
curl -H "Authorization: Bearer $API_TOKEN" -F file=@photo.jpg http://localhost:8000/predict
```

## Docker

```bash
# Image optimisée (défaut) : ONNX Runtime int8, 551 Mo, sans PyTorch
docker build --target runtime-onnx -t marketplace-api:onnx .
docker run -d --read-only --env-file .env -p 8000:8000 marketplace-api:onnx

# Image de référence : PyTorch fp32, 2 Go
docker build --target runtime-pytorch -t marketplace-api:pytorch .
docker run -d --read-only --tmpfs /tmp --env-file .env -p 8000:8000 marketplace-api:pytorch
```

Le modèle est téléchargé (et, pour ONNX, exporté puis quantifié) au build : le conteneur démarre hors-ligne.

## MLflow

```bash
docker compose up -d --build     # API ONNX sur :8000 + MLflow sur :5000 (chaque requête est journalisée)
python scripts/evaluate.py --backend onnx --onnx-path models/onnx/resnet50-int8-static.onnx --mlflow
```

## Documentation

- [Spécifications](docs/SPECIFICATIONS.md)
- [Sujet](docs/SUJET.md)
- [Décisions (LLM Council)](docs/llm-council/)
