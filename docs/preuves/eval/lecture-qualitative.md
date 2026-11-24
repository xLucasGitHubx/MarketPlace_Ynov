# Lecture qualitative — proxy de 200 photos

Ces cas commentent des lignes déjà mesurées. Chaque catégorie du proxy compte **20 photos**. La lecture est illustrative : elle n'est pas une nouvelle accuracy. Le mapping `data/imagenet_mapping.tsv` n'a pas été modifié. Le jeu focal (`focus_manifest.csv`) n'est pas prêt ; aucune photo n'a été inventée. Les vignettes sont celles déjà présentes dans `web/public/jeu/`.

Les chiffres de cadrage, à ne pas recalculer à partir de ces cas :

| Modèle | Accuracy sur 200 | Véhicules | Jeux | Électroménager | Ce qu'on a le droit de dire |
| --- | --- | --- | --- | --- | --- |
| ResNet-50 int8 (historique) | 68,5 % | 95 % | 20 % | 55 % | 11 des 16 erreurs Jeux ont une confiance > 0,6. Confiance et top-1 ImageNet seulement sur les 63 erreurs. |
| EfficientNet-B0 int8 (ce run) | 63,5 % | 90 % | 25 % | 50 % | p50 = **103,8 ms** sur CPU Windows (`eval-efficientnet-b0-int8-static-200.json`). |
| CLIP ViT-B/32, vocabulaire générique | 76,5 % | 80 % | 90 % | 85 % | Le 88,5 % du vocabulaire détaillé est un autre protocole. |

Accord de catégorie sur les 200 : EfficientNet / ResNet **73,5 %**, CLIP / ResNet **60,5 %**. MobileNet fp32 (57,5 % sur 200, ce n'est pas un int8) et le student non distillé sont **non comparables** : ils n'entrent pas dans cette lecture.

Sources des lignes : `preds-resnet50-int8-historique-200.jsonl`, `preds-efficientnet-b0-int8-200.jsonl`, `preds-clip-vit-b32-generique-200.jsonl`. La confiance est le score de catégorie cumulé sur le top-5 (`suggest`). Le top-1 est la classe la plus forte. Pour CLIP, ce top-1 est un libellé de texte du vocabulaire générique, pas une classe ImageNet. Le seuil métier rappelé ici est 0,6. Le détail machine est dans `cas-qualitatifs.json` (13 cas : 10 sur Véhicules et Jeux, 3 sur Électroménager).

## Accord

La catégorie rendue est la même pour les trois modèles, et c'est la bonne. Cela arrive quand ImageNet a déjà la classe (véhicules, peluche). L'accord de catégorie ne dit pas que le statut serait `auto`.

### Camion de pompiers

- Fichier : `vehicules-et-pieces/caltech_fire-truck_2139.jpg`
- Vignette : `web/public/jeu/vehicules-et-pieces/caltech_fire-truck_2139.webp`
- Attendu : Véhicules et pièces
- ResNet int8 : Véhicules et pièces. Confiance et top-1 non archivés (photo absente des erreurs).
- EfficientNet int8 : Véhicules et pièces, 0,934, top-1 ImageNet `fire engine`, auto.
- CLIP générique : Véhicules et pièces, 0,923, texte `vehicle`, auto.

Le camion de pompiers est une classe ImageNet, fire engine, déjà mappée vers Véhicules et pièces. Les trois modèles rendent cette catégorie : EfficientNet à 0,934 (auto) et CLIP, vocabulaire générique, à 0,923 (libellé vehicle, auto). La confiance et le top-1 ResNet ne sont pas archivés, la photo étant absente des 63 erreurs.

### Motoneige

- Fichier : `vehicules-et-pieces/caltech_snowmobile_2477.jpg`
- Vignette : `web/public/jeu/vehicules-et-pieces/caltech_snowmobile_2477.webp`
- Attendu : Véhicules et pièces
- ResNet int8 : Véhicules et pièces. Confiance et top-1 non archivés.
- EfficientNet int8 : Véhicules et pièces, 0,897, top-1 ImageNet `snowmobile`, auto.
- CLIP générique : Véhicules et pièces, 0,285, texte `vehicle`, à confirmer.

La motoneige est dans le mapping, sous le nom snowmobile. ResNet et EfficientNet (0,897, auto) la classent en Véhicules, et CLIP aussi, avec le libellé vehicle à 0,285 seulement, donc à confirmer. Les trois modèles s'accordent sur la catégorie ; le statut auto dépend du score, et la confiance ResNet de cette réussite n'est pas archivée.

### Peluche

- Fichier : `jeux-et-jouets/caltech_teddy-bear_2938.jpg`
- Vignette : `web/public/jeu/jeux-et-jouets/caltech_teddy-bear_2938.webp`
- Attendu : Jeux et jouets
- ResNet int8 : Jeux et jouets. Confiance et top-1 non archivés.
- EfficientNet int8 : Jeux et jouets, 0,797, top-1 ImageNet `teddy`, auto.
- CLIP générique : Jeux et jouets, 0,576, texte `toy`, à confirmer.

teddy est l'une des neuf classes ImageNet mappées vers Jeux et jouets. Sur les 20 photos de la catégorie, les quatre peluches sont les quatre bonnes réponses de ResNet ; ici EfficientNet lit teddy à 0,797 (auto) et CLIP lit toy à 0,576 (à confirmer). La confiance ResNet de cette photo n'est pas dans l'archive.

## Classe absente

ImageNet n'a pas l'objet, et le mapping n'a pas été étendu pour le faire apparaître. Jeux et jouets ne reçoit que neuf classes : boulier, ballon, puzzle, masque, tirelire, moulin, peluche, magasin de jouets, tricycle. Dé, carte, yo-yo, échiquier et distributeur Pez n'y sont pas. Côté électroménager, la machine à pain et la bouilloire électrique n'y sont pas non plus (17 classes mappées).

### Yo-yo, trois directions

- Fichier : `jeux-et-jouets/caltech_yo-yo_921.jpg`
- Vignette : `web/public/jeu/jeux-et-jouets/caltech_yo-yo_921.webp`
- Attendu : Jeux et jouets
- ResNet int8 : Maison et meubles, 0,416, top-1 ImageNet `ladle`.
- EfficientNet int8 : Sport et loisirs, 0,067, top-1 ImageNet `whistle`, à confirmer.
- CLIP générique : Livres et musique, 0,254, texte `musical instrument`, à confirmer.

Le mapping Jeux compte neuf classes et n'a pas été modifié pour cette lecture : le yo-yo n'y figure pas. Les trois modèles se trompent dans trois directions : ResNet louche vers Maison à 0,416, EfficientNet sifflet vers Sport à 0,067, CLIP instrument de musique à 0,254. Aucun score n'atteint 0,6.

### Machine à pain lue comme une imprimante

- Fichier : `electromenager/caltech_breadmaker_2646.jpg`
- Vignette : `web/public/jeu/electromenager/caltech_breadmaker_2646.webp`
- Attendu : Électroménager
- ResNet int8 : Électronique, 0,993, top-1 ImageNet `printer`.
- EfficientNet int8 : Électronique, 0,275, top-1 ImageNet `printer`, à confirmer.
- CLIP générique : Électroménager, 0,913, texte `household appliance`, auto.

La machine à pain n'est pas dans les 17 classes Électroménager du mapping. ResNet et EfficientNet tombent tous les deux sur printer, donc Électronique : 0,993 pour ResNet, 0,275 pour EfficientNet (à confirmer). CLIP, vocabulaire générique, reste sur Électroménager, libellé household appliance, à 0,913 (auto).

## Puits Autre

Une classe ImageNet hors mapping aboutit à Autre. Ce puits compte 596 classes sur 1 000. Le yo-yo et la carte n'ont pas de classe à eux : selon la photo, la masse tombe dans ce puits, parfois au-dessus du seuil.

### Yo-yo lu comme « slot »

- Fichier : `jeux-et-jouets/caltech_yo-yo_1378.jpg`
- Vignette : `web/public/jeu/jeux-et-jouets/caltech_yo-yo_1378.webp`
- Attendu : Jeux et jouets
- ResNet int8 : Autre, 0,677, top-1 ImageNet `slot`.
- EfficientNet int8 : Maison et meubles, 0,395, top-1 ImageNet `saltshaker`, à confirmer.
- CLIP générique : Jeux et jouets, 0,619, texte `toy`, auto.

Sur cette autre photo de yo-yo, la classe ImageNet la plus forte de ResNet est slot, qui n'est pas mappée. Elle rejoint Autre, le puits des 596 classes hors mapping, avec une confiance de 0,677 : au seuil 0,6 la catégorie pré-remplie serait Autre. EfficientNet part vers une salière (Maison, 0,395) et CLIP retrouve toy à 0,619 (auto).

### Carte à jouer lue comme un pansement

- Fichier : `jeux-et-jouets/caltech_playing-card_1212.jpg`
- Vignette : `web/public/jeu/jeux-et-jouets/caltech_playing-card_1212.webp`
- Attendu : Jeux et jouets
- ResNet int8 : Autre, 0,503, top-1 ImageNet `Band Aid`.
- EfficientNet int8 : Livres et musique, 0,405, top-1 ImageNet `book jacket`, à confirmer.
- CLIP générique : Jeux et jouets, 0,835, texte `game`, auto.

La carte à jouer n'est pas une classe ImageNet. ResNet retient Band Aid, classe non mappée, donc Autre, à 0,503 : le puits reste sous le seuil 0,6. EfficientNet lit book jacket (Livres et musique, 0,405, à confirmer) et CLIP lit game à 0,835 (auto).

## Confusion voisine

La classe retenue existe, et elle est proche de l'objet : un tapis pour un échiquier, un vélo pour une moto, une théière pour une bouilloire. Maison et Électroménager sont le couple déjà décrit à l'itération 2. L'accord des deux CNN peut porter sur cette erreur commune.

### Échiquier lu comme un tapis

- Fichier : `jeux-et-jouets/caltech_chess-board_1380.jpg`
- Vignette : `web/public/jeu/jeux-et-jouets/caltech_chess-board_1380.webp`
- Attendu : Jeux et jouets
- ResNet int8 : Maison et meubles, 0,959, top-1 ImageNet `prayer rug`.
- EfficientNet int8 : Maison et meubles, 0,875, top-1 ImageNet `prayer rug`, auto.
- CLIP générique : Jeux et jouets, 0,544, texte `game`, à confirmer.

L'échiquier n'a pas de classe ImageNet. ResNet et EfficientNet s'accordent sur prayer rug, mappée vers Maison et meubles, à 0,959 et 0,875 : un rectangle à motif est lu comme un tapis. CLIP reste sur game, à 0,544, donc à confirmer.

### Moto lue comme un vélo

- Fichier : `vehicules-et-pieces/caltech_motorbikes-101_1465.jpg`
- Vignette : `web/public/jeu/vehicules-et-pieces/caltech_motorbikes-101_1465.webp`
- Attendu : Véhicules et pièces
- ResNet int8 : Véhicules et pièces. Confiance et top-1 non archivés.
- EfficientNet int8 : Véhicules et pièces, 0,490, top-1 ImageNet `moped`, à confirmer.
- CLIP générique : Sport et loisirs, 0,880, texte `bicycle`, auto.

Le cyclomoteur est une classe ImageNet mappée vers Véhicules : EfficientNet lit moped à 0,490 (à confirmer), et ResNet est dans la bonne catégorie, sans score archivé. Le vocabulaire générique de CLIP n'a pas de moto ; le libellé le plus fort est bicycle, côté Sport et loisirs, à 0,880 (auto). Moto et vélo sont des catégories voisines, et ce score passerait en auto.

### Bouilloire lue comme une théière

- Fichier : `electromenager/sop_271957718827_0.jpg` (classe source du manifest : `kettle`)
- Vignette : `web/public/jeu/electromenager/sop_271957718827_0.webp`
- Attendu : Électroménager
- ResNet int8 : Maison et meubles, 0,964, top-1 ImageNet `teapot`.
- EfficientNet int8 : Maison et meubles, 0,782, top-1 ImageNet `teapot`, auto.
- CLIP générique : Maison et meubles, 0,822, texte `kitchenware`, auto.

La ligne du manifest est une bouilloire (kettle). ImageNet n'a pas de bouilloire électrique : teapot est mappée vers Maison et meubles, et les trois modèles y vont, ResNet à 0,964, EfficientNet à 0,782 (auto), CLIP avec le libellé kitchenware à 0,822 (auto). Le vocabulaire générique range les ustensiles avec Maison.

## Erreur confiante

La confiance de catégorie dépasse 0,6 et la catégorie est fausse. Monter le seuil ne crée pas la classe manquante, et il laisse passer l'annonce. Sur le ResNet historique : 11 erreurs Jeux sur 16, la seule erreur Véhicules, et 7 erreurs Électroménager sur 9 sont dans ce cas. Les photos ci-dessous en sont des exemples, pas un nouveau décompte.

### Dé lu comme une gomme

- Fichier : `jeux-et-jouets/caltech_dice_716.jpg`
- Vignette : `web/public/jeu/jeux-et-jouets/caltech_dice_716.webp`
- Attendu : Jeux et jouets
- ResNet int8 : Livres et musique, 0,872, top-1 ImageNet `rubber eraser`.
- EfficientNet int8 : Vêtements et accessoires, 0,207, top-1 ImageNet `hair slide`, à confirmer.
- CLIP générique : Jeux et jouets, 0,990, texte `game`, auto.

Le dé n'est pas une classe ImageNet. ResNet choisit rubber eraser, donc Livres et musique, à 0,872 : au-dessus de 0,6, l'annonce fausse partirait en auto, comme 11 des 16 erreurs Jeux. EfficientNet part vers une barrette (0,207, à confirmer) et CLIP retrouve game à 0,990 (auto).

### Volant lu comme un ventilateur

- Fichier : `vehicules-et-pieces/caltech_steering-wheel_1266.jpg`
- Vignette : `web/public/jeu/vehicules-et-pieces/caltech_steering-wheel_1266.webp`
- Attendu : Véhicules et pièces
- ResNet int8 : Électroménager, 0,985, top-1 ImageNet `electric fan`.
- EfficientNet int8 : Électroménager, 0,806, top-1 ImageNet `electric fan`, auto.
- CLIP générique : Véhicules et pièces, 0,864, texte `vehicle`, auto.

C'est la seule erreur ResNet sur les 20 photos Véhicules, et sa confiance dépasse 0,6. Les deux CNN lisent electric fan, donc Électroménager, à 0,985 et à 0,806 : les deux dépasseraient le seuil. CLIP reste sur vehicle à 0,864 (auto).

### Lave-linge lu comme une photocopieuse

- Fichier : `electromenager/caltech_washing-machine_2316.jpg`
- Vignette : `web/public/jeu/electromenager/caltech_washing-machine_2316.webp`
- Attendu : Électroménager
- ResNet int8 : Électronique, 0,972, top-1 ImageNet `photocopier`.
- EfficientNet int8 : Bricolage et jardin, 0,468, top-1 ImageNet `ashcan`, à confirmer.
- CLIP générique : Électroménager, 0,899, texte `household appliance`, auto.

ImageNet possède la classe washer, et l'autre lave-linge des 20 photos est bien classé par les trois modèles. Ici ResNet lit photocopier, donc Électronique, à 0,972 : sept des neuf erreurs Électroménager dépassent ainsi 0,6. EfficientNet lit une poubelle (0,468, à confirmer) et CLIP retrouve household appliance à 0,899 (auto).
