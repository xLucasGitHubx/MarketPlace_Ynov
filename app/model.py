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
from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

HF_MODEL_ID = "microsoft/resnet-50"
DEFAULT_ONNX_PATH = "models/onnx/resnet50-int8-static.onnx"


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


class OnnxPredictor:
    """Modèle optimisé : CNN ImageNet exporté en ONNX (fp32 ou int8), exécuté par ONNX Runtime.

    N'importe ni torch ni transformers : le prétraitement est fait en numpy
    (`to_model_input`, identique à l'AutoImageProcessor, vérifié par les tests).
    """

    def __init__(self, model_path: str, num_threads: int | None = None, name: str | None = None):
        import onnxruntime as ort

        from app.preprocessing import to_model_input

        self._to_input = to_model_input
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        if num_threads:
            opts.intra_op_num_threads = num_threads
        self.session = ort.InferenceSession(model_path, sess_options=opts, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        if name:
            self.name = name
        else:
            stem = Path(model_path).stem  # ex. resnet50-int8-static
            self.name = stem.replace("resnet50-", "resnet50-onnx-")
        logger.info("Modèle ONNX chargé : %s (%s)", model_path, self.name)

    def predict_proba(self, image: Image.Image) -> np.ndarray:
        pixel_values = self._to_input(image)
        logits = self.session.run(None, {self.input_name: pixel_values})[0]
        probs = softmax(logits[0])
        del pixel_values, logits
        return probs


def load_predictor(backend: str, **kwargs) -> Predictor:
    backend = backend.lower()
    if backend == "pytorch":
        return PytorchPredictor(
            cache_dir=kwargs.get("cache_dir"),
            hf_token=kwargs.get("hf_token"),
        )
    if backend == "onnx":
        return OnnxPredictor(kwargs.get("onnx_path") or DEFAULT_ONNX_PATH, num_threads=kwargs.get("num_threads"))
    raise ValueError(f"MODEL_BACKEND inconnu : {backend!r} (attendu : pytorch | onnx)")
