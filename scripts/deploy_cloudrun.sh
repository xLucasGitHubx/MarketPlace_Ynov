#!/usr/bin/env bash
# Itération 7 — déploiement de l'image ONNX sur Google Cloud Run.
#
# Prérequis : gcloud installé et connecté (gcloud auth login), un projet GCP avec
# facturation activée, Docker. Le token d'API est stocké dans Secret Manager,
# jamais dans l'image ni dans la ligne de commande du service.
#
# Usage :
#   export PROJECT_ID=mon-projet-gcp
#   export API_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
#   ./scripts/deploy_cloudrun.sh
#
# Variables optionnelles : REGION (europe-west9 = Paris), SERVICE, REPO, MIN_INSTANCES (0 = scale à zéro).
set -euo pipefail

: "${PROJECT_ID:?définir PROJECT_ID}"
REGION="${REGION:-europe-west9}"
SERVICE="${SERVICE:-marketplace-api}"
REPO="${REPO:-marketplace}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:$(git rev-parse --short HEAD)"

echo "==> Projet ${PROJECT_ID}, région ${REGION}, image ${IMAGE}"
gcloud config set project "${PROJECT_ID}" >/dev/null
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

echo "==> Registry Artifact Registry"
gcloud artifacts repositories describe "${REPO}" --location "${REGION}" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "${REPO}" --repository-format docker --location "${REGION}"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo "==> Build et push de l'image ONNX (linux/amd64)"
docker build --platform linux/amd64 --target runtime-onnx -t "${IMAGE}" .
docker push "${IMAGE}"

echo "==> Secret API_TOKEN dans Secret Manager"
if [ -n "${API_TOKEN:-}" ]; then
  if gcloud secrets describe api-token >/dev/null 2>&1; then
    printf "%s" "${API_TOKEN}" | gcloud secrets versions add api-token --data-file=-
  else
    printf "%s" "${API_TOKEN}" | gcloud secrets create api-token --data-file=- --replication-policy automatic
  fi
fi
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format 'value(projectNumber)')
gcloud secrets add-iam-policy-binding api-token \
  --member "serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role roles/secretmanager.secretAccessor >/dev/null

echo "==> Déploiement Cloud Run"
# 1 vCPU / 1 Gio : l'image ONNX tient dans 160 Mo de RAM au repos.
# concurrency 4 : sur 1 vCPU, p95 ≈ 280 ms à 4 requêtes simultanées, ≈ 500 ms à 8 (docs/preuves/it5-charge.md).
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --cpu 1 --memory 1Gi \
  --concurrency 4 \
  --min-instances "${MIN_INSTANCES}" --max-instances 10 \
  --timeout 30 \
  --set-env-vars MODEL_BACKEND=onnx \
  --set-secrets API_TOKEN=api-token:latest \
  --allow-unauthenticated \
  --port 8000

URL=$(gcloud run services describe "${SERVICE}" --region "${REGION}" --format 'value(status.url)')
echo
echo "==> Déployé : ${URL}"
echo "    curl ${URL}/health"
echo "    curl -H \"Authorization: Bearer \$API_TOKEN\" -F file=@photo.jpg ${URL}/predict"
# --allow-unauthenticated : l'accès réseau est public, mais /predict exige le Bearer token de l'API.
