# Image prod Azure — multi-stage slim, ONNX-only, SPA embarquée.
#
#   docker build --target runtime-onnx -t marketplace-api:onnx .
#
# Stages :
#   web-build     node:22-alpine → assets SPA (dist/ uniquement vers le runtime)
#   deps-*        venv API (+ onnxruntime) ; PyTorch uniquement dans les stages d'export
#   model-onnx    export ResNet-50 int8 (torch ne traverse PAS l'image finale)
#   onnx-collect  ResNet exporté + éventuels *.onnx pré-buildés (catalogue)
#   runtime-onnx  python:3.11-slim + onnxruntime + app + SPA + ONNX int8  (défaut / Azure)
#   runtime-pytorch  référence it.3 uniquement — ne pas déployer sur Azure
#
# Catalogue EfficientNet / MobileNet / student :
#   1. Hors Docker : python scripts/export_catalog.py (et/ou distill_student.py)
#   2. Copier les *.onnx int8 dans artifacts/onnx/ avant le build
#      (ex. efficientnet-b0-int8-static.onnx, mobilenet-v3-small-int8-static.onnx)
#   3. docker build … — ils sont COPYés dans /models sans torch dans le runtime
#   Alternative : --build-arg PREBUILT_ONNX_DIR=models/onnx si les fichiers sont déjà là
#   (et .dockerignore autorise ce chemin).
#
# Portable : pas de syntaxe BuildKit (RUN --mount). Proxy TLS optionnel :
#   --build-arg EXTRA_CA_CERT_B64="$(base64 -w0 proxy-ca.pem)"
ARG BASE_IMAGE=python:3.11-slim
ARG NODE_IMAGE=node:22-alpine
ARG PREBUILT_ONNX_DIR=artifacts/onnx

# ---------- SPA React/Vite (assets statiques uniquement) ----------
FROM ${NODE_IMAGE} AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
# Pas de sourcemaps dans l'image prod (poids).
RUN npx tsc -b && npx vite build --sourcemap false

# ---------- Dépendances de l'API (communes) ----------
FROM ${BASE_IMAGE} AS deps-base
ARG EXTRA_CA_CERT_B64=""
RUN cp /etc/ssl/certs/ca-certificates.crt /opt/build-ca.pem \
 && if [ -n "$EXTRA_CA_CERT_B64" ]; then echo "$EXTRA_CA_CERT_B64" | base64 -d >> /opt/build-ca.pem; fi
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PATH=/opt/venv/bin:$PATH \
    PIP_CERT=/opt/build-ca.pem REQUESTS_CA_BUNDLE=/opt/build-ca.pem SSL_CERT_FILE=/opt/build-ca.pem
RUN python -m venv /opt/venv
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

# ---------- Runtime ONNX : + onnxruntime uniquement ----------
FROM deps-base AS deps-onnx
COPY requirements-onnx.txt /tmp/
RUN pip install -r /tmp/requirements-onnx.txt

# ---------- PyTorch + transformers (export / référence — jamais dans runtime-onnx) ----------
FROM deps-base AS deps-torch
RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.*" \
 && pip install "transformers>=4.44,<5"

# ---------- Téléchargement du modèle Hugging Face (public) ----------
FROM deps-torch AS model-hf
COPY scripts/download_model.py /tmp/
RUN python /tmp/download_model.py --cache-dir /models

# ---------- Export ONNX ResNet + quantization int8 statique ----------
FROM model-hf AS model-onnx
COPY requirements-export.txt /tmp/
RUN pip install -r /tmp/requirements-export.txt pandas pyarrow
WORKDIR /build
COPY app/ app/
COPY scripts/export_onnx.py scripts/
COPY data/test_set/manifest.csv data/test_set/
RUN HF_HUB_OFFLINE=1 python scripts/export_onnx.py --cache-dir /models \
 && cat models/onnx/export_report.json

# ---------- Bundle ONNX int8 : ResNet exporté + pré-buildés catalogue ----------
FROM ${BASE_IMAGE} AS onnx-collect
ARG PREBUILT_ONNX_DIR=artifacts/onnx
WORKDIR /models
# Dossier hôte versionné (souvent vide hors .gitkeep) : EfficientNet, MobileNet, student…
COPY ${PREBUILT_ONNX_DIR}/ ./
# ResNet prod toujours fourni par l'étape d'export (chemin historique conservé)
COPY --from=model-onnx /build/models/onnx/resnet50-int8-static.onnx ./resnet50-int8-static.onnx
# Ne garder que les int8 utiles (pas de fp32 / dynamic / rapports JSON)
RUN find . -type f ! -name '*.onnx' -delete 2>/dev/null || true \
 && find . -type f \( -name '*-fp32.onnx' -o -name '*-int8-dynamic.onnx' \) -delete 2>/dev/null || true \
 && ls -la

# ---------- Socle d'exécution commun ----------
FROM ${BASE_IMAGE} AS runtime-base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/venv/bin:$PATH
RUN useradd --create-home --uid 1000 appuser
WORKDIR /srv
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=4).status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------- Cible : PyTorch (référence it. 3 — pas pour Azure) ----------
FROM runtime-base AS runtime-pytorch
ENV MODEL_BACKEND=pytorch MODEL_CACHE_DIR=/models HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
COPY --from=deps-torch /opt/venv /opt/venv
COPY --from=model-hf --chown=appuser /models /models
COPY --chown=appuser app/ app/
COPY --from=web-build --chown=appuser /web/dist/ app/static/
USER appuser

# ---------- Cible : ONNX Runtime int8 + SPA (prod Azure) — défaut ----------
FROM runtime-base AS runtime-onnx
ENV MODEL_BACKEND=onnx \
    ONNX_MODEL_PATH=/models/resnet50-int8-static.onnx \
    ONNX_MODELS_DIR=/models \
    AZURE_RUNTIME=false \
    DEFAULT_MODEL_ID=resnet50-onnx-int8
COPY --from=deps-onnx /opt/venv /opt/venv
COPY --from=onnx-collect --chown=appuser /models/ /models/
COPY --chown=appuser app/ app/
COPY --from=web-build --chown=appuser /web/dist/ app/static/
# Métriques FinOps / GET /models (fichier versionné, sans secrets)
COPY --chown=appuser docs/preuves/eval/catalog_metrics.json docs/preuves/eval/catalog_metrics.json
USER appuser
