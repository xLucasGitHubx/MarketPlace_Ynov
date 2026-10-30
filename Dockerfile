# syntax=docker/dockerfile:1.7
# Itération 3 — image PyTorch (modèle de référence), build multi-stage.
ARG BASE_IMAGE=python:3.11-slim

# ---------- Étape 1 : dépendances + téléchargement du modèle ----------
FROM ${BASE_IMAGE} AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
# Secret optionnel « ca_bundle » : certificat d'un proxy d'entreprise (TLS intercepté).
# Absent par défaut ; jamais copié dans l'image.
COPY requirements.txt /tmp/
RUN --mount=type=secret,id=ca_bundle,required=false \
    if [ -f /run/secrets/ca_bundle ]; then export PIP_CERT=/run/secrets/ca_bundle; fi \
 && pip install -r /tmp/requirements.txt \
 && pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.*" \
 && pip install "transformers>=4.44,<5"
COPY scripts/download_model.py /tmp/
# Le token HF (optionnel) passe par un secret de build : il n'est jamais écrit dans une couche.
RUN --mount=type=secret,id=hf_token,required=false \
    --mount=type=secret,id=ca_bundle,required=false \
    if [ -f /run/secrets/ca_bundle ]; then export REQUESTS_CA_BUNDLE=/run/secrets/ca_bundle SSL_CERT_FILE=/run/secrets/ca_bundle; fi \
 && HF_TOKEN="$(cat /run/secrets/hf_token 2>/dev/null || true)" \
    python /tmp/download_model.py --cache-dir /models

# ---------- Étape 2 : image d'exécution ----------
FROM ${BASE_IMAGE} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    MODEL_BACKEND=pytorch MODEL_CACHE_DIR=/models \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN useradd --create-home --uid 1000 appuser
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=appuser /models /models
WORKDIR /srv
COPY --chown=appuser app/ app/
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=4).status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
