# LLM Council — Choix du cœur de modèle (30/10/2026)

## Question posée

ResNet-50 + mapping ImageNet (spec) vs CLIP zero-shot vs hybride : quel cœur de modèle pour le MVP ?

## Question cadrée (envoyée aux 5 conseillers)

CONTEXTE : Projet d'école (Ynov, Master/Niveau 7 "expert IA", module "Industrialisation de l'IA dans le Cloud"), étudiant en alternance travaillant seul. Sujet : transformer un modèle de vision Hugging Face pré-entraîné en microservice API industrialisé, en 9 itérations notées : 1 API FastAPI + Swagger, 2 intégration modèle HF, 3 Docker, 4 optimisation (ONNX/quantization), 5 test de charge, 6 sécurité (token + aucune image conservée, RGPD), 7 déploiement cloud (si possible), 8 MLflow (comparer modèle lourd vs optimisé : latence + métriques), 9 FinOps (coût pour 1M images/mois) + README. Le module évalue l'industrialisation, pas l'entraînement. Thème choisi : Marketplace type Leboncoin — l'API reçoit la photo d'un objet prise par un vendeur et renvoie une catégorie d'annonce parmi ~10 (Électronique, Maison et meubles, Électroménager, Vêtements et accessoires, Sport et loisirs, Jeux et jouets, Véhicules et pièces, Bricolage et jardin, Livres et musique, Autre), un titre suggéré, une confiance, et un statut "auto" (confiance >= 0.6) ou "a_confirmer" (top-3 proposé au vendeur). Critères de réussite fixés : accuracy catégorie >= 80 % sur 100 photos étiquetées à la main, modèle optimisé taille /3 et latence CPU -40 %, perte d'accuracy <= 2 pts, p95 < 500 ms à 10 req/s en local CPU, image Docker légère.

DÉCISION À TRANCHER : Quel cœur de modèle pour le MVP ?
Option A (spec actuelle) : microsoft/resnet-50 (classifieur ImageNet 1000 classes) + fichier categories.json qui mappe à la main les 1000 classes ImageNet vers les 10 catégories, score de catégorie = somme des probabilités softmax des classes mappées. Export ONNX + quantization dynamique int8 très bien documentés pour ResNet. Risque connu : ImageNet colle mal aux catégories Leboncoin (beaucoup de classes animaux/nature → "Autre", vêtements et meubles peu couverts), donc l'accuracy métier peut être faible.
Option B : modèle zero-shot CLIP (ex. openai/clip-vit-base-patch32) avec des prompts texte par catégorie ("une photo de vélo", etc.) : classe directement dans les catégories métier, plus flexible (changer de catégorie = changer un texte), mais modèle plus lourd (~600 Mo, deux encodeurs), export ONNX/quantization moins direct, et s'éloigne de la spec rédigée.
Option C : hybride — ResNet-50 en modèle principal pour suivre la spec, CLIP comme "modèle alternatif" comparé dans MLflow.
Enjeux : note du projet, temps limité (étudiant seul en alternance), démonstration en soutenance de 10 min, cohérence avec la spec déjà rédigée et le formateur. Que doit-il faire ?

## Réponses des conseillers

Mapping d'anonymisation pour la revue : A = Outsider, B = Executor, C = Contrarian, D = Expansionist, E = First Principles

**Response A:**
Regard d'un outsider (juré qui découvre le projet, ou vendeur qui utilise l'appli) : Le problème du ResNet-50 saute aux yeux dès la démo. Un juré met une photo de canapé, de vélo, de robe. Le modèle renvoie "Autre" ou une catégorie absurde. Il ne comprend pas "somme des softmax des classes ImageNet mappées à la main" : il voit juste que ça ne marche pas. Pire : "atteindre 80 % sur 100 photos que j'ai moi-même étiquetées" ressemble à un test arrangé. Le piège du vocabulaire : pour toi, "industrialisation" = ONNX, Docker, p95, FinOps. Pour un juré, la question évidente reste : "est-ce que ça sert vraiment à un vendeur Leboncoin ?" Une API très bien emballée qui se trompe une fois sur deux, c'est un camion de livraison vide. Verdict : Option C, mais avec CLIP comme modèle principal et ResNet comme baseline. CLIP zero-shot répond directement aux 10 catégories ; ajouter une catégorie en live prend 5 secondes. Risque réel : export ONNX de CLIP moins direct. Atténuation : exporter uniquement l'encodeur image en ONNX et précalculer les embeddings texte des 10 prompts au démarrage. Présenter le changement comme une décision d'ingénieur documentée ("j'ai mesuré, ResNet échoue à X %").

**Response B:**
Option C, mais discipline stricte sur l'ordre : ResNet-50 d'abord, CLIP seulement après que les 9 itérations tournent. Le module note l'industrialisation. Si tu pars sur CLIP, l'export ONNX avec deux encodeurs et la quantization te feront perdre des jours sur l'itération 4. Lundi matin : 1) itérations 1-3 avec ResNet-50 et categories.json ; 2) constitue tout de suite les 100 photos étiquetées ; 3) mesure l'accuracy du ResNet dès que l'API tourne ; 4) après les itérations 1-6, passe CLIP en pur PyTorch, sans ONNX, sur ces 100 photos (2-3 h max) ; 5) dans MLflow, compare ResNet-50, ResNet-50 quantizé et CLIP. Si ResNet fait 55 % et CLIP 85 %, le récit : « j'ai mesuré, le modèle imposé ne tient pas le critère, voici la preuve et le coût de la bascule ». Garde-fou : si retard > 1 semaine à la fin de l'itération 6, abandonne CLIP ; CLIP reste un script de benchmark séparé, pas de code de production.

**Response C:**
Les trois options ont un défaut fatal : ton critère d'accuracy. 1) Option A probablement condamnée : ~50 % d'accuracy à tout casser (peu de vêtements, meubles, électroménager moderne ; beaucoup d'animaux en "Autre"). Tu le sauras seulement à l'itération 8. Échouer à son propre critère en soutenance est pire que dévier de la spec. 2) "Cohérence avec la spec" est un faux argument : la spec, tu l'as rédigée, elle se modifie en une ligne. 3) Vrai piège de CLIP : "taille /3, perte ≤2 pts" — quantifier l'encodeur visuel seul est faisable (~90 Mo int8, texte précalculé) mais personne n'a vérifié la dégradation ≤2 pts. Teste-le aujourd'hui. 4) Option C est un piège de temps : deux modèles doublent tests, exports, benchmarks, Docker. Verdict : spike de 2 h avant de trancher : CLIP zero-shot sur les 100 photos. Si > 80 %, pars sur B seul (il porte lui-même le comparatif lourd vs optimisé). Sinon, preuve chiffrée pour un fallback. Ne choisis jamais sans mesurer.

**Response D:**
Option C, et CLIP devient l'argument de soutenance, pas un plan B. Tableau MLflow à trois lignes : ResNet-50 FP32, ResNet-50 int8, CLIP zero-shot : un arbitrage produit précision vs coût/latence. Le FinOps prend de la valeur : "combien coûte chaque point d'accuracy". Flexibilité de CLIP : ajouter "Animaux" ou "Immobilier" dans un JSON en direct sans réentraîner. Portfolio : comparatif ImageNet mappé vs zero-shot sur 100 photos réelles. Concrètement : ResNet comme chemin principal pour les itérations 3-6, puis CLIP derrière une interface commune predict() ; mêmes 100 photos ; exporter seulement l'encodeur image de CLIP en ONNX. Étape à ne pas rater : test d'accuracy de ResNet sur les 100 photos dès maintenant ; s'il est sous 80 %, CLIP passe principal.

**Response E:**
Mauvaise question : le module évalue l'industrialisation, le modèle n'est que la charge utile. Mais le critère 80 % sera probablement raté avec ResNet + mapping manuel, et bricoler categories.json est de l'entraînement déguisé. Retire le critère "80 %" comme condition de réussite ; remplace-le par un critère relatif : le modèle optimisé perd < 2 pts face au lourd (ce que demande l'itération 8). Si tu veux une démo crédible, CLIP zero-shot est la bonne base. L'argument "ONNX moins direct" est faible : export de l'encodeur image seul + embeddings texte précalculés = un graphe simple. Vrai coût de CLIP : le poids, mais int8 + comparaison lourd/optimisé = récit FinOps plus intéressant. Verdict : itérations 1-3 avec le modèle qui s'exporte le plus vite, puis trancher sur un test de 20 photos. Ne décide pas à l'aveugle.

## Revues croisées (anonymes)

Les 5 relecteurs désignent **B (Executor)** comme réponse la plus solide (plan séquencé, garde-fou chiffré, protège la note).
Plus gros angle mort : **A (Outsider)** pour 4 relecteurs sur 5 (CLIP principal sans mesure, risque ONNX/planning ignoré), **E (First Principles)** pour 1 relecteur (« retirer le critère 80 % revient à tricher sur ses propres critères »).

Ce que les 5 conseillers ont tous manqué (consensus des relecteurs) :
- **Biais du jeu de test** : 100 photos étiquetées par l'étudiant lui-même → risque de test arrangé ; prévoir des « Autre » réalistes et des cas ambigus.
- **Valider avec le formateur** avant toute déviation de la spec (un mail suffit).
- **Seuil 0,6 non transposable** : somme de softmax ResNet et scores zero-shot CLIP n'ont pas la même distribution → seuil calibré par modèle.
- **Latence p95 et taille Docker de CLIP non chiffrées** (torch + 2 encodeurs).
- **Troisième voie oubliée** : un classifieur à vocabulaire plus riche (ImageNet-21k, ConvNeXt/ViT) ou un modèle HF déjà orienté produits.
- **Démo de 10 min** non planifiée en fonction du choix.

## Synthèse du Chairman

### Où le conseil est d'accord
- Le module note l'**industrialisation** : la chaîne API → Docker → ONNX → sécurité → MLflow → FinOps doit être finie quoi qu'il arrive.
- ResNet-50 + mapping manuel risque fortement de rater les 80 % (vêtements, meubles, électroménager mal couverts).
- **Ne pas trancher à l'aveugle** : mesurer l'accuracy tôt (dès l'itération 2), pas à l'itération 8.
- Si CLIP est utilisé : exporter **uniquement l'encodeur image** en ONNX et **pré-calculer les embeddings texte** au démarrage.

### Où le conseil diverge
- **Modèle principal** : Executor/Expansionist → ResNet principal, CLIP en benchmark ; Outsider → CLIP principal dès le départ ; Contrarian → spike CLIP de 2 h puis B seul s'il passe 80 %.
- **Critère 80 %** : First Principles veut le remplacer par un critère relatif ; les relecteurs jugent que c'est contourner le problème.

### Recommandation
**Option C, séquencée.** ResNet-50 reste le chemin de production pour les itérations 1 → 6 (conforme à la spec, ONNX/quantization éprouvés). Le code est conçu dès l'itération 2 autour d'une **interface `Predictor` commune** et d'un **seuil par modèle**, pour que CLIP puisse s'y brancher sans réécriture. L'accuracy est mesurée dès l'itération 2 sur un **jeu de test proxy public** (pas d'étiquetage maison biaisé), complété ensuite par les photos réelles de Lucas. CLIP est évalué comme **benchmark séparé** ; il ne devient principal que si la mesure le justifie (ResNet < 80 % et CLIP ≥ 80 % avec p95 < 500 ms). Le critère 80 % est conservé. Garde-fou : si le MVP prend du retard, CLIP reste une piste documentée.

### La première chose à faire
Constituer le jeu d'évaluation étiqueté (proxy public + photos réelles) et mesurer ResNet dès que l'itération 2 tourne.

## Décisions appliquées au repo
- `app/model.py` expose une interface `Predictor` (backends interchangeables : `pytorch`, `onnx`, plus tard `clip`).
- `CONFIDENCE_THRESHOLD` paramétrable par backend.
- `scripts/evaluate.py` produit accuracy + latence dès l'itération 2, loggé dans MLflow à l'itération 8.
- À faire par Lucas : mail court au formateur pour valider ResNet pré-entraîné sans fine-tuning + CLIP comme comparaison.
