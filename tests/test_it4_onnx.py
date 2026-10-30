"""Itération 4 : backend ONNX Runtime et prétraitement numpy."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.preprocessing import to_model_input

ort = pytest.importorskip("onnxruntime")
onnx = pytest.importorskip("onnx")


@pytest.fixture
def tiny_onnx_model(tmp_path: Path) -> Path:
    """Mini-modèle ONNX (moyenne globale + couche linéaire) : mêmes entrées/sorties que ResNet-50."""
    from onnx import TensorProto, helper, numpy_helper

    w = numpy_helper.from_array(np.random.default_rng(0).normal(size=(3, 1000)).astype(np.float32), "W")
    axes = numpy_helper.from_array(np.array([2, 3], dtype=np.int64), "axes")
    graph = helper.make_graph(
        [
            helper.make_node("ReduceMean", ["pixel_values", "axes"], ["pooled"], keepdims=0),
            helper.make_node("MatMul", ["pooled", "W"], ["logits"]),
        ],
        "tiny",
        [helper.make_tensor_value_info("pixel_values", TensorProto.FLOAT, ["batch", 3, 224, 224])],
        [helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["batch", 1000])],
        initializer=[w, axes],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 18)], ir_version=9)
    path = tmp_path / "resnet50-int8-static.onnx"
    onnx.save(model, path)
    return path


@pytest.mark.parametrize("size", [(640, 480), (480, 640), (224, 224), (1000, 300)])
def test_to_model_input_forme_et_normalisation(size):
    arr = to_model_input(Image.new("RGB", size, (124, 116, 104)))  # ≈ moyenne ImageNet
    assert arr.shape == (1, 3, 224, 224)
    assert arr.dtype == np.float32
    assert np.abs(arr).max() < 0.02  # une image « moyenne » donne ~0 après normalisation


def test_onnx_predictor_renvoie_des_probabilites(tiny_onnx_model):
    from app.model import OnnxPredictor

    p = OnnxPredictor(str(tiny_onnx_model))
    probs = p.predict_proba(Image.new("RGB", (300, 200), (10, 200, 30)))
    assert probs.shape == (1000,)
    assert probs.sum() == pytest.approx(1.0, abs=1e-5)
    assert p.name == "resnet50-onnx-int8-static"


def test_api_avec_backend_onnx(make_client, tiny_onnx_model, jpeg_bytes):
    from app.model import load_predictor

    c = make_client(load_predictor("onnx", onnx_path=str(tiny_onnx_model)))
    r = c.post("/predict", files={"file": ("x.jpg", jpeg_bytes, "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["modele"] == "resnet50-onnx-int8-static"


def test_backend_inconnu():
    from app.model import load_predictor

    with pytest.raises(ValueError):
        load_predictor("tensorflow")


@pytest.mark.skipif(not os.getenv("MODEL_CACHE_DIR"), reason="nécessite le modèle HF en cache (MODEL_CACHE_DIR)")
def test_pretraitement_numpy_identique_a_huggingface():
    from transformers import AutoImageProcessor

    proc = AutoImageProcessor.from_pretrained("microsoft/resnet-50", cache_dir=os.environ["MODEL_CACHE_DIR"])
    rng = np.random.default_rng(1)
    for size in [(640, 480), (333, 777), (224, 224)]:
        img = Image.fromarray((rng.random((size[1], size[0], 3)) * 255).astype("uint8"))
        ref = proc(images=img, return_tensors="np")["pixel_values"]
        np.testing.assert_allclose(to_model_input(img), ref, atol=1e-5)
