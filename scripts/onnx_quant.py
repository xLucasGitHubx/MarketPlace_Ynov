"""Helpers partagés : export HF → ONNX fp32 et quantization int8 (statique QDQ).

Utilisé par `export_onnx.py` (ResNet-50) et `export_catalog.py` (catalogue multi-modèles).
Calibration sur images Caltech-256 **hors** jeu de test (pas de fuite).
"""

from __future__ import annotations

import csv
import io
import random
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

from app.preprocessing import to_model_input

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "models" / "onnx"
CALTECH_URL = "https://huggingface.co/datasets/ilee0022/Caltech-256/resolve/main/data/test-00000-of-00001.parquet"


def calibration_images(parquet: Path | None, n: int) -> list[Image.Image]:
    """Images Caltech-256 qui ne sont PAS dans le jeu de test (pas de fuite)."""
    import pandas as pd

    src = parquet or io.BytesIO(urllib.request.urlopen(CALTECH_URL, timeout=120).read())  # noqa: S310
    df = pd.read_parquet(src)
    used: set[int] = set()
    manifest = ROOT / "data" / "test_set" / "manifest.csv"
    if manifest.exists():
        with manifest.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["source"] == "caltech":
                    used.add(int(Path(row["fichier"]).stem.rsplit("_", 1)[1]))
    candidates = [i for i in df.index if i not in used]
    picked = random.Random(0).sample(candidates, min(n, len(candidates)))
    return [Image.open(io.BytesIO(df.loc[i, "image"]["bytes"])).convert("RGB") for i in picked]


class ImageCalibrationReader:
    def __init__(self, images: list[Image.Image]):
        self._it = iter([{"pixel_values": to_model_input(im)} for im in images])

    def get_next(self):
        return next(self._it, None)


def export_hf_classifier_fp32(hf_model_id: str, path: Path, cache_dir: str | None) -> None:
    """Exporte un AutoModelForImageClassification Hugging Face en ONNX fp32 (logits)."""
    import torch
    from transformers import AutoModelForImageClassification

    model = AutoModelForImageClassification.from_pretrained(hf_model_id, cache_dir=cache_dir).eval()

    class LogitsOnly(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, pixel_values):
            return self.m(pixel_values=pixel_values).logits

    dummy = torch.randn(1, 3, 224, 224)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        LogitsOnly(model),
        (dummy,),
        str(path),
        input_names=["pixel_values"],
        output_names=["logits"],
        dynamic_axes={"pixel_values": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )


def quantize_int8_dynamic(fp32_or_pre: Path, out: Path) -> None:
    from onnxruntime.quantization import QuantType, quantize_dynamic

    quantize_dynamic(str(fp32_or_pre), str(out), weight_type=QuantType.QInt8)


def quantize_int8_static(pre_path: Path, out: Path, images: list[Image.Image]) -> None:
    from onnxruntime.quantization import (
        CalibrationMethod,
        QuantFormat,
        QuantType,
        quantize_static,
    )

    quantize_static(
        str(pre_path),
        str(out),
        ImageCalibrationReader(images),
        quant_format=QuantFormat.QDQ,
        per_channel=True,
        activation_type=QuantType.QUInt8,
        weight_type=QuantType.QInt8,
        calibrate_method=CalibrationMethod.MinMax,
    )


def preprocess_for_quant(fp32: Path, pre: Path) -> None:
    from onnxruntime.quantization.shape_inference import quant_pre_process

    quant_pre_process(str(fp32), str(pre), skip_symbolic_shape=True)


def compare_logits_vs_pytorch(
    hf_model_id: str,
    onnx_paths: list[Path],
    probe: list[Image.Image],
    cache_dir: str | None,
) -> dict:
    """Rapport taille + écart logits / top-1 vs PyTorch de référence."""
    import onnxruntime as ort
    import torch
    from transformers import AutoModelForImageClassification

    ref = AutoModelForImageClassification.from_pretrained(hf_model_id, cache_dir=cache_dir).eval()
    with torch.inference_mode():
        ref_logits = [
            ref(pixel_values=torch.from_numpy(to_model_input(im))).logits.numpy() for im in probe
        ]

    report: dict = {}
    for path in onnx_paths:
        if not path.is_file():
            continue
        sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        outs = [sess.run(None, {"pixel_values": to_model_input(im)})[0] for im in probe]
        report[path.name] = {
            "taille_mo": round(path.stat().st_size / 1_048_576, 1),
            "ecart_max_logits": round(
                float(max(np.abs(o - r).max() for o, r in zip(outs, ref_logits))), 4
            ),
            "top1_identique": sum(int(o.argmax() == r.argmax()) for o, r in zip(outs, ref_logits))
            / len(probe),
        }
    return report


def export_and_quantize(
    *,
    hf_model_id: str,
    stem: str,
    cache_dir: str | None,
    calib_parquet: Path | None,
    calib_size: int,
    do_dynamic: bool = True,
    out_dir: Path | None = None,
) -> dict:
    """Pipeline complet : fp32 → (dynamique) → int8 statique. Renvoie le rapport de contrôle."""
    directory = out_dir or OUT_DIR
    directory.mkdir(parents=True, exist_ok=True)

    fp32 = directory / f"{stem}-fp32.onnx"
    pre = directory / f"{stem}-fp32-pre.onnx"
    dyn = directory / f"{stem}-int8-dynamic.onnx"
    sta = directory / f"{stem}-int8-static.onnx"

    print(f"  Export fp32 ({hf_model_id}) → {fp32.name} ...")
    export_hf_classifier_fp32(hf_model_id, fp32, cache_dir)
    preprocess_for_quant(fp32, pre)

    paths = [fp32]
    if do_dynamic:
        print(f"  Quantization dynamique → {dyn.name} ...")
        quantize_int8_dynamic(pre, dyn)
        paths.append(dyn)

    print(f"  Quantization statique (calib={calib_size}) → {sta.name} ...")
    calib = calibration_images(calib_parquet, calib_size)
    quantize_int8_static(pre, sta, calib)
    paths.append(sta)
    pre.unlink(missing_ok=True)

    print("  Contrôle sorties vs PyTorch ...")
    report = compare_logits_vs_pytorch(hf_model_id, paths, calib[:8], cache_dir)
    return report
