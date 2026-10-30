# Spécifications — API de catégorisation d'images Marketplace

Version de référence : 30/10/2026 (copie de travail du doc projet ; la version vivante est dans le projet claude.ai « MarketPlace_Ynov »).

## Contexte et objectif

Microservice qui, à partir d'une photo prise par un vendeur, propose la catégorie et un titre d'annonce sur une marketplace type Leboncoin. La marketplace n'est pas recréée : l'API est le produit, testée via Swagger, un script client et un test de charge.

- **Problème métier :** publier une annonce prend du temps et les vendeurs se trompent souvent de catégorie.
- **Promesse :** une photo → en moins d'une seconde une catégorie, un titre suggéré et un niveau de confiance. Confiance faible → le vendeur choisit parmi 3 propositions.

## Périmètre

| Dans le périmètre | Hors périmètre |
| --- | --- |
| `POST /predict` avec upload d'image | Site / appli marketplace |
| Pipeline : validation, prétraitement, inférence, logique métier | Entraînement / fine-tuning |
| Mapping des classes du modèle vers ~10 catégories | Détection multi-objets |
| Docker, ONNX + quantization, auth par token, purge des images | Base de données d'annonces |
| Test de charge, MLflow, déploiement cloud, FinOps | Modération de contenu |

## Pipeline (9 étapes, en mémoire, rien sur disque)

1. Réception multipart (`await file.read()`) → 2. Auth Bearer → 3. Validation (MIME réel, ≤ 5 Mo, décodable, RGB) → 4. Prétraitement 224×224 normalisé → 5. Inférence (PyTorch ou ONNX int8) + softmax → 6. Logique métier (top-5 → catégories, score cumulé, titre) → 7. Réponse JSON → 8. Purge mémoire → 9. Log MLflow (sans image).

Rejet immédiat : 401 · 413 · 415 · 422. Confiance ≥ 0,6 → `auto`, sinon `a_confirmer` (3 choix).

## Endpoints

| Endpoint | Méthode | Auth | Rôle |
| --- | --- | --- | --- |
| `/predict` | POST multipart, champ `file` | Bearer | Catégorise une image |
| `/health` | GET | — | API + modèle chargés |
| `/docs` | GET | — | Swagger |

Entrée : JPEG, PNG, WebP, 5 Mo max. Erreurs : 401 token, 413 trop lourd, 415 format, 422 illisible, 500 inférence (jamais de stack trace).

Réponse type :

```json
{
  "categorie": "Électronique",
  "titre_suggere": "Ordinateur portable",
  "confiance": 0.92,
  "statut": "auto",
  "top3": [
    {"label": "laptop", "categorie": "Électronique", "score": 0.92},
    {"label": "notebook", "categorie": "Électronique", "score": 0.05},
    {"label": "desk", "categorie": "Maison et meubles", "score": 0.01}
  ],
  "modele": "resnet50-onnx-int8",
  "latence_ms": 48
}
```

Catégories : Électronique, Maison et meubles, Électroménager, Vêtements et accessoires, Sport et loisirs, Jeux et jouets, Véhicules et pièces, Bricolage et jardin, Livres et musique, Autre.

## Stack technique

FastAPI + Uvicorn · `microsoft/resnet-50` (alternative `google/vit-base-patch16-224`) · Pillow + `AutoImageProcessor` · `optimum` + ONNX Runtime int8 dynamique · Docker `python:3.11-slim` multi-stage · Bearer token en variable d'env · Locust ou `asyncio` + `httpx` · MLflow · Google Cloud Run.

## Critères de réussite

| Domaine | Cible |
| --- | --- |
| Accuracy catégorie | ≥ 80 % sur jeu de test (100 photos) |
| Entrées invalides | 100 % des cas d'erreur renvoient le bon code (pytest) |
| Portabilité | `docker run` fonctionne du premier coup |
| Optimisation | Taille ÷ 3, latence CPU −40 %, perte d'accuracy ≤ 2 pts |
| Performance | p95 < 500 ms en local à 10 req/s |
| Robustesse | < 1 % d'erreurs sur 5 min de charge |
| Sécurité | 401 systématique sans token valide |
| RGPD | 0 fichier image sur disque, aucun contenu dans les logs |
| Cloud | URL publique fonctionnelle |
| MLOps | ≥ 2 runs MLflow (accuracy, latence, taille) |
| FinOps | Coût mensuel pour 1 M images, hypothèses explicites |
| Documentation | Un tiers relance le projet en < 15 min |

## MVP

P0 : it. 1, 2, 3, 6, 9 · P1 : it. 4, 8 · P2 : it. 5, 7. Ordre : 1 → 2 → 3 → 6 → 4 → 8 → 5 → 7 → 9. Non négociable : logique métier visible (catégorie + seuil), pas juste le label ImageNet brut.

## Risques principaux

ImageNet colle mal aux catégories (→ mapping soigné, seuil, `a_confirmer`, mesure) · pas de jeu de test étiqueté · image Docker trop lourde (→ ONNX Runtime seul en prod) · cold start Cloud Run · quantization qui dégrade (→ repli ONNX fp32) · secret commité · réseau absent le jour J (→ vidéo + Docker local).
