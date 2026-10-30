#!/usr/bin/env bash
# Itération 7 — déploiement sur Azure Container Apps (abonnement Azure for Students).
#
# L'image n'est PAS construite dans Azure : les abonnements gratuits/étudiants ne
# peuvent pas utiliser ACR Tasks (`az acr build` -> TasksOperationsNotAllowed), et un
# registre ACR Basic coûterait ~5 $/mois. C'est la CI GitHub Actions qui construit
# l'image ONNX et la publie sur GitHub Container Registry (gratuit) ;
# Azure Container Apps la tire directement depuis ghcr.io.
#
# Le plus simple : Azure Cloud Shell (bash), où `az` est déjà installé et connecté.
#   git clone https://github.com/xLucasGitHubx/MarketPlace_Ynov.git && cd MarketPlace_Ynov
#   export API_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
#   ./scripts/deploy_azure.sh
#
# Variables optionnelles :
#   LOCATION       région (défaut francecentral ; un abonnement étudiant n'autorise que certaines régions)
#   RG, ENV_NAME, APP     noms des ressources
#   IMAGE          image à déployer (défaut : ghcr.io/xlucasgithubx/marketplace_ynov:latest)
#   GHCR_USER / GHCR_TOKEN  si le paquet GHCR est privé (token GitHub avec read:packages)
#   CPU / MEMORY   défaut 1.0 / 2.0Gi (mesures de docs/preuves/it5-charge.md) ; 0.5 / 1.0Gi divise le coût par 2
#   MIN_REPLICAS   0 = scale à zéro (défaut) ; 1 = pas de démarrage à froid (≈ 23 $/mois au tarif « repos »)
set -euo pipefail

: "${API_TOKEN:?définir API_TOKEN (python3 -c \"import secrets; print(secrets.token_urlsafe(32))\")}"
LOCATION="${LOCATION:-francecentral}"
RG="${RG:-rg-marketplace-ynov}"
ENV_NAME="${ENV_NAME:-cae-marketplace}"
APP="${APP:-marketplace-api}"
IMAGE="${IMAGE:-ghcr.io/xlucasgithubx/marketplace_ynov:latest}"
CPU="${CPU:-1.0}"
MEMORY="${MEMORY:-2.0Gi}"
MIN_REPLICAS="${MIN_REPLICAS:-0}"
MAX_REPLICAS="${MAX_REPLICAS:-3}"

az account show --query "{abonnement:name, id:id}" -o table || { echo "Lancer d'abord : az login"; exit 1; }

echo "==> Fournisseurs de ressources (une seule fois par abonnement)"
for p in Microsoft.App Microsoft.OperationalInsights; do
  az provider register --namespace "$p" --wait
done

echo "==> Groupe de ressources ${RG} (${LOCATION})"
if ! az group create --name "$RG" --location "$LOCATION" -o none; then
  echo "Échec : la région ${LOCATION} est peut-être interdite par la politique de l'abonnement étudiant."
  echo "Régions autorisées :"
  az policy assignment list --query "[].parameters.listOfAllowedLocations.value" -o tsv 2>/dev/null || true
  echo "Relancer avec : LOCATION=<région autorisée> ./scripts/deploy_azure.sh"
  exit 1
fi

echo "==> Environnement Container Apps ${ENV_NAME} (crée aussi un espace Log Analytics)"
az containerapp env show --name "$ENV_NAME" --resource-group "$RG" -o none 2>/dev/null || \
  az containerapp env create --name "$ENV_NAME" --resource-group "$RG" --location "$LOCATION" -o none

REGISTRY_ARGS=()
if [ -n "${GHCR_TOKEN:-}" ]; then
  REGISTRY_ARGS=(--registry-server ghcr.io --registry-username "${GHCR_USER:?GHCR_USER requis avec GHCR_TOKEN}"
                 --registry-password "$GHCR_TOKEN")
fi

if az containerapp show --name "$APP" --resource-group "$RG" -o none 2>/dev/null; then
  echo "==> Mise à jour de ${APP} -> ${IMAGE}"
  az containerapp secret set --name "$APP" --resource-group "$RG" --secrets "api-token=${API_TOKEN}" -o none
  az containerapp update --name "$APP" --resource-group "$RG" --image "$IMAGE" \
    --cpu "$CPU" --memory "$MEMORY" --min-replicas "$MIN_REPLICAS" --max-replicas "$MAX_REPLICAS" \
    --set-env-vars API_TOKEN=secretref:api-token MODEL_BACKEND=onnx \
    --revision-suffix "r$(date +%m%d%H%M)" -o none
else
  echo "==> Création de ${APP} -> ${IMAGE}"
  # concurrency 4 : sur 1 vCPU, p95 ≈ 280 ms à 4 requêtes simultanées (docs/preuves/it5-charge.md) ;
  # au-delà, Container Apps ajoute une réplique plutôt que d'allonger la file.
  az containerapp create --name "$APP" --resource-group "$RG" --environment "$ENV_NAME" \
    --image "$IMAGE" "${REGISTRY_ARGS[@]}" \
    --target-port 8000 --ingress external \
    --cpu "$CPU" --memory "$MEMORY" \
    --min-replicas "$MIN_REPLICAS" --max-replicas "$MAX_REPLICAS" \
    --scale-rule-name http-concurrency --scale-rule-type http --scale-rule-http-concurrency 4 \
    --secrets "api-token=${API_TOKEN}" \
    --env-vars API_TOKEN=secretref:api-token MODEL_BACKEND=onnx -o none
fi

URL="https://$(az containerapp show --name "$APP" --resource-group "$RG" --query properties.configuration.ingress.fqdn -o tsv)"
echo "==> Attente du démarrage (démarrage à froid possible si MIN_REPLICAS=0)"
for _ in $(seq 1 30); do
  if curl -sf "${URL}/health" >/dev/null; then break; fi
  sleep 5
done
curl -s "${URL}/health"; echo
echo
echo "Déployé : ${URL}"
echo "  Swagger : ${URL}/docs"
echo "  curl -H \"Authorization: Bearer \$API_TOKEN\" -F file=@photo.jpg ${URL}/predict"
echo
echo "Pour tout supprimer (et arrêter toute facturation) : az group delete --name ${RG} --yes --no-wait"
