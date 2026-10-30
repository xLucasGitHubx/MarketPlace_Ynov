# Itération 2 — Le Cerveau : preuves

Modèle : `microsoft/resnet-50` (PyTorch fp32, CPU). Logique métier : `app/business.py` + `app/categories.json`.

## Prédictions réelles sur 4 photos d'objets différents

```
$ curl -s -F file=@sop_252045189366_0.jpg localhost:8000/predict
{
    "categorie": "Sport et loisirs",
    "titre_suggere": "Vélo",
    "confiance": 0.7205,
    "statut": "auto",
    "top3": [
        {
            "label": "bicycle-built-for-two",
            "categorie": "Sport et loisirs",
            "score": 0.6389
        },
        {
            "label": "tricycle",
            "categorie": "Jeux et jouets",
            "score": 0.1002
        },
        {
            "label": "mountain bike",
            "categorie": "Sport et loisirs",
            "score": 0.0816
        }
    ],
    "propositions": [
        {
            "categorie": "Sport et loisirs",
            "score": 0.7205,
            "titre": "Tandem"
        },
        {
            "categorie": "Jeux et jouets",
            "score": 0.1002,
            "titre": "Tricycle"
        },
        {
            "categorie": "Bricolage et jardin",
            "score": 0.0631,
            "titre": "Tondeuse à gazon"
        }
    ],
    "modele": "resnet50-pytorch-fp32",
    "latence_ms": 128.5
}
```

```
$ curl -s -F file=@sop_371404182471_0.jpg localhost:8000/predict
{
    "categorie": "Maison et meubles",
    "titre_suggere": "Canapé",
    "confiance": 0.9991,
    "statut": "auto",
    "top3": [
        {
            "label": "studio couch",
            "categorie": "Maison et meubles",
            "score": 0.9986
        },
        {
            "label": "home theater",
            "categorie": "Électronique",
            "score": 0.0002
        },
        {
            "label": "table lamp",
            "categorie": "Maison et meubles",
            "score": 0.0002
        }
    ],
    "propositions": [
        {
            "categorie": "Maison et meubles",
            "score": 0.9991,
            "titre": "Canapé"
        },
        {
            "categorie": "Électronique",
            "score": 0.0002,
            "titre": "Home cinéma"
        }
    ],
    "modele": "resnet50-pytorch-fp32",
    "latence_ms": 91.6
}
```

```
$ curl -s -F file=@caltech_laptop-101_1831.jpg localhost:8000/predict
{
    "categorie": "Électronique",
    "titre_suggere": "Ordinateur portable",
    "confiance": 0.9092,
    "statut": "auto",
    "top3": [
        {
            "label": "laptop",
            "categorie": "Électronique",
            "score": 0.3693
        },
        {
            "label": "notebook",
            "categorie": "Électronique",
            "score": 0.3281
        },
        {
            "label": "space bar",
            "categorie": "Électronique",
            "score": 0.1797
        }
    ],
    "propositions": [
        {
            "categorie": "Électronique",
            "score": 0.9092,
            "titre": "Ordinateur portable"
        }
    ],
    "modele": "resnet50-pytorch-fp32",
    "latence_ms": 102.5
}
```

```
$ curl -s -F file=@caltech_teddy-bear_2062.jpg localhost:8000/predict
{
    "categorie": "Jeux et jouets",
    "titre_suggere": "Peluche",
    "confiance": 0.9266,
    "statut": "auto",
    "top3": [
        {
            "label": "teddy",
            "categorie": "Jeux et jouets",
            "score": 0.9266
        },
        {
            "label": "overskirt",
            "categorie": "Vêtements et accessoires",
            "score": 0.008
        },
        {
            "label": "maraca",
            "categorie": "Livres et musique",
            "score": 0.0035
        }
    ],
    "propositions": [
        {
            "categorie": "Jeux et jouets",
            "score": 0.9266,
            "titre": "Peluche"
        },
        {
            "categorie": "Vêtements et accessoires",
            "score": 0.0102,
            "titre": "Surjupe"
        },
        {
            "categorie": "Livres et musique",
            "score": 0.0035,
            "titre": "Maracas"
        }
    ],
    "modele": "resnet50-pytorch-fp32",
    "latence_ms": 137.8
}
```

## Première mesure d'accuracy (jeu de test proxy, 200 photos)

Jeu construit par `scripts/build_test_set.py` : 20 photos × 10 catégories, issues de Stanford Online Products (photos d'annonces eBay) et Caltech-256, étiquetées par des tiers (voir `data/test_set/manifest.csv`). Mesure : `python scripts/evaluate.py --backend pytorch`.

| Version du mapping | Accuracy catégorie | Taux `auto` (seuil 0,6) | Précision quand `auto` | Latence p50 / p95 |
| --- | --- | --- | --- | --- |
| v1.0 (mapping initial) | 67,0 % | 77,0 % | 75,3 % | 99 / 120 ms |
| v1.1 (+18 classes oubliées, audit complet des « Autre ») | **69,0 %** | 77,5 % | 76,8 % | 102 / 120 ms |

Par catégorie (v1.1) : Véhicules 95 % · Électronique 85 % · Maison 85 % · Livres et musique 80 % · Vêtements 75 % · Autre 70 % · Sport 65 % · Électroménager 55 % · Bricolage 55 % · **Jeux et jouets 25 %**.

Le top-K du score cumulé change peu le résultat (top-1 : 69,0 % · top-3 : 68,5 % · top-5 : 69,0 % · toutes classes : 68,5 %) : on garde top-5 (spec).

**Lecture :** ResNet-50 ImageNet plafonne autour de 70 %, sous la cible de 80 %, comme anticipé par le LLM Council. Les échecs sont structurels : ImageNet n'a pas de classe « bouilloire électrique » (prédite *teapot*/*water jug* → Maison), ni « dé », « carte à jouer », « yo-yo » (Jeux et jouets à 25 %). Le mapping n'a été corrigé que pour des oublis manifestes, pas pour coller au jeu de test. Le seuil 0,6 donne 77 % de catégories pré-remplies avec 77 % de précision ; à 0,8 la précision passe à 85 % pour 60 % de pré-remplissage (arbitrage à trancher à l'itération 8).

Prochaine étape (plan du Council) : benchmark CLIP zero-shot sur le même jeu après l'itération 6.
