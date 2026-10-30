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
pytest -q
```

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
| 1. Squelette | en cours | — |
| 2. Cerveau | à faire | — |
| 3. Isolement | à faire | — |
| 6. Barrière | à faire | — |
| 4. Optimisation | à faire | — |
| 8. Rétroviseur | à faire | — |
| 5. Flux | à faire | — |
| 7. Grand saut | à faire (si possible) | — |
| 9. Facture | à faire | — |

## Points ouverts

- Lucas : créer le repo GitHub vide `xLucasGitHubx/MarketPlace_Ynov` pour passer en PR.
- Lucas : mail au formateur pour valider ResNet pré-entraîné sans fine-tuning + CLIP en comparaison.
- Lucas : photos réelles d'objets (vélo, chaise, téléphone…) pour compléter le jeu de test proxy.
