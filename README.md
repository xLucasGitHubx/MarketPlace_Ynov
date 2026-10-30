# Marketplace Vision API

Une photo d'objet → une catégorie d'annonce, un titre suggéré et un niveau de confiance. Projet Ynov « Industrialisation de l'IA dans le Cloud » (thème Marketplace).

> README en construction : il est complété à chaque itération (preuves, commandes, chiffres).

## Démarrage rapide

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Swagger : http://localhost:8000/docs

## Documentation

- [Spécifications](docs/SPECIFICATIONS.md)
- [Sujet](docs/SUJET.md)
- [Décisions (LLM Council)](docs/llm-council/)
