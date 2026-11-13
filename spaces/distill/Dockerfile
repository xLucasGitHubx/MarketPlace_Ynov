# Space Hugging Face — distillation ZeroGPU (PAS l'image Azure prod).
# Prod Azure = Dockerfile racine (python:3.11-slim + onnxruntime uniquement).
#
# Build context attendu : racine du dépôt MarketPlace_Ynov
#   docker build -f spaces/distill/Dockerfile -t marketplace-distill .
#
# Sur le Space Lulu18 : hardware ZeroGPU ; lancer scripts/distill_student.py
# (voir docs/preuves/it-hf-space.md).

FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/data/hf \
    TRANSFORMERS_CACHE=/data/hf

WORKDIR /app

# Ne pas réinstaller torch CPU : la base image fournit CUDA + torch.
# Export ONNX optionnel après KD (quantize sur CPU dans le même conteneur).
COPY requirements-export.txt /tmp/requirements-export.txt
RUN pip install "transformers>=4.44,<5" "numpy>=1.26,<3" "pandas>=2.2" \
        "pyarrow>=15" "Pillow>=10" \
 && pip install -r /tmp/requirements-export.txt

COPY app/ app/
COPY scripts/distill_student.py scripts/export_onnx.py scripts/
COPY data/test_set/manifest.csv data/test_set/manifest.csv
COPY spaces/distill/README.md /app/SPACE_README.md

# Dry-run par défaut (safe). Sur le Space, override la commande :
#   python scripts/distill_student.py --epochs 2 --max-minutes 35 ...
CMD ["python", "scripts/distill_student.py", "--dry-run"]
