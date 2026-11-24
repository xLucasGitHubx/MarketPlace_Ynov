# Jeu focal — Véhicules et Jeux

Jeu **séparé** de `data/test_set/manifest.csv` (200 photos, 20 × 10). Ce manifeste n'a pas été modifié : les preuves it. 2 et it. 4 restent comparables. Électroménager reste à **n = 20** dans le jeu historique ; il n'est pas dans le manifeste focal.

Graine **42**. Tirage round-robin sur les classes figées de `PLAN` (`scripts/build_test_set.py`). `data/imagenet_mapping.tsv` et `app/categories.json` n'ont pas été réajustés.

Les photos déjà listées dans le manifeste des 200 sont exclues. Aucun doublon (chemin Caltech, puis SHA-256 des octets source). Les noms commencent par `focus_caltech_` pour ne pas croiser les fichiers historiques.

## Effectifs

| Catégorie | n | Caltech test | Caltech validation | Caltech train | SOP |
| --- | ---: | ---: | ---: | ---: | ---: |
| Véhicules et pièces | 100 | 100 | 0 | 0 | 0 |
| Jeux et jouets | 100 | 44 | 52 | 4 | 0 |

Aucun écart par rapport à 100. Source : **200 Caltech-256, 0 Stanford Online Products**. Ces deux catégories n'ont aucune classe SOP dans `PLAN`.

Le split test ne laissait que 44 photos de jeux hors des 200. Le complément vient du même jeu public `ilee0022/Caltech-256` : d'abord la validation (52), puis le train (4, dont 1 dans `train0` et 3 dans `train1`).

### Classes

Véhicules et pièces (toutes du split test) : car-side-101 9, motorbikes-101 60, car-tire **0**, school-bus 7, fire-truck 9, snowmobile 7, speed-boat 3, steering-wheel 5.

`car-tire` est à 0 ici parce que les 3 images du split test sont déjà dans les 200. La catégorie atteint quand même 100 avec les autres classes du `PLAN`, sans sortir du split test.

Jeux et jouets : teddy-bear 15, chess-board 25, dice 9, playing-card 17, yo-yo 18, pez-dispenser 16.

## Fichiers

- Manifeste : `data/test_set/focus_manifest.csv` (colonnes `fichier,categorie,source,classe_source`).
- JPEG, gitignorés : `data/test_set/vehicules-et-pieces/focus_*.jpg`, `data/test_set/jeux-et-jouets/focus_*.jpg`.
- Vignettes WebP : `web/public/jeu/` (200 nouvelles, les 200 historiques sont conservées). `web/src/parcours/jeuPhotos.json` n'est pas réécrit.

```bash
python scripts/build_test_set.py --focus
python scripts/build_test_thumbnails.py --focus
```
