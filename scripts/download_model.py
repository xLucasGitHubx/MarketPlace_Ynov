"""Télécharge le modèle Hugging Face dans un dossier local (utilisé au build Docker).

Usage : python scripts/download_model.py --cache-dir /models
Le token HF est lu dans HF_TOKEN (optionnel : microsoft/resnet-50 est public).
"""

from __future__ import annotations

import argparse
import os

from transformers import AutoImageProcessor, AutoModelForImageClassification

MODEL_ID = "microsoft/resnet-50"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--model-id", default=MODEL_ID)
    args = ap.parse_args()
    token = os.getenv("HF_TOKEN") or None
    AutoImageProcessor.from_pretrained(args.model_id, cache_dir=args.cache_dir, token=token)
    AutoModelForImageClassification.from_pretrained(args.model_id, cache_dir=args.cache_dir, token=token)
    print(f"{args.model_id} téléchargé dans {args.cache_dir}")


if __name__ == "__main__":
    main()
