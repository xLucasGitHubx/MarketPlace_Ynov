# Lecture qualitative — jeu focal Véhicules et Jeux

Ces dix cas commentent des lignes déjà mesurées sur le jeu focal (`focus_manifest.csv`, 100 Véhicules + 100 Jeux, photos `focus_caltech_`, séparées des 200 historiques). La lecture est illustrative : elle n'est pas une nouvelle accuracy. Le mapping `data/imagenet_mapping.tsv` n'a pas été modifié. Ce jeu ne contient aucune image SOP. `car-tire` est absent : ses 3 images du split test sont déjà dans les 200.

Chiffres de cadrage, recopiés de `compare-models-focus.json`. On ne les recalcule pas à partir de ces cas.

| Modèle | Accuracy (n=200) | Véhicules (n=100) | Jeux (n=100) | taux_auto | précision auto |
| --- | ---: | ---: | ---: | ---: | ---: |
| EfficientNet-B0 int8 | 52,5 % | 88 % | 17 % | 44,5 % | 84,3 % |
| CLIP ViT-B/32, vocabulaire générique | 62,5 % | 44 % | 81 % | 52 % | 88,5 % |

Détail auto par catégorie, même fichier : EfficientNet Véhicules 69 % d'auto et 95,65 % de précision auto, Jeux 20 % et 45 %. CLIP Véhicules 36 % et 80,56 %, Jeux 68 % et **92,7 %**. La précision auto globale d'EfficientNet (84,3 %) est portée par les véhicules.

Accord de catégorie CLIP / EfficientNet : **30,5 %** (61/200). Les deux se trompent sur **12 %** des photos (24/200). Même catégorie sur Véhicules : 41 %. Même catégorie sur Jeux : 20 %. Les deux faux : 7 véhicules sur 100, 17 jeux sur 100.

**Le 80 % de CLIP sur Véhicules mesure les 20 photos de l'autre jeu.** Sur les 100 véhicules de ce jeu focal, CLIP est à **44 %**. Ce 80 % ne se reporte pas, et on ne le défend pas comme résultat d'ici.

ResNet-50 int8 n'a pas été relancé : le fichier onnx est absent de ce jeu. Aucune prédiction ResNet n'est donnée pour ces photos. Le 68,5 % global, le 95 % Véhicules et le 20 % Jeux appartiennent aux 200 photos historiques seulement.

La confiance est le score de catégorie cumulé sur le top-5 (`suggest`). Le seuil métier est 0,6 (`auto` si confiance ≥ 0,6). Le top-1 EfficientNet est une classe ImageNet. Le top-1 CLIP est un libellé des 24 textes du vocabulaire générique : côté Véhicules, seulement `vehicle` et `car part` ; `bicycle` est rangé en Sport. Le détail machine est dans `cas-qualitatifs-focus.json`.

## Accord

La catégorie rendue est la même, et c'est la bonne. Cela arrive quand ImageNet a déjà la classe (bus, peluche) et que le texte générique de CLIP tombe du même côté. L'accord global n'est que de 30,5 % : ces photos montrent le cas favorable, pas la moyenne.

### Bus scolaire

- Fichier : `vehicules-et-pieces/focus_caltech_test_school-bus_150.jpg`
- Vignette : `web/public/jeu/vehicules-et-pieces/focus_caltech_test_school-bus_150.webp`
- Attendu : Véhicules et pièces
- EfficientNet int8 : Véhicules et pièces, 0,912, top-1 ImageNet `school bus`, auto.
- CLIP générique : Véhicules et pièces, 0,971, texte `vehicle`, auto.

Le bus scolaire est une classe ImageNet, school bus, déjà mappée vers Véhicules et pièces. Sur cette photo du jeu focal, EfficientNet la lit à 0,912 (auto) et CLIP, vocabulaire générique, lit vehicle à 0,971 (auto) : les deux rendent la bonne catégorie. ResNet n'a pas été relancé sur ce jeu, donc cette photo n'a pas de score ResNet.

### Peluche

- Fichier : `jeux-et-jouets/focus_caltech_test_teddy-bear_1630.jpg`
- Vignette : `web/public/jeu/jeux-et-jouets/focus_caltech_test_teddy-bear_1630.webp`
- Attendu : Jeux et jouets
- EfficientNet int8 : Jeux et jouets, 0,762, top-1 ImageNet `teddy`, auto.
- CLIP générique : Jeux et jouets, 0,871, texte `toy`, auto.

teddy est l'une des neuf classes ImageNet mappées vers Jeux et jouets, et le mapping n'a pas été étendu. EfficientNet lit teddy à 0,762 (auto) et CLIP lit toy à 0,871 (auto) : les deux rendent Jeux. C'est le cas où la classe existe déjà ; l'accuracy Jeux d'EfficientNet sur ce jeu reste 17 %.

## Désaccord des modèles

Les deux modèles rendent une catégorie différente, ici tous les deux en auto. Sur l'ensemble du jeu focal ils divergent sur 139 photos sur 200. Le motif du n=100 : EfficientNet tient les véhicules (88 %), CLIP tient les jeux (81 %).

### Motoneige lue comme un jeu

- Fichier : `vehicules-et-pieces/focus_caltech_test_snowmobile_233.jpg`
- Vignette : `web/public/jeu/vehicules-et-pieces/focus_caltech_test_snowmobile_233.webp`
- Attendu : Véhicules et pièces
- EfficientNet int8 : Véhicules et pièces, 0,727, top-1 ImageNet `snowmobile`, auto.
- CLIP générique : Jeux et jouets, 0,604, texte `game`, auto.

La motoneige est dans le mapping, sous le nom snowmobile : EfficientNet la rend en Véhicules à 0,727 (auto). CLIP lit game et rend Jeux et jouets à 0,604, donc auto aussi, mais faux. Les deux modèles dépassent 0,6 sans s'accorder ; 17 des 100 véhicules partent ainsi vers Jeux chez CLIP.

## Confusion voisine

La classe retenue existe, et elle est proche de l'objet : un vélo pour une moto, un paillasson pour un échiquier. Sur les 100 véhicules, 37 erreurs CLIP vont vers Sport. Sur les 100 jeux, 35 prédictions EfficientNet tombent dans Maison.

### Moto lue comme un vélo

- Fichier : `vehicules-et-pieces/focus_caltech_test_motorbikes-101_1395.jpg`
- Vignette : `web/public/jeu/vehicules-et-pieces/focus_caltech_test_motorbikes-101_1395.webp`
- Attendu : Véhicules et pièces
- EfficientNet int8 : Véhicules et pièces, 0,823, top-1 ImageNet `moped`, auto.
- CLIP générique : Sport et loisirs, 0,654, texte `bicycle`, auto.

La moto est lue moped par EfficientNet, classe mappée vers Véhicules, à 0,823 (auto). Le vocabulaire générique de CLIP place bicycle en Sport et loisirs, et vehicle ou car part sont ses seuls textes Véhicules : ici bicycle sort à 0,654 (auto). EfficientNet a raison et CLIP se trompe vers le voisin, au-dessus du seuil 0,6 ; 37 des 100 véhicules vont vers Sport chez CLIP.

### Moto, les deux du côté du vélo

- Fichier : `vehicules-et-pieces/focus_caltech_test_motorbikes-101_1268.jpg`
- Vignette : `web/public/jeu/vehicules-et-pieces/focus_caltech_test_motorbikes-101_1268.webp`
- Attendu : Véhicules et pièces
- EfficientNet int8 : Sport et loisirs, 0,637, top-1 ImageNet `bicycle-built-for-two`, auto.
- CLIP générique : Sport et loisirs, 0,481, texte `bicycle`, à confirmer.

Cette moto est fausse pour les deux : EfficientNet lit bicycle-built-for-two, mappée vers Sport, à 0,637 (auto), et CLIP lit bicycle à 0,481 (à confirmer). Les deux tombent sur la catégorie voisine. Sept des 100 véhicules du jeu focal sont faux pour les deux modèles, et la confiance 0,637 est l'une des deux erreurs Véhicules d'EfficientNet au-dessus de 0,6.

### Échiquier lu comme un paillasson

- Fichier : `jeux-et-jouets/focus_caltech_test_chess-board_474.jpg`
- Vignette : `web/public/jeu/jeux-et-jouets/focus_caltech_test_chess-board_474.webp`
- Attendu : Jeux et jouets
- EfficientNet int8 : Maison et meubles, 0,794, top-1 ImageNet `doormat`, auto.
- CLIP générique : Jeux et jouets, 0,875, texte `game`, auto.

L'échiquier n'a pas de classe ImageNet. EfficientNet lit doormat, mappée vers Maison et meubles, à 0,794 (auto) : un rectangle à motif est lu comme un paillasson, et 35 des 100 jeux tombent dans Maison. CLIP reste sur game à 0,875 (auto).

## Erreur confiante

La confiance de catégorie dépasse 0,6 et la catégorie est fausse. Monter le seuil laisse passer l'annonce. Sur ce jeu, EfficientNet a 13 erreurs confiantes sur 95 (2 des 12 erreurs Véhicules, 11 des 83 erreurs Jeux). CLIP en a 12 sur 75 (7 des 56 erreurs Véhicules, 5 des 19 erreurs Jeux). Le décompte vient du JSON de comparaison ; les photos ci-dessous en sont des exemples.

### Volant lu comme un lecteur de cassettes

- Fichier : `vehicules-et-pieces/focus_caltech_test_steering-wheel_538.jpg`
- Vignette : `web/public/jeu/vehicules-et-pieces/focus_caltech_test_steering-wheel_538.webp`
- Attendu : Véhicules et pièces
- EfficientNet int8 : Électronique, 0,842, top-1 ImageNet `cassette player`, auto.
- CLIP générique : Véhicules et pièces, 0,897, texte `vehicle`, auto.

Le volant n'est pas une classe du mapping. EfficientNet lit cassette player, donc Électronique, à 0,842 : au-dessus de 0,6 l'annonce fausse partirait en auto, comme 2 des 12 erreurs Véhicules de ce modèle. CLIP reste sur vehicle à 0,897 (auto).

### Carte à jouer lue comme une enveloppe

- Fichier : `jeux-et-jouets/focus_caltech_test_playing-card_2330.jpg`
- Vignette : `web/public/jeu/jeux-et-jouets/focus_caltech_test_playing-card_2330.webp`
- Attendu : Jeux et jouets
- EfficientNet int8 : Livres et musique, 0,729, top-1 ImageNet `envelope`, auto.
- CLIP générique : Jeux et jouets, 0,988, texte `game`, auto.

La carte à jouer n'est pas dans le mapping. EfficientNet lit envelope, donc Livres et musique, à 0,729 : le seuil 0,6 laisserait partir une annonce fausse en auto, comme 11 des 83 erreurs Jeux de ce modèle. CLIP lit game à 0,988 (auto, bonne catégorie).

## Puits Autre

Une classe ImageNet hors mapping aboutit à Autre. Le dé, la carte, le yo-yo, l'échiquier et le distributeur Pez n'ont pas de classe à eux : selon la photo, la masse tombe dans ce puits, ici sous le seuil. CLIP, avec les textes `toy` et `game`, reste sur Jeux.

### Dé lu comme une boîte de Petri

- Fichier : `jeux-et-jouets/focus_caltech_test_dice_1238.jpg`
- Vignette : `web/public/jeu/jeux-et-jouets/focus_caltech_test_dice_1238.webp`
- Attendu : Jeux et jouets
- EfficientNet int8 : Autre, 0,396, top-1 ImageNet `Petri dish`, à confirmer.
- CLIP générique : Jeux et jouets, 0,973, texte `game`, auto.

Le dé n'est pas une classe ImageNet, et le mapping n'a pas été modifié. EfficientNet retient Petri dish, classe hors mapping, donc le puits Autre, à 0,396 (à confirmer). CLIP lit game à 0,973 (auto, bonne catégorie) : sur les jouets, c'est CLIP qui rattrape la photo, dans un ensemble où il atteint 81 %.

## Classe absente

ImageNet n'a pas l'objet, et le mapping n'a pas été étendu pour le faire apparaître. Jeux et jouets ne reçoit que neuf classes : boulier, ballon, puzzle, masque, tirelire, moulin, peluche, magasin de jouets, tricycle. Le yo-yo n'y figure pas. Les deux modèles partent alors dans deux directions, et l'un des deux peut quand même dépasser 0,6.

### Yo-yo, les deux faux

- Fichier : `jeux-et-jouets/focus_caltech_test_yo-yo_1788.jpg`
- Vignette : `web/public/jeu/jeux-et-jouets/focus_caltech_test_yo-yo_1788.webp`
- Attendu : Jeux et jouets
- EfficientNet int8 : Livres et musique, 0,278, top-1 ImageNet `gong`, à confirmer.
- CLIP générique : Maison et meubles, 0,907, texte `kitchenware`, auto.

Le yo-yo n'est pas dans les neuf classes Jeux du mapping, qui n'a pas été modifié. Les deux modèles se trompent : EfficientNet lit gong (Livres et musique, 0,278, à confirmer) et CLIP lit kitchenware (Maison et meubles, 0,907, auto). Une classe absente produit ici une annonce fausse au-dessus du seuil ; 17 des 100 jeux sont faux pour les deux, et 5 des 19 erreurs Jeux de CLIP dépassent 0,6.

## Ce que ces cas ne disent pas

Les dix photos illustrent le motif mesuré sur 100 + 100 : EfficientNet juste et CLIP faux sur un véhicule (moto, motoneige), CLIP juste et EfficientNet faux sur un jouet (dé, carte, échiquier), une erreur au-dessus de 0,6 (volant, carte, yo-yo côté CLIP), et des photos fausses pour les deux (tandem, yo-yo). Elles ne remplacent pas le tableau du début.

Le 80 % Véhicules de CLIP reste le chiffre des 20 photos de l'autre jeu. Le 68,5 % / 95 % / 20 % de ResNet reste le chiffre des 200 historiques. Rien, dans ce dossier, ne leur attribue une valeur sur `focus_caltech_`.
