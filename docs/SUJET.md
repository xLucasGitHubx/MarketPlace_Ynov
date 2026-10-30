# Projet d'industrialisation d'une API de vision par ordinateur (sujet Ynov)

Module : Industrialisation de l'IA dans le Cloud. Thème retenu : **B — La Marketplace** (API de catégorisation : l'API reçoit des photos d'objets réalisées par des utilisateurs et identifie la catégorie de l'objet pour pré-remplir une annonce e-commerce).

Prérequis : compte Hugging Face + Access Token pour télécharger les modèles.

Méthodologie : 9 itérations ; pour chacune, une phase **Mission** (pratique, essais/erreurs) puis **Application** (concepts d'industrialisation).

| It. | Nom | Mission | Livrable |
| --- | --- | --- | --- |
| 1 | Le Squelette | API web basique avec un point d'entrée POST recevant une image | Code Python fonctionnel + Swagger local |
| 2 | Le Cerveau | Connecter un modèle Hugging Face : prétraitement, inférence, prédiction JSON | API renvoyant une prédiction réelle |
| 3 | L'Isolement | Packager l'API avec Docker | Dockerfile optimisé et fonctionnel |
| 4 | L'Optimisation | Réduire poids et temps d'inférence (ONNX, quantization) | Code utilisant la version optimisée du modèle |
| 5 | Le Flux | Script externe simulant un afflux continu d'images (test de charge) | — |
| 6 | La Barrière | Authentification + aucune image conservée après inférence (RGPD) | API exigeant un token |
| 7 | Le Grand Saut | Déployer le conteneur sur un cloud (si possible) | — |
| 8 | Le Rétroviseur | MLflow : tracker le temps de réponse, comparer modèle lourd (it. 2) et optimisé (it. 4) | Dashboard MLflow (historique requêtes + métriques) |
| 9 | La Facture | Estimation budgétaire pour 1 M images/mois + documentation finale | Repo Git complet : code, Dockerfile, README.md, estimation budgétaire |
