# FinOps — Estimation budgétaire

**Question :** combien coûte la catégorisation de **1 million de photos par mois** ?

**Réponse courte, sur Azure Container Apps (plateforme retenue) :**

- Pour **1 M d'images/mois** : environ **25 $/mois** avec une réplique toujours prête (1 vCPU, 2 Gio), soit **2,5 centimes pour 1 000 images**. Avec 0,5 vCPU, c'est environ **13 $/mois**.
- Pour **la phase projet** (démos, soutenance, quelques centaines de requêtes) : **0 $**. Le scale à zéro et l'offre gratuite mensuelle couvrent tout, et le crédit Azure for Students de 100 $ n'est pas entamé.
- **À fort volume**, le coût tend vers **≈ 1,8 $ par million d'images**.
- Sans l'optimisation ONNX de l'itération 4, il faudrait **5× plus de CPU** par image.

Prix publics Azure en USD, région **France Central**, relevés le 30/10/2026 via l'[API Azure Retail Prices](https://prices.azure.com/api/retail/prices) ; règles de facturation : [Container Apps billing](https://learn.microsoft.com/azure/container-apps/billing). Les consommations viennent de nos mesures ([it5-charge.md](docs/preuves/it5-charge.md)), pas d'hypothèses théoriques.

## 1. Mesures de départ

| Mesure (1 vCPU) | ONNX int8 (prod) | PyTorch fp32 (référence) |
| --- | --- | --- |
| Temps de traitement d'une requête isolée (p50) | 68 ms | 205 ms |
| Débit max d'une réplique | ≈ 23 req/s | ≈ 4,6 req/s |
| CPU consommé par image à saturation | ≈ 0,043 vCPU-s | ≈ 0,22 vCPU-s |
| Mémoire en charge | 260 Mo | 533 Mo |
| Taille de l'image Docker | 551 Mo | 2,04 Go |
| Démarrage à froid (conteneur prêt) | 1,6 s | ≈ 7 s |

## 2. Tarifs Azure Container Apps (plan Consommation, France Central)

| Poste | Prix | Offre gratuite mensuelle (par abonnement) |
| --- | --- | --- |
| vCPU, réplique **active** | 0,000024 $ / vCPU-seconde | 180 000 vCPU-s |
| vCPU, réplique **au repos** | 0,000003 $ / vCPU-seconde | (même enveloppe) |
| Mémoire, active ou au repos | 0,000003 $ / Gio-seconde | 360 000 Gio-s |
| Requêtes HTTP | 0,40 $ / million | 2 millions |
| GPU NVIDIA T4 (serverless) | 0,000091 $ / seconde | — |
| Registre ACR Basic (non utilisé) | 0,1666 $ / jour ≈ 5 $/mois | — |
| Log Analytics (ingestion) | 2,76 $ / Go | quelques Mo/mois ici |

Ce qu'il faut savoir sur la facturation Container Apps, et qui change tout le calcul :

1. **Scale à zéro = 0 $**, mais une réplique ne s'éteint qu'après **300 s sans requête** (*cooldown*). Pendant ce délai, elle est facturée au **tarif actif**.
2. Le **tarif repos** (8× moins cher en CPU) ne s'applique qu'aux répliques du **minimum** (`min-replicas ≥ 1`) qui ne traitent aucune requête.
3. Les sondes de santé ne sont pas facturées comme requêtes.

Le registre est **GitHub Container Registry** (gratuit, image publiée par la CI) plutôt qu'ACR. Cela évite 5 $/mois et contourne le blocage d'ACR Tasks sur les abonnements étudiants.

## 3. Hypothèses

1. **Volume :** 1 000 000 photos/mois, soit 0,39 req/s en moyenne. Le trafic d'une marketplace se concentre sur ~16 h par jour (pic estimé ×5, soit ≈ 2 req/s) : une seule réplique suffit (capacité 23 req/s).
2. **Configuration de base :** 1 vCPU / 2 Gio (couple imposé par Container Apps), `concurrency` 4, comme mesuré. Variante : 0,5 vCPU / 1 Gio, environ 2× plus lente mais toujours sous la cible de 500 ms à faible charge.
3. **Temps actif :** environ 0,1 s par requête (68 ms de traitement plus la marge), soit 100 000 s/mois pour 1 M d'images.
4. **Négligés :** trafic sortant (réponses JSON de ~600 octets, ≈ 0,6 Go/mois), Log Analytics (quelques Mo), MLflow (tourne en local pendant le projet). Le trafic entrant (les photos) n'est pas facturé.

## 4. Calcul pour 1 M d'images/mois (image ONNX int8, 1 vCPU / 2 Gio)

Coût d'une réplique par seconde : **active** = 0,000024 + 2 × 0,000003 = **0,000030 $** ; **au repos** = 0,000003 + 2 × 0,000003 = **0,000009 $**.

### Option A — `min-replicas=0` (scale à zéro)

Avec une requête toutes les 1 à 2 s en journée, la réplique ne reste jamais 300 s sans requête : elle tourne au tarif actif pendant les ~16 h d'activité.

| Poste | Calcul | Coût |
| --- | --- | --- |
| Réplique active | 16 h × 30 j = 1 728 000 s × 0,000030 $ | 51,84 $ |
| Requêtes | 1 M < 2 M gratuits | 0 $ |
| Offre gratuite | 180 000 vCPU-s (4,32 $) + 360 000 Gio-s (1,08 $) | −5,40 $ |
| **Total** | | **≈ 46 $ / mois** |

### Option B — `min-replicas=1` (une réplique toujours prête) ✅ recommandée à ce volume

| Poste | Calcul | Coût |
| --- | --- | --- |
| Réplique au repos | (2 592 000 − 100 000) s × 0,000009 $ | 22,43 $ |
| Réplique active | 100 000 s × 0,000030 $ | 3,00 $ |
| Requêtes | 1 M < 2 M gratuits | 0 $ |
| **Total brut** | | **25,43 $ / mois** |
| Après offre gratuite | selon la façon dont Azure impute les vCPU-s gratuits | **≈ 20 à 25 $ / mois** |

Soit **2 à 2,5 centimes pour 1 000 images**, sans démarrage à froid. C'est paradoxalement **moins cher que le scale à zéro**, parce que le tarif repos est 3,3× plus bas que le tarif actif.

Variante **0,5 vCPU / 1 Gio** : actif ≈ 150 000 s × 0,000015 $ = 2,25 $, plus repos 2 442 000 s × 0,0000045 $ = 10,99 $, soit **≈ 13 $ / mois**.

### Même calcul avec le modèle PyTorch non optimisé

PyTorch demande ≈ 0,3 s de calcul par image (contre 0,1 s) et sature à 4,6 req/s par réplique. À 1 M d'images, l'option B passe à 300 000 s actives × 0,000030 $ = 9 $, plus 2 292 000 s au repos × 0,000009 $ = 20,6 $, soit **≈ 30 $**. L'écart grandit avec le volume, puisque le coût actif est 5× plus élevé par image, et l'image de 2 Go rend chaque démarrage à froid lent (≈ 7 s plus le téléchargement).

## 5. Phase projet : ce que coûte vraiment le déploiement étudiant

| Usage | Calcul | Coût |
| --- | --- | --- |
| Démos ponctuelles (10 sessions/mois, ≈ 10 min actives chacune, cooldown inclus) | 6 000 s × 0,000030 $ = 0,18 $, couvert par l'offre gratuite | **0 $** |
| Jour de la soutenance avec `MIN_REPLICAS=1` (pas de démarrage à froid) | 86 400 s × 0,000009 $ | **0,78 $ / jour** |
| Registre (GHCR) | gratuit | **0 $** |
| Log Analytics | quelques Mo | **≈ 0 $** |

Le crédit de 100 $ suffit très largement. Conseil : passer `MIN_REPLICAS=1` la veille de la soutenance, le remettre à 0 après, puis supprimer le groupe de ressources en fin de projet (`az group delete`).

## 6. Et si le volume change ?

À fort volume, le coût suit le CPU réellement consommé : 0,043 vCPU-s par image, à ~70 % d'utilisation des répliques (Container Apps en ajoute dès 4 requêtes simultanées), soit **≈ 61 000 réplique-secondes par million d'images ≈ 1,84 $**.

| Volume mensuel | Pic estimé (×5) | Azure Container Apps (ONNX, min=1) | Google Cloud Run (ONNX, comparaison) | VM Linux 2 vCPU 24/7 (≈ 54 $) |
| --- | --- | --- | --- | --- |
| 1 M | 2 req/s | ≈ 25 $ | 1,55 – 3,05 $ | 1 VM ≈ 54 $ |
| 10 M | 19 req/s | ≈ 60 $ (réplique active ~16 h/j) | 15 – 30 $ | 1 VM ≈ 54 $ |
| 50 M | 96 req/s | ≈ 92 $ | ≈ 77 $ | 3 VM ≈ 161 $ (dimensionnées pour le pic) |
| 100 M | 193 req/s | ≈ 184 $ | ≈ 155 $ | 5 VM ≈ 269 $ |

(Montants bruts. Cloud Run : tarifs publics GCP Tier 1, facturation à la requête arrondie à 100 ms. VM : capacité mesurée ≈ 48 req/s sur 2 vCPU, prix de référence `e2-standard-2` GCP ; une VM Azure équivalente est du même ordre.)

**Lecture :**
- **Petit volume :** Cloud Run est moins cher que Container Apps, parce qu'il ne facture que les 100 ms de chaque requête alors qu'Azure facture la durée de vie de la réplique (cooldown de 300 s ou tarif repos). Pour ce projet, l'écart est sans importance : l'offre gratuite et le crédit étudiant couvrent tout.
- **Gros volume :** les deux plateformes convergent vers le coût du CPU consommé (≈ 1,6 à 1,8 $ par million d'images).
- **VM :** avec un trafic en pics comme celui d'une marketplace, le serverless reste moins cher qu'une VM dimensionnée pour la pointe. Une VM ne gagne que si le trafic est régulier et dépasse ~20-30 M d'images/mois, et il faut alors gérer soi-même la mise à l'échelle, les mises à jour et la disponibilité.

## 7. Pourquoi pas de GPU ?

Un GPU T4 serverless sur Container Apps coûte 0,000091 $/s, soit **≈ 236 $/mois** pour le seul GPU allumé en continu. Le tarif repos ne s'applique pas aux GPU. Pour un ResNet-50 int8 de 25 Mo qui répond en 20 à 70 ms sur CPU, c'est **10 fois le coût de l'option B** sans bénéfice pour l'utilisateur. Le GPU devient pertinent pour un modèle bien plus lourd (CLIP ViT-L, génération de descriptions) ou au-delà de quelques centaines de requêtes par seconde.

## 8. Et CLIP ?

Le benchmark CLIP ViT-B/32 (76,5 à 88,5 % d'accuracy) tourne aujourd'hui en PyTorch fp32 (577 Mo, ≈ 90 ms sur 2 vCPU). En production tel quel, son coût serait comparable au ResNet PyTorch (≈ 30 $/mois à 1 M d'images, option B). Exporter son encodeur image en ONNX int8 le ramènerait vers le coût actuel. À ce volume, le choix se joue sur la qualité, pas sur le budget.

## 9. Leviers d'économie

1. **ONNX int8** (fait) : 5× moins de CPU par image, mémoire ÷ 2, image ÷ 3,7, démarrage ÷ 4.
2. **Registre gratuit** (fait) : GHCR alimenté par la CI au lieu d'ACR Basic (−5 $/mois).
3. **`min-replicas` adapté au trafic** : 0 pour un usage ponctuel, 1 dès que le trafic est continu (tarif repos 3,3× moins cher que le tarif actif).
4. **0,5 vCPU / 1 Gio** si la latence le permet : facture divisée par 2.
5. **Rejet avant lecture** (fait) : les requêtes sans token ou trop lourdes ne consomment presque rien (elles restent comptées comme requêtes HTTP).
6. **Redimensionnement côté client** : envoyer une photo de 512 px au lieu de 4 000 px réduit l'upload et le décodage, sans effet sur la prédiction (le modèle travaille en 224 px).
7. **Garde-fous** : `max-replicas 3` plafonne la dépense en cas de pic ou d'abus (3 × 23 ≈ 70 req/s). Ajouter un budget Azure avec alertes à 10, 25 et 50 $ sur l'abonnement.
