# Itération 7 — Le Grand Saut : déploiement Azure Container Apps

> Statut : **déployé**. URL publique live :
> [https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io](https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io)
>
> Runtime : image **ONNX-only** (pas de PyTorch / transformers / CUDA) + SPA React servie par FastAPI. Cible taille ≈ **≤ 551 Mo** (catalogue = petits `.onnx` int8 supplémentaires).

## Architecture de déploiement

```
git push main ──► GitHub Actions ──► tests pytest
                                  └► docker build (runtime-onnx : node SPA + python slim + onnxruntime)
                                       └► ghcr.io/xlucasgithubx/marketplace_ynov:latest
                                       └► smoke : SPA /, 401 sans token, 200 avec /api/predict
Azure Cloud Shell ──► scripts/deploy_azure.sh ──► Azure Container Apps (Sweden Central)
                                                   --logs-destination none (pas de Log Analytics)
                                                   image tirée de GHCR, HTTPS public,
                                                   API_TOKEN en secret, AZURE_RUNTIME=true,
                                                   scale 0 → 3 répliques
```

## URL et smoke live

| Ressource | URL |
| --- | --- |
| SPA + API | https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io/ |
| Health | …/health ou …/api/health |
| Catalogue modèles | …/api/models |
| Swagger | …/docs |

```bash
URL=https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io
curl -s $URL/health
curl -s $URL/api/models | head
curl -s -o /dev/null -w "%{http_code}\n" -F file=@velo.jpg $URL/api/predict                                   # 401
curl -s -H "Authorization: Bearer $API_TOKEN" -F file=@velo.jpg $URL/api/predict                             # 200 + JSON
```

## Choix et justifications

| Choix | Pourquoi |
| --- | --- |
| **Azure Container Apps**, plan Consommation | Conteneur serverless : HTTPS fourni, scale à zéro, offre gratuite mensuelle. Couvert par le crédit Azure for Students. |
| **Image GHCR** (CI GitHub Actions) | Pas d'ACR Tasks sur abo étudiant ; ACR Basic ≈ 5 $/mois. |
| **`--logs-destination none`** à la création de l'env | Évite Log Analytics / `ResourceNotFound` / policy sur abo étudiants. |
| **ONNX-only + SPA dans le même conteneur** | Un seul service facturé ; PyTorch / CLIP restent hors image Azure (export CI / Space `Lulu18`). |
| **1 vCPU / 2 Gio** | Mesures it. 5 : ≈ 23 req/s par réplique. |
| **`API_TOKEN` en secret** (`secretref:`) | Jamais dans l'image ni le dépôt. |
| **`AZURE_RUNTIME=true`** | Les modèles `space_only` (CLIP) ne démarrent pas sur ACA. |
| **`min-replicas=0`** par défaut | 0 $ hors usage ; `MIN_REPLICAS=1` le jour J (soutenance). |

## Procédure (re-déploiement / autre région)

1. Pousser sur `main` : Actions → job `image` vert.
2. Paquet GHCR **public** (ou `GHCR_USER` + `GHCR_TOKEN` avec `read:packages`).
3. [Azure Cloud Shell](https://shell.azure.com) (bash) :

```bash
git clone https://github.com/xLucasGitHubx/MarketPlace_Ynov.git && cd MarketPlace_Ynov
export API_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "$API_TOKEN"                 # à garder pour la démo
LOCATION=swedencentral ./scripts/deploy_azure.sh
```

4. Si `RequestDisallowedByPolicy`, choisir une région autorisée affichée par le script.

## Image Docker (rappel taille)

```bash
# Prod (défaut) : SPA + ONNX int8, sans torch dans les couches finales
docker build --target runtime-onnx -t marketplace-api:onnx .
docker images marketplace-api:onnx   # viser ≈ ≤ 551 Mo ; + quelques Mo par ONNX catalogue

# Catalogue supplémentaire (EfficientNet / MobileNet / student) :
python scripts/export_catalog.py
cp models/onnx/*-int8-static.onnx artifacts/onnx/
docker build --target runtime-onnx -t marketplace-api:onnx .
```

## Fin de projet

```bash
az group delete --name rg-marketplace-ynov --yes --no-wait     # supprime tout, plus aucune facturation
```
