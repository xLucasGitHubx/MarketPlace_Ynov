# FinOps — Estimation budgétaire

**Question :** combien coûte la catégorisation de **1 million de photos par mois** ?

**Réponse courte :** environ **3 $ par mois** avant offre gratuite (**0,3 centime pour 1 000 images**) sur Google Cloud Run avec l'image ONNX int8, et **0 $** une fois l'offre gratuite déduite. Le même volume coûte **3× plus** avec le modèle PyTorch non optimisé. Garder une instance toujours allumée pour supprimer le démarrage à froid ajoute **≈ 13 $/mois**.

Tous les prix sont les tarifs publics Google Cloud en USD, région Tier 1 (`europe-west1` Belgique / `europe-west9` Paris), relevés le 30/10/2026 ([Cloud Run pricing](https://cloud.google.com/run/pricing)). Les consommations viennent de nos mesures ([it5-charge.md](docs/preuves/it5-charge.md)), pas d'hypothèses théoriques.

## 1. Mesures de départ

| Mesure (1 vCPU, comme une instance Cloud Run) | ONNX int8 (prod) | PyTorch fp32 (référence) |
| --- | --- | --- |
| Temps de traitement d'une requête isolée (p50) | 68 ms | 205 ms |
| Débit max d'une instance | ≈ 23 req/s | ≈ 4,6 req/s |
| CPU consommé par image à saturation | ≈ 0,043 vCPU-s | ≈ 0,22 vCPU-s |
| Mémoire en charge | 260 Mo → instance 1 Gio | 533 Mo → instance 2 Gio |
| Taille de l'image Docker | 551 Mo | 2,04 Go |
| Démarrage à froid (conteneur prêt) | 1,6 s | ≈ 7 s |

## 2. Tarifs utilisés (Cloud Run, facturation à la requête)

| Poste | Prix | Offre gratuite mensuelle |
| --- | --- | --- |
| CPU actif | 0,000024 $ / vCPU-seconde | 180 000 vCPU-s |
| Mémoire active | 0,0000025 $ / Gio-seconde | 360 000 Gio-s |
| Requêtes | 0,40 $ / million | 2 millions |
| Instance minimale au repos (CPU + mémoire) | 0,0000025 $ / vCPU-s + 0,0000025 $ / Gio-s | — |
| GPU NVIDIA L4 (sans redondance zonale) | 0,0001867 $ / seconde | — |

Cloud Run facture le temps d'instance **arrondi aux 100 ms supérieures** et seulement pendant le traitement des requêtes : à zéro trafic, zéro coût (hors instance minimale).

## 3. Hypothèses

1. **Volume :** 1 000 000 photos/mois, soit 0,39 req/s en moyenne. Le trafic d'une marketplace est concentré en soirée : pic estimé à ×5, soit ≈ 2 req/s. Une seule instance suffit largement (capacité 23 req/s).
2. **Facturation par requête, cas défavorable :** à 0,4 req/s, les requêtes se chevauchent rarement. Chaque requête est donc facturée comme une période d'activité isolée, arrondie à 100 ms (ONNX : 68 ms → 100 ms ; PyTorch : 205 ms → 300 ms).
3. **Cas favorable (fort trafic) :** les instances tournent à saturation, le coût par image tend vers le CPU réellement consommé (0,043 vCPU-s).
4. **Configuration :** ONNX = 1 vCPU / 1 Gio ; PyTorch = 1 vCPU / 2 Gio ; `concurrency` = 4 ; scale à zéro.
5. **Postes négligés car négligeables à ce volume :** stockage de l'image dans Artifact Registry (0,55 Go), trafic sortant (réponses JSON de ~600 octets, ≈ 0,6 Go/mois), Secret Manager, Cloud Logging (sous les seuils gratuits). Le trafic entrant (les photos) n'est pas facturé.
6. Le serveur MLflow n'est pas compté : il tourne en local ou sur un poste de l'équipe pendant la phase projet.

## 4. Calcul pour 1 M d'images/mois

### Image ONNX int8 (production)

| Poste | Calcul | Coût |
| --- | --- | --- |
| CPU | 1 M × 0,1 s × 1 vCPU = 100 000 vCPU-s × 0,000024 $ | 2,40 $ |
| Mémoire | 1 M × 0,1 s × 1 Gio = 100 000 Gio-s × 0,0000025 $ | 0,25 $ |
| Requêtes | 1 M × 0,40 $ / M | 0,40 $ |
| **Total brut** | | **3,05 $ / mois** |
| Offre gratuite | 100 000 vCPU-s < 180 000 ; 100 000 Gio-s < 360 000 ; 1 M req < 2 M | −3,05 $ |
| **Total net** | | **0 $ / mois** |

Cas favorable (instances saturées, 0,043 s/image) : 1,04 $ CPU + 0,11 $ mémoire + 0,40 $ requêtes = **1,55 $ brut**. Le coût réel se situe donc entre **1,55 et 3,05 $ pour 1 M d'images**, soit **0,15 à 0,3 centime pour 1 000 images**.

### Image PyTorch fp32 (sans optimisation)

| Poste | Calcul | Coût |
| --- | --- | --- |
| CPU | 1 M × 0,3 s × 1 vCPU = 300 000 vCPU-s | 7,20 $ |
| Mémoire | 1 M × 0,3 s × 2 Gio = 600 000 Gio-s | 1,50 $ |
| Requêtes | | 0,40 $ |
| **Total brut** | | **9,10 $ / mois** |
| **Total net** (après offre gratuite) | (120 000 vCPU-s + 240 000 Gio-s facturés) | **3,48 $ / mois** |

**L'optimisation de l'itération 4 divise la facture par 3** (par ~4,4 à fort trafic : 1,55 $ contre 6,78 $ par million d'images).

### Supprimer le démarrage à froid (`min-instances=1`)

Une instance ONNX toujours prête, facturée au tarif « repos » quand elle ne traite rien :
2 592 000 s/mois × (1 vCPU × 0,0000025 $ + 1 Gio × 0,0000025 $) = **12,96 $ / mois**.
Recommandé le jour de la soutenance (ou un appel `/health` juste avant la démo). Le démarrage à froid de l'image ONNX (1,6 s) est déjà court ; avec PyTorch (≈ 7 s + 2 Go à télécharger), l'instance minimale serait quasi obligatoire.

## 5. Et si le volume change ?

| Volume mensuel | Pic estimé (×5) | Cloud Run ONNX | Cloud Run PyTorch | VM e2-standard-2, trafic régulier | VM e2-standard-2, dimensionnée pour le pic |
| --- | --- | --- | --- | --- | --- |
| 1 M | 2 req/s | 1,55 – 3,05 $ | 6,8 – 9,1 $ | 53,81 $ (1 VM) | 53,81 $ (1 VM) |
| 10 M | 19 req/s | 15 – 30 $ | 68 – 91 $ | 53,81 $ (1 VM) | 53,81 $ (1 VM) |
| 50 M | 96 req/s | ≈ 77 $ | ≈ 340 $ | 53,81 $ (1 VM) | ≈ 161 $ (3 VM) |
| 100 M | 193 req/s | ≈ 155 $ | ≈ 680 $ | ≈ 108 $ (2 VM) | ≈ 269 $ (5 VM) |

Montants bruts, hors offre gratuite. Cloud Run : fourchette « requêtes isolées » → « instances saturées » ; à fort volume, on prend le cas saturé. VM : tarif à la demande `europe-west1` de 53,81 $/mois, capacité mesurée ≈ 48 req/s sur 2 vCPU.

**Lecture :** avec un trafic en pics, comme sur une marketplace, Cloud Run reste le moins cher à tous les volumes, car il ne paie que les secondes utilisées alors qu'une VM doit être dimensionnée pour la pointe. Une VM ne gagne que si le trafic est régulier et dépasse ~20-30 M d'images/mois. Il faut alors gérer soi-même la mise à l'échelle, les mises à jour et la haute disponibilité.

## 6. Pourquoi pas de GPU ?

Une instance Cloud Run avec GPU L4 coûte 0,0001867 $/s pour le seul GPU, soit **≈ 484 $/mois** allumée en continu. S'y ajoutent les 4 vCPU et 16 Gio minimum (facturation à l'instance), soit ≈ 270 $, pour un total d'environ **750 $/mois**. Pour un ResNet-50 int8 de 25 Mo qui répond en 20 à 70 ms sur CPU, le GPU coûte **250 fois plus cher** sans bénéfice pour l'utilisateur. Le GPU devient pertinent pour un modèle beaucoup plus lourd (CLIP ViT-L, génération de descriptions) ou au-delà de quelques centaines de requêtes par seconde.

## 7. Et CLIP ?

Le benchmark CLIP ViT-B/32 (88,5 % d'accuracy, borne optimiste) tourne aujourd'hui en PyTorch fp32 (577 Mo, ≈ 90 ms sur 2 vCPU). Sans optimisation, son coût serait du même ordre que ResNet PyTorch : **≈ 9 $ brut pour 1 M d'images**, soit ≈ 6 $ de plus par mois pour +7 à +20 points d'accuracy. Exporter son encodeur image en ONNX int8 ramènerait ce coût vers celui de l'image actuelle. À ce volume, la décision se joue sur la qualité, pas sur le budget.

## 8. Leviers d'économie

1. **ONNX int8** (fait) : calcul ÷ 3 à 5, mémoire ÷ 2, image ÷ 3,7, démarrage ÷ 4.
2. **Scale à zéro** (par défaut) : 0 $ la nuit.
3. **Rejet avant lecture** (fait) : les requêtes sans token ou trop lourdes ne consomment presque rien. Avec `--allow-unauthenticated` côté Cloud Run, elles restent néanmoins facturées comme requêtes (0,40 $/M) : un Cloud Armor ou un quota par client couvrirait un abus massif.
4. **Redimensionnement côté client** : envoyer une photo de 512 px au lieu de 4 000 px réduit l'upload et le décodage, sans effet sur la prédiction (le modèle travaille en 224 px).
5. **Facturation à l'instance** (0,000018 $/vCPU-s) si le trafic devient continu : 25 % moins cher que la facturation à la requête.
6. **Budget et alerte** : budget GCP à 10 $/mois avec alertes à 50/90/100 % ; `--max-instances 10` plafonne la dépense en cas de pic ou d'attaque (10 instances × 23 req/s ≈ 230 req/s max).
