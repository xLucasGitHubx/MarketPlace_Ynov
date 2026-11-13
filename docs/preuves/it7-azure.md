# Itération 7 — Le Grand Saut : déploiement Azure Container Apps

> Statut : **déployé**. URL publique live :
> [https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io](https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io)
>
> Runtime : image **ONNX-only** (pas de PyTorch / transformers / CUDA) + SPA React servie par FastAPI. Cible taille ≈ **≤ 551 Mo** (catalogue = petits `.onnx` int8 supplémentaires).
>
> **CD** : push `main` → CI (`tests` + `image` + smoke) → job `deploy` met à jour l’image ACA via OIDC (plus besoin de lancer `deploy_azure.sh` à la main).

## Architecture de déploiement

```
git push main ──► GitHub Actions
                    ├─ tests (pytest)
                    ├─ image : docker build runtime-onnx
                    │          → ghcr.io/xlucasgithubx/marketplace_ynov:latest
                    │          → ghcr.io/…/marketplace_ynov:<sha>
                    │          → smoke (SPA /, 401, 200 /api/predict)
                    └─ deploy (OIDC azure/login)
                         → az containerapp update --image …:<sha>
                            MODEL_BACKEND=onnx AZURE_RUNTIME=true
                            (API_TOKEN secret ACA inchangé)

Création initiale (une fois) : Cloud Shell + scripts/deploy_azure.sh
  → env ACA --logs-destination none, secret api-token, ingress HTTPS
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
| **CD OIDC** (`azure/login` + federated credential) | Pas de `AZURE_CLIENT_SECRET` longue durée dans GitHub ; le token est éphémère par run. |
| **Tag SHA** pour le deploy | Même digest que le smoke du même workflow ; `latest` reste un alias pratique. |
| **`--logs-destination none`** à la création de l'env | Évite Log Analytics / `ResourceNotFound` / policy sur abo étudiants. |
| **ONNX-only + SPA dans le même conteneur** | Un seul service facturé ; PyTorch / CLIP restent hors image Azure (export CI / Space `Lulu18`). |
| **1 vCPU / 2 Gio** | Mesures it. 5 : ≈ 23 req/s par réplique. |
| **`API_TOKEN` en secret ACA** (`secretref:`) | Jamais dans l'image, le dépôt, ni les secrets GitHub du CD. |
| **`AZURE_RUNTIME=true`** | Les modèles `space_only` (CLIP) ne démarrent pas sur ACA. |
| **`min-replicas=0`** par défaut | 0 $ hors usage ; `MIN_REPLICAS=1` le jour J (soutenance). |

---

## Continuous Deployment — checklist Lucas (OIDC, une seule fois)

Objectif : après configuration, **chaque merge / push sur `main`** met à jour `marketplace-api` sans relancer `deploy_azure.sh`.

### 1. Où coller les valeurs dans GitHub

Repo → **Settings** → **Secrets and variables** → **Actions**

- Onglet **Secrets** → *New repository secret* pour les 3 secrets Azure.
- Onglet **Variables** (optionnel) → *New repository variable* pour surcharger les noms de ressources.

### 2. Secrets GitHub (obligatoires pour le job `deploy`)

| Nom du secret | Contenu | Où le trouver / créer |
| --- | --- | --- |
| `AZURE_CLIENT_ID` | Application (client) ID de l’App Registration | Azure Portal → Microsoft Entra ID → App registrations → l’app `github-marketplace-ynov-cd` → *Overview* |
| `AZURE_TENANT_ID` | Directory (tenant) ID | Même page *Overview*, ou `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | Subscription ID | Portail → Abonnements, ou `az account show --query id -o tsv` |

**`API_TOKEN` n’a PAS besoin d’être dans GitHub Secrets.**  
Il est déjà (ou sera) un secret de la Container App (`api-token`). Le job `deploy` met à jour **uniquement** l’image + `MODEL_BACKEND` / `AZURE_RUNTIME` et **ne touche pas** à `API_TOKEN`.

### 3. Variables GitHub (optionnelles)

| Nom | Défaut si absent | Rôle |
| --- | --- | --- |
| `AZURE_RESOURCE_GROUP` | `rg-marketplace-ynov` | Groupe de ressources |
| `AZURE_CONTAINER_APP` | `marketplace-api` | Nom de l’app |

### 4. Commandes `az` à coller une fois dans Azure Cloud Shell

Remplace `OWNER` et `REPO` si besoin (`xLucasGitHubx` / `MarketPlace_Ynov`).  
Le subject OIDC pour les pushes sur `main` est `repo:OWNER/REPO:ref:refs/heads/main`.

```bash
# --- Identifiants abonnement ---
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
echo "SUBSCRIPTION_ID=$SUBSCRIPTION_ID"
echo "TENANT_ID=$TENANT_ID"

# --- App Registration ---
APP_NAME="github-marketplace-ynov-cd"
APP_ID=$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)
echo "AZURE_CLIENT_ID=$APP_ID"

# Service principal lié à l'app
az ad sp create --id "$APP_ID" -o none

# --- Credential fédéré GitHub Actions (OIDC, push main) ---
# Issuer + audience standard GitHub ; subject = branche main uniquement.
cat > /tmp/github-oidc-federated.json <<EOF
{
  "name": "github-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:xLucasGitHubx/MarketPlace_Ynov:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"],
  "description": "GitHub Actions CD push main MarketPlace_Ynov"
}
EOF
az ad app federated-credential create --id "$APP_ID" --parameters @/tmp/github-oidc-federated.json

# --- Rôle sur le groupe de ressources (Contributor suffit pour containerapp update) ---
RG=rg-marketplace-ynov
SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role Contributor \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}"

echo
echo "Coller dans GitHub → Settings → Secrets and variables → Actions → Secrets :"
echo "  AZURE_CLIENT_ID       = $APP_ID"
echo "  AZURE_TENANT_ID       = $TENANT_ID"
echo "  AZURE_SUBSCRIPTION_ID = $SUBSCRIPTION_ID"
```

Si tu déploies aussi depuis `workflow_dispatch` sur une autre ref, ajoute un second federated credential avec le subject correspondant (ex. `repo:…:environment:production` si tu utilises un Environment GitHub).

### 5. Paquet GHCR public ou privé

Azure tire `ghcr.io/xlucasgithubx/marketplace_ynov:<sha>`.

- **Recommandé (étudiants / démo)** : rendre le package **Public**  
  GitHub → *Packages* → `marketplace_ynov` → *Package settings* → *Change visibility* → Public.
- **Sinon (package Private)** : enregistrer les credentials registre sur la Container App (une fois) :

```bash
# PAT GitHub avec scope read:packages (Settings → Developer settings → Personal access tokens)
export GHCR_USER=xLucasGitHubx
export GHCR_TOKEN=ghp_...   # ne jamais committer
az containerapp registry set \
  --name marketplace-api \
  --resource-group rg-marketplace-ynov \
  --server ghcr.io \
  --username "$GHCR_USER" \
  --password "$GHCR_TOKEN"
```

(`scripts/deploy_azure.sh` accepte déjà `GHCR_USER` / `GHCR_TOKEN` à la **création** de l’app.)

### 6. Vérifier le CD

1. Secrets collés → push (ou merge) sur `main`.
2. Onglet **Actions** : workflow **CI** → jobs `tests` → `image` → `deploy` verts.
3. `curl -s https://marketplace-api.whitepond-81c2f971.swedencentral.azurecontainerapps.io/health`

---

## Création initiale (si l’app n’existe pas encore)

1. Pousser sur `main` : Actions → job `image` vert (image sur GHCR).
2. Paquet GHCR **public** (ou registry credentials, §5).
3. [Azure Cloud Shell](https://shell.azure.com) (bash) :

```bash
git clone https://github.com/xLucasGitHubx/MarketPlace_Ynov.git && cd MarketPlace_Ynov
export API_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "$API_TOKEN"                 # à garder pour la démo
LOCATION=swedencentral ./scripts/deploy_azure.sh
```

4. Puis enchaîner la checklist OIDC (§4) pour les mises à jour automatiques.
5. Si `RequestDisallowedByPolicy`, choisir une région autorisée affichée par le script.

## Image Docker (rappel taille)

```bash
# Prod (défaut) : SPA + ONNX int8, sans torch dans les couches finales
docker build --target runtime-onnx -t marketplace-api:onnx .
docker images marketplace-api:onnx   # viser ≈ ≤ 551 Mo ; + quelques Mo par ONNX catalogue

# Optionnel — catalogue int8 (EfficientNet / MobileNet). KD/student non requis.
python scripts/export_catalog.py
cp models/onnx/efficientnet-b0-int8-static.onnx \
   models/onnx/mobilenet-v3-small-int8-static.onnx \
   artifacts/onnx/
docker build --target runtime-onnx -t marketplace-api:onnx .
```

## Fin de projet

```bash
az group delete --name rg-marketplace-ynov --yes --no-wait     # supprime tout, plus aucune facturation
# Optionnel : supprimer aussi l'App Registration github-marketplace-ynov-cd dans Entra ID
```
