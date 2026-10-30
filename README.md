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
docker build -t marketplace-api:pytorch .
docker run -d --read-only --tmpfs /tmp --env-file .env -p 8000:8000 marketplace-api:pytorch
```

Le modèle est téléchargé au build : le conteneur démarre hors-ligne.

## Documentation

- [Spécifications](docs/SPECIFICATIONS.md)
- [Sujet](docs/SUJET.md)
- [Décisions (LLM Council)](docs/llm-council/)
