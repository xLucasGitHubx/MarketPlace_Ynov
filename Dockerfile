# Image de l'API Marketplace — build multi-stage, deux cibles :
#   docker build --target runtime-onnx    -t marketplace-api:onnx .     (défaut, optimisée : it. 4)
#   docker build --target runtime-pytorch -t marketplace-api:pytorch .  (référence : it. 3)
#
# Dockerfile « portable » : aucune syntaxe BuildKit (pas de RUN --mount), il se construit
# aussi bien avec Docker local qu'avec `az acr build` (Azure) ou Podman.
#
# Build derrière un proxy d'entreprise qui intercepte le TLS (optionnel) :
#   --build-arg EXTRA_CA_CERT_B64="$(base64 -w0 proxy-ca.pem)"
# Le certificat ne sert qu'aux étapes de build : il n'est pas copié dans l'image finale.
ARG BASE_IMAGE=python:3.11-slim

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

# ---------- PyTorch + transformers (référence et export) ----------
FROM deps-base AS deps-torch
RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.*" \
 && pip install "transformers>=4.44,<5"

# ---------- Téléchargement du modèle Hugging Face (public : aucun token nécessaire) ----------
FROM deps-torch AS model-hf
COPY scripts/download_model.py /tmp/
RUN python /tmp/download_model.py --cache-dir /models

# ---------- Export ONNX + quantization int8 statique ----------
FROM model-hf AS model-onnx
COPY requirements-export.txt /tmp/
RUN pip install -r /tmp/requirements-export.txt pandas pyarrow
WORKDIR /build
COPY app/ app/
COPY scripts/export_onnx.py scripts/
# Le manifeste du jeu de test sert à exclure ces images de la calibration
COPY data/test_set/manifest.csv data/test_set/
RUN HF_HUB_OFFLINE=1 python scripts/export_onnx.py --cache-dir /models \
 && cat models/onnx/export_report.json

# ---------- Socle d'exécution commun ----------
FROM ${BASE_IMAGE} AS runtime-base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/venv/bin:$PATH
RUN useradd --create-home --uid 1000 appuser
WORKDIR /srv
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=4).status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------- Cible : PyTorch (référence, itération 3) ----------
FROM runtime-base AS runtime-pytorch
ENV MODEL_BACKEND=pytorch MODEL_CACHE_DIR=/models HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
COPY --from=deps-torch /opt/venv /opt/venv
COPY --from=model-hf --chown=appuser /models /models
COPY --chown=appuser app/ app/
USER appuser

# ---------- Cible : ONNX Runtime int8 (optimisée, itération 4) — défaut ----------
FROM runtime-base AS runtime-onnx
ENV MODEL_BACKEND=onnx ONNX_MODEL_PATH=/models/resnet50-int8-static.onnx
COPY --from=deps-onnx /opt/venv /opt/venv
COPY --from=model-onnx --chown=appuser /build/models/onnx/resnet50-int8-static.onnx /models/
COPY --chown=appuser app/ app/
USER appuser
