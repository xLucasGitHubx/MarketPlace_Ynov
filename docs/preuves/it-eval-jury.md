# Évaluation jury — discours oral

24 novembre 2026. Ce texte est celui qu’on peut tenir à l’oral. Chaque accuracy ci-dessous appartient à **un** protocole. On ne les moyenne pas.

Spec visée : accuracy de catégorie **≥ 80 %** (`docs/SPECIFICATIONS.md`). Question du professeur, ramenée à une exigence : **pouvoir dire, preuve en main, si un chiffre est pertinent.** Le catalogue mêlait une mesure (ResNet int8, 68,5 % sur 200 photos) et des graines (EfficientNet 66 %, MobileNet 60 %, student 64 %). Le Space ne produit aucun artefact. Vingt photos ne suffisent pas pour les deux catégories dont on parle. Il fallait diagnostiquer le Space et les deux modèles `building`, mesurer ce qui infère vraiment sur les mêmes photos, et comparer Véhicules et Jeux sur un jeu plus large, en chiffres et sur des photos.

## Protocole

Deux manifestes, mapping ImageNet **gelé** (`data/imagenet_mapping.tsv`, 404 classes mappées, puits **Autre = 596** classes, dont **9** vers Jeux et jouets). Le mapping n’a pas été réajusté pour faire monter un score.

| Jeu | Manifeste | Composition | Ce qu’on y mesure |
| --- | --- | --- | --- |
| Proxy historique | `data/test_set/manifest.csv` | 200 photos, 20 × 10 | ResNet int8 **historique** (fichier non relancé). EfficientNet int8 et CLIP générique **relancés** sur ces fichiers. |
| Jeu focal | `data/test_set/focus_manifest.csv` | 100 Véhicules + 100 Jeux | EfficientNet int8 et CLIP générique seulement. |

Jeu focal (`docs/preuves/eval/focus-set.md`) : graine 42, photos déjà dans les 200 exclues, noms `focus_caltech_`. **200 Caltech-256, 0 Stanford Online Products.** Véhicules : 100 images du split test (motos, bus, camions, etc.). `car-tire` est à 0 : ses 3 images de test sont déjà dans les 200. Jeux : 44 test, 52 validation, 4 train, même jeu public, pour atteindre 100 sans dupliquer. Électroménager reste au **n = 20** du proxy (indicatif).

Ce qui n’a pas tourné :

- ResNet int8 sur le jeu focal : `resnet50-int8-static.onnx` est absent de `models/onnx/`. Aucun score ResNet sur `focus_caltech_`. Le 68,5 %, le 95 % Véhicules et le 20 % Jeux restent ceux des 200.
- ResNet int8 sur les 200 : **pas une nouvelle passe**. p50 21,5 ms = machine de l’it. 4 (2 vCPU), fichier `docs/preuves/eval/eval-onnx-int8-static.json`.
- Distillation GPU. Le dry-run local a écrit `models/distill/distill_meta.json` avec `mode: dry-run`. `device_detecte: cuda` veut dire que torch voit un GPU ; aucun batch n’a été lancé.
- CLIP sur le Space. L’application `spaces/marketplace-ynov/app.py` est une distillation. CLIP n’y est pas un endpoint.
- Accuracy int8 de MobileNet, et tout ONNX student. Les graines 60 % et 64 % de `docs/preuves/eval/catalog_metrics.json` restent `estimated`.
- MLflow local : pas de serveur au moment du proxy (`compare-models-200.json`). Le JSON est la preuve.

Le champ `jeu_focal: non exécuté` dans `compare-models-200.json` date d’avant le second manifeste. Les chiffres du focal sont dans `compare-models-focus.json`.

## Chiffres — proxy, n = 200 (20 par catégorie)

Sources : `compare-models-200.json`, `eval-efficientnet-b0-int8-static-200.json`, `eval-clip-vocab-generique-200.json`, et pour ResNet `eval-onnx-int8-static.json`. Seuil métier 0,6. La catégorie vient de `suggest` (top-5 cumulé).

| Modèle | Accuracy | Véhicules n=20 | Jeux n=20 | Électroménager n=20 | p50 / p95 | Banc |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| ResNet-50 int8 | **68,5 %** | **95 %** | **20 %** | **55 %** | 21,5 / 28,6 ms | it. 4, non relancé |
| EfficientNet-B0 int8 | **63,5 %** | **90 %** | **25 %** | **50 %** | **103,8 / 120,7 ms** | ce CPU Windows, `ORT_ENABLE_BASIC` |
| CLIP ViT-B/32, vocab générique | **76,5 %** | **80 %** | **90 %** | **85 %** | **82,6 / 90,0 ms** | ce run local, 24 textes |

Accord de catégorie (même photo, même manifeste) : EfficientNet / ResNet **73,5 %** (147/200), CLIP / ResNet **60,5 %** (121/200), CLIP / EfficientNet **57 %** (114/200).

Le 76,5 % de CLIP est le zero-shot à mettre à côté du ResNet. La tâche n’est pas la même : texte contre classement ImageNet puis mapping. Le vocabulaire détaillé, **88,5 %** (`eval-clip-vocab-detaille.json`, 0,885, n = 200, 165 textes écrits en connaissant les classes du jeu), est un autre protocole. Il ne siège pas dans le tableau.

`catalog_metrics.json` porte encore le p50 CLIP historique **83,0 ms** (bench du 30 octobre, ligne CLAUDE 83 / 114 ms). Le p50 de **cette** relance est **82,6 ms**. L’accuracy, elle, est la même : 76,5 %.

Sur ce proxy, ResNet a 11 erreurs Jeux sur 16 dont la confiance dépasse 0,6 (`compare-models-200.json` ; la confiance n’est archivée que sur les 63 erreurs). Le taux `auto` historique du fichier it. 4 est 78 % (`eval-onnx-int8-static.json`). Le comparatif du 24 novembre laisse ce taux vide pour ResNet, parce que les bonnes photos n’ont pas leur confiance dans le jsonl repris.

Lecture des 20 : `docs/preuves/eval/lecture-qualitative.md` et `cas-qualitatifs.json` (13 cas). Archive. La première phrase de cette lecture dit encore que le jeu focal n’était pas prêt : elle est périmée. Les pourcentages du tableau, eux, restent ceux du proxy.

## Chiffres — jeu focal, n = 100 + 100

Sources : `compare-models-focus.json`, `eval-efficientnet-b0-int8-static-focus.json`, `eval-clip-vocab-generique-focus.json`. Même `suggest`, même seuil. **Pas de ResNet.**

| Modèle | Accuracy n=200 | Véhicules n=100 | Jeux n=100 | p50 / p95 |
| --- | ---: | ---: | ---: | --- |
| EfficientNet-B0 int8 | **52,5 %** | **88 %** | **17 %** | **23,0 / 26,2 ms** |
| CLIP générique | **62,5 %** | **44 %** | **81 %** | **53,3 / 82,6 ms** |

Le p50 focal d’EfficientNet (**23,0 ms**) est une autre exécution que les **103,8 ms** du proxy, et une autre machine que les **21,5 ms** du ResNet. Le p95 CLIP du focal est **82,6 ms** : même écriture que le p50 CLIP du proxy, autre mesure.

Accord CLIP / EfficientNet : **30,5 %** (61/200). Les deux se trompent sur **12 %** (24/200) : 7 véhicules sur 100, 17 jeux sur 100. Même catégorie : 41 % des véhicules, 20 % des jeux.

Le **80 %** CLIP Véhicules du proxy (n = 20) **ne se reporte pas** : sur ces 100 véhicules, CLIP est à **44 %**. C’est la leçon de pertinence.

Statut `auto` (confiance ≥ 0,6), pour situer le seuil, pas pour le mélanger à l’accuracy : EfficientNet taux auto 44,5 %, précision auto 84,3 % (0,8427), portée par les véhicules (précision auto Véhicules 95,65 %, Jeux 45 %). CLIP taux auto 52 %, précision auto **0,8846**. Ce 0,8846 est la précision du statut auto. Ce n’est pas les 88,5 % du vocabulaire détaillé.

Erreurs dont la confiance **dépasse** 0,6 (comparaison stricte du JSON, pas `≥`) : EfficientNet 13/95, dont 2/12 en Véhicules et **11/83 en Jeux**. CLIP 12/75, dont 7/56 en Véhicules et 5/19 en Jeux.

Dix photos commentées : `docs/preuves/eval/cas-qualitatifs-focus.json` et `lecture-qualitative-focus.md`. Elles illustrent le tableau (classe ImageNet déjà mappée, voisin vélo/moto, puits Autre, classe absente, erreur au-dessus de 0,6). Elles ne sont pas une onzième accuracy.

## Ce qu’on a le droit de conclure

La cible 80 % est manquée **pour une raison de structure**, pas parce qu’un plus gros modèle n’a pas été essayé.

- Sur le proxy, le meilleur classifieur ImageNet mesuré est le ResNet int8 à 68,5 %. EfficientNet int8, mesuré le même jour sur les mêmes 200 photos, est à 63,5 %, avec 73,5 % d’accord : même famille d’erreurs.
- Jeux et jouets ne reçoit que 9 classes ImageNet. Dé, carte, yo-yo, échiquier, Pez n’y sont pas. L’accuracy Jeux reste basse quand on passe de n = 20 (ResNet 20 %, EfficientNet 25 %) à n = 100 (EfficientNet **17 %**). CLIP, qui lit les textes `toy` et `game`, tient les jeux (90 % puis **81 %**) et lâche les véhicules dès que n = 100 (**44 %**). Le vocabulaire générique ne contient, côté véhicules, que `vehicle` et `car part` ; `bicycle` part en Sport.
- Électroménager, n = 20 seulement : ResNet 55 %, EfficientNet 50 %, CLIP 85 %. Milieu de tableau pour les deux CNN, confusions avec Maison déjà vues à l’it. 2. On ne l’extrapole pas à 100.
- Le puits Autre (596 classes) et les catégories voisines absorbent le reste. Monter le seuil ne change pas la catégorie prédite. Sur le focal, le balayage 0,3 → 0,9 d’EfficientNet est **global** : à 0,6, 44,5 % d’annonces auto et 84,3 % de précision auto ; à 0,9, 9 % d’auto et 100 % de précision auto. L’accuracy Jeux reste 17 %. Onze des 83 erreurs Jeux d’EfficientNet sont déjà au-dessus de 0,6 : ces annonces partiraient en `auto`.

Quantization, trois phrases séparées :

- ResNet : int8 statique **−0,5 point** par rapport au fp32 ONNX, 69,0 % → 68,5 %, même jeu de 200, preuve it. 4. Historique, non rejoué.
- EfficientNet : l’accuracy de catégorie mesurée ici **est** celle de l’int8 (63,5 % / 52,5 %). La fidélité top-1 face au fp32 reste la sonde déjà consignée le 20 novembre : **7/8**. Elle n’a pas été rejouée. On n’en déduit pas un écart d’accuracy fp32 → int8.
- MobileNet int8 : **écarté**. Sonde 0/8 top-1 (HardSwish), QDQ statique et dynamique. Pas d’accuracy int8. Le fp32 timm, une passe CPU sur les 200, fait **57,5 %** (115/200, `docs/preuves/it-eval-blocages.md`). C’est l’architecture, pas le fichier int8. La graine catalogue 60 % n’est pas ce chiffre.

Un fichier local `models/onnx/catalog_export_report.json` affiche encore `top1_identique: 0.0` pour `efficientnet-b0-int8-static.onnx`, avec un statut `ok`. Ce chantier **ne publie pas 0,0** comme fidélité : le script d’export actuel écarte un top-1 sous 0,5, la sonde retenue dans la mémoire du 20 novembre est 7/8, et la mesure de catégorie a tourné en `ORT_ENABLE_BASIC` (le piège `ORT_ENABLE_ALL` renvoie une classe constante).

Modèles qu’on ne défend pas par une accuracy : MobileNet int8, student KD. CLIP reste `space_only`. L’écran `/comparateur#jury-eval` (`web/src/data/jury-eval.json`) met en tête le focal (EfficientNet 88 % / 17 %, CLIP 44 % / 81 %, n = 100) et le proxy dans un second tableau. MobileNet et le student y sont **écartés**, sans accuracy. Le parcours, étape Mesure, partie Référence, lie vers cette ancre. Le bloc est un JSON statique : si l’API du port 8000 est arrêtée, le tableau catalogue peut répondre 500 ; la lecture jury ne le charge pas. La phrase d’écran « l’inférence Space ne fonctionne pas encore » est plus courte que le diagnostic ci-dessous.

## Runbook Space

1. Pousser le package Gradio `spaces/marketplace-ynov/` (`app.py`, `distill_student.py`, `requirements.txt` avec `timm`) vers **Lulu18/MarketPlaceYnov**.
2. Sur le Space, dry-run d’abord, sans quota : le JSON doit montrer `student_id` = `timm/mobilenetv3_small_100.lamb_in1k` et `student_loader` = `timm`.
3. Distillation GPU seulement si le quota du jour est libre (plafond Academia ≈ 40 min, session ≤ 35 min).
4. Si le budget coupe la session, reprendre le lendemain avec `models/distill/last.pt`.
5. Ne passer `student-kd-mobilenet-int8` à `ready` qu’une fois un ONNX contrôlé sur de vraies prédictions. Le dry-run, même avec `device_detecte: cuda`, n’est pas cette session.

Cause du blocage, déjà écrite dans `docs/preuves/it-eval-blocages.md` : l’ancien id `facebook/mobilenet_v3_small` répondait **401**. Le chargement s’arrêtait avant tout batch. Il n’y a ni `best.pt`, ni ONNX student. ZeroGPU n’a pas échoué au milieu d’une inférence : l’entraînement n’a pas démarré. L’id est corrigé dans `scripts/distill_student.py` et dans la copie vendored. Aucune distillation n’a été lancée depuis.

## Questions anticipées

**Le 88,5 % de CLIP est-il comparable au 68,5 % ?** Non : c’est le vocabulaire détaillé (165 textes, classes du jeu déjà connues) ; le chiffre à côté du ResNet est le 76,5 % du vocabulaire générique, et la tâche reste un zero-shot texte.

**Pourquoi pas 80 % ?** L’écart est localisé dans l’espace de labels (Jeux, 9 classes ImageNet, puits Autre, voisins Maison / Électroménager / Sport), et il tient quand on passe à 100 photos : EfficientNet Jeux 17 %, CLIP Véhicules 44 %.

**L’int8 a-t-il abîmé le modèle ?** Sur ResNet, −0,5 point (69,0 → 68,5), historique. Sur EfficientNet, on a l’accuracy int8 et la sonde 7/8, pas un nouvel écart fp32. L’int8 MobileNet est un échec de quantization (0/8), le fp32 à 57,5 % est une autre mesure.

**Peut-on faire confiance au comparateur ?** Le bloc `#jury-eval` recopie les deux JSON de comparaison, focal en tête et proxy à part, avec n et source ; MobileNet et le student n’y ont pas d’accuracy ; il ne dépend pas de l’API catalogue.

**Qu’est-ce qui échoue exactement sur le Space ?** L’ancien id student n’est pas un dépôt public (401), donc l’entraînement n’a jamais démarré ; l’app est une distillation, pas une inférence CLIP, et aucune session GPU n’a été lancée après le correctif.

**Le seuil 0,6 rattrape-t-il Jeux ?** Non : la catégorie fausse est déjà décidée, et 11 des 83 erreurs Jeux d’EfficientNet sur le focal dépassent 0,6, donc partiraient en `auto`.
