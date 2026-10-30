"""Chargement et inférence du modèle de vision.

Interface commune `Predictor` : chaque backend reçoit une image PIL RGB et renvoie
le vecteur de probabilités (softmax) sur les 1000 classes ImageNet. La logique
métier (business.py) ne dépend que de ce vecteur, ce qui permet de changer de
backend (PyTorch, ONNX, plus tard CLIP) sans toucher au reste de l'API.

Les imports lourds (torch, transformers, onnxruntime) sont faits dans chaque
backend : l'image Docker ONNX n'embarque pas PyTorch.
"""

from __future__ import annotations

import logging
from typing import Protocol

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

HF_MODEL_ID = "microsoft/resnet-50"


def softmax(logits: np.ndarray) -> np.ndarray:
    z = logits - logits.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


class Predictor(Protocol):
    name: str

    def predict_proba(self, image: Image.Image) -> np.ndarray: ...


class PytorchPredictor:
    """Modèle de référence : ResNet-50 PyTorch fp32 depuis Hugging Face."""

    def __init__(self, model_id: str = HF_MODEL_ID, cache_dir: str | None = None, hf_token: str | None = None):
        import torch
        from transformers import AutoImageProcessor, AutoModelForImageClassification

        self._torch = torch
        torch.set_num_threads(max(1, torch.get_num_threads()))
        self.processor = AutoImageProcessor.from_pretrained(model_id, cache_dir=cache_dir, token=hf_token)
        self.model = AutoModelForImageClassification.from_pretrained(model_id, cache_dir=cache_dir, token=hf_token)
        self.model.eval()
        self.name = "resnet50-pytorch-fp32"
        logger.info("Modèle chargé : %s (%s)", model_id, self.name)

    def predict_proba(self, image: Image.Image) -> np.ndarray:
        inputs = self.processor(images=image, return_tensors="pt")
        with self._torch.inference_mode():
            logits = self.model(**inputs).logits
        probs = softmax(logits.numpy()[0])
        del inputs, logits  # purge explicite des tenseurs
        return probs


def load_predictor(backend: str, **kwargs) -> Predictor:
    backend = backend.lower()
    if backend == "pytorch":
        return PytorchPredictor(
            cache_dir=kwargs.get("cache_dir"),
            hf_token=kwargs.get("hf_token"),
        )
    raise ValueError(f"MODEL_BACKEND inconnu : {backend!r} (attendu : pytorch)")
