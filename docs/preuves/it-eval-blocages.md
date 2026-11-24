# Blocages Space et modèles `building`

Note d’Agent A, 24 novembre 2026. Aucun modèle n’est passé à `ready`. Le registre (`app/registry.py`) n’est pas modifié : les graines 60 % (MobileNet) et 64 % (student) restent des estimations.

## Student retenu

Identifiant : `timm/mobilenetv3_small_100.lamb_in1k`.  
Nom timm : `mobilenetv3_small_100.lamb_in1k`.  
Teacher inchangé : `microsoft/resnet-50`.

Il charge. `timm.create_model(..., pretrained=True)` sur CPU donne `num_classes = 1000` et des logits `(1, 1000)`. Moyenne / écart-type ImageNet : `(0,485, 0,456, 0,406)` / `(0,229, 0,224, 0,225)`, les mêmes que le prétraitement du runtime.

`transformers.AutoConfig` refuse ce dépôt : le `config.json` du Hub n’a pas de clé `model_type` (`Unrecognized model`). `facebook/mobilenet_v3_small` répond **401**. Les deux scripts chargent donc le student avec timm, et le teacher avec `AutoModelForImageClassification`.

La KL est sur le même espace. Les 1000 descriptions timm (`index_to_description`) sont identiques, indice par indice, à l’`id2label` de `microsoft/resnet-50` (0 écart). Ce n’est pas un entraînement : aucun forward teacher/student n’a été lancé pour la distillation.

Fichiers alignés : `scripts/distill_student.py`, `spaces/marketplace-ynov/distill_student.py`. Le package Gradio affiche le même id (`app.py`) et déclare `timm` dans `requirements.txt`, sinon le Space ne pourrait pas charger le student.

## Dry-run

Commande, sans entraînement :

```bash
python scripts/distill_student.py --dry-run
```

Le processus n’a pas chargé de poids et n’a pas écrit de `.pt` ni de `.onnx` student. Seul `models/distill/distill_meta.json` a été écrit (dossier `models/` ignoré par git, `mode` = `dry-run`). `device_detecte` vaut `cuda` parce que torch voit un GPU sur cette machine : ce champ ne lance rien.

Plan imprimé :

- teacher `microsoft/resnet-50` (transformers), student `timm/mobilenetv3_small_100.lamb_in1k` (timm), 1000 logits
- epochs 2, batch 32, lr 3e-4, température 4, poids CE 0,1, 3000 images, graine 42, 35 min, images 224
- artefacts attendus, pas encore produits : `models/distill/last.pt`, `best.pt`, `models/onnx/student-kd-mobilenet-fp32.onnx`, `student-kd-mobilenet-int8-static.onnx` (+ alias)
- catalogue visé : `student-kd-mobilenet-int8`
- budget ZeroGPU : plafond 40 min/jour, session 35 min, Space Lulu18

## Pourquoi l’inférence ZeroGPU n’a pas démarré

Trois faits, indépendants du correctif d’identifiant :

1. L’ancien student `facebook/mobilenet_v3_small` n’est pas un dépôt public (401). Le chargement transformers échouait avant tout batch.
2. Il n’y a ni `best.pt`, ni `last.pt`, ni ONNX student. Rien à exporter, rien à servir.
3. L’application du Space (`spaces/marketplace-ynov/app.py`) est une distillation ResNet → MobileNet. Elle n’a pas de chemin d’inférence photo → catégorie, et pas de code CLIP.

Corriger l’id rend un futur lancement possible. Ce n’est pas une session GPU déjà faite.

## Pourquoi CLIP reste `space_only`

CLIP n’existe ici que dans le bench local `scripts/benchmark_clip.py`. Le Space ne l’exécute pas. L’API Azure ne charge pas les modèles `space_only`.

Les deux chiffres ne sont pas le même protocole (preuve it. 8) :

| Protocole | Accuracy catégorie |
| --- | --- |
| Vocabulaire générique (25 descriptions) | **76,5 %** |
| Vocabulaire détaillé (165 objets, écrit en connaissant les classes du jeu) | **88,5 %** |

Le 88,5 % est une borne optimiste. Le chiffre à mettre à côté du ResNet int8 (68,5 %, classement ImageNet + mapping) est le **76,5 %**, avec l’écart de tâche écrit : zero-shot texte, pas le même classifieur. On ne passe pas CLIP à `ready`.

## Pourquoi MobileNet int8 reste `building`

Le fp32 timm `mobilenetv3_small_100.lamb_in1k` se charge et prédit. L’int8 ONNX Runtime, QDQ statique et dynamique, a fait **0/8 top-1** face à ce fp32 (HardSwish). `scripts/export_catalog.py` supprime le fichier si l’accord top-1 de la sonde est sous 0,5, puis lève une erreur. Cette session n’a pas relancé de quantization.

Un fichier `models/onnx/mobilenet-v3-small-int8-static.onnx` peut être présent en local (hors git). Il n’a pas été réévalué ici. Ce n’est pas un artefact livré, et il ne doit pas être copié dans `artifacts/onnx/`.

La graine catalogue 60 % reste une estimation. Le modèle reste `building`.

### fp32 sur les 200 photos (une passe, CPU)

torch et timm étaient déjà installés. Les 200 JPEG de `data/test_set/manifest.csv` étaient lisibles (aucun manquant, 4 Ko à 660 Ko). Une seule passe, CPU, sans int8 :

- modèle : `timm/mobilenetv3_small_100.lamb_in1k` fp32
- même `to_model_input` et même `suggest()` que l’évaluation (top-5 ; le seuil 0,6 ne change pas la catégorie)
- **115 / 200 = 57,5 %** d’accuracy catégorie

| Catégorie | Correct | n |
| --- | --- | --- |
| Autre | 14 | 20 |
| Bricolage et jardin | 6 | 20 |
| Jeux et jouets | 3 | 20 |
| Livres et musique | 12 | 20 |
| Maison et meubles | 17 | 20 |
| Sport et loisirs | 11 | 20 |
| Véhicules et pièces | 15 | 20 |
| Vêtements et accessoires | 11 | 20 |
| Électroménager | 9 | 20 |
| Électronique | 17 | 20 |

Lecture : l’architecture fp32 est en dessous du ResNet int8 (68,5 % sur le même type de jeu), elle n’est pas à zéro. L’int8 à 0/8 est une quantization cassée, pas ce 57,5 %. Le 57,5 % ne remplace pas la graine 60 % du registre et ne qualifie pas un fichier int8.

## Pourquoi le student reste `building`

Aucun ONNX student ne prédit. Le dry-run ne crée pas de checkpoint. Le statut ne bouge qu’avec un int8 qui prédit vraiment, après une distillation réelle. Le précédent HardSwish interdit de supposer que la quantization du student réussira le jour où les poids existeront.

## Runbook Space

1. Pousser le package `spaces/marketplace-ynov/` (dont `distill_student.py`, `app.py`, `requirements.txt` avec `timm`) vers **Lulu18/MarketPlaceYnov**.
2. Sur le Space, **dry-run d’abord** (l’UI, sans consommer le quota). Le JSON doit montrer `student_id` = `timm/mobilenetv3_small_100.lamb_in1k` et `student_loader` = `timm`.
3. **Distillation GPU seulement si le quota du jour est libre** (plafond Academia ≈ 40 min, session ≤ 35 min). Reprise le lendemain via `last.pt` si le budget coupe la session.
4. Ne pas passer `student-kd-mobilenet-int8` ni `mobilenet-v3-small-onnx-int8` à `ready` tant qu’un ONNX n’a pas été contrôlé sur de vraies prédictions.

## Ce que la synthèse ne doit pas affirmer

- Que la distillation a tourné, qu’un checkpoint existe, ou que le Space infère.
- Que CLIP est mesuré sur le Space, ou que 88,5 % est comparable à 76,5 % ou à 68,5 %.
- Que le MobileNet int8 a une accuracy (la graine 60 % n’est pas une mesure ; le 57,5 % est le **fp32**, n = 200).
- Que le student vaut 64 %, ou qu’il est `ready`.
- Que l’int8 du student marchera (même famille HardSwish que le MobileNet écarté).
- Que `device_detecte: cuda` du dry-run est une session GPU.
- Un chiffre EfficientNet : hors de cette note.
