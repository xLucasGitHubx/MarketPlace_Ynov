"""Itération 4 : export ONNX de ResNet-50 et quantization int8.

Produit dans models/onnx/ :
- resnet50-fp32.onnx         : export direct du modèle PyTorch (même précision) ;
- resnet50-int8-dynamic.onnx : quantization dynamique (poids int8, activations à la volée) ;
- resnet50-int8-static.onnx  : quantization statique QDQ (poids + activations int8),
                               calibrée sur des images HORS jeu de test ;
- export_report.json         : tailles et écart des sorties vs PyTorch.

Usage :
    python scripts/export_onnx.py [--calib-parquet chemin/caltech_test.parquet] [--calib-size 64]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from app.preprocessing import to_model_input  # noqa: E402

OUT_DIR = ROOT / "models" / "onnx"
MODEL_ID = "microsoft/resnet-50"
CALTECH_URL = "https://huggingface.co/datasets/ilee0022/Caltech-256/resolve/main/data/test-00000-of-00001.parquet"


def export_fp32(path: Path, cache_dir: str | None) -> None:
    import torch
    from transformers import AutoModelForImageClassification

    model = AutoModelForImageClassification.from_pretrained(MODEL_ID, cache_dir=cache_dir).eval()

    class LogitsOnly(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, pixel_values):
            return self.m(pixel_values=pixel_values).logits

    dummy = torch.randn(1, 3, 224, 224)
    torch.onnx.export(
        LogitsOnly(model), (dummy,), str(path),
        input_names=["pixel_values"], output_names=["logits"],
        dynamic_axes={"pixel_values": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17, do_constant_folding=True, dynamo=False,
    )


def calibration_images(parquet: Path | None, n: int) -> list[Image.Image]:
    """Images Caltech-256 qui ne sont PAS dans le jeu de test (pas de fuite)."""
    import pandas as pd

    src = parquet or io.BytesIO(urllib.request.urlopen(CALTECH_URL, timeout=120).read())  # noqa: S310
    df = pd.read_parquet(src)
    used = set()
    manifest = ROOT / "data" / "test_set" / "manifest.csv"
    if manifest.exists():
        with manifest.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["source"] == "caltech":
                    used.add(int(Path(row["fichier"]).stem.rsplit("_", 1)[1]))
    candidates = [i for i in df.index if i not in used]
    picked = random.Random(0).sample(candidates, n)
    return [Image.open(io.BytesIO(df.loc[i, "image"]["bytes"])).convert("RGB") for i in picked]


class ImageCalibrationReader:
    def __init__(self, images: list[Image.Image]):
        self._it = iter([{"pixel_values": to_model_input(im)} for im in images])

    def get_next(self):
        return next(self._it, None)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default="models/hf")
    ap.add_argument("--calib-parquet", type=Path, default=None)
    ap.add_argument("--calib-size", type=int, default=64)
    args = ap.parse_args()

    import onnxruntime as ort
    from onnxruntime.quantization import CalibrationMethod, QuantFormat, QuantType, quantize_dynamic, quantize_static
    from onnxruntime.quantization.shape_inference import quant_pre_process

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fp32 = OUT_DIR / "resnet50-fp32.onnx"
    pre = OUT_DIR / "resnet50-fp32-pre.onnx"
    dyn = OUT_DIR / "resnet50-int8-dynamic.onnx"
    sta = OUT_DIR / "resnet50-int8-static.onnx"

    print("1/4 Export fp32 ...")
    export_fp32(fp32, args.cache_dir)
    quant_pre_process(str(fp32), str(pre), skip_symbolic_shape=True)

    print("2/4 Quantization dynamique ...")
    quantize_dynamic(str(pre), str(dyn), weight_type=QuantType.QInt8)

    print(f"3/4 Quantization statique (calibration sur {args.calib_size} images hors test) ...")
    calib = calibration_images(args.calib_parquet, args.calib_size)
    quantize_static(
        str(pre), str(sta), ImageCalibrationReader(calib),
        quant_format=QuantFormat.QDQ, per_channel=True,
        activation_type=QuantType.QUInt8, weight_type=QuantType.QInt8,
        calibrate_method=CalibrationMethod.MinMax,
    )
    pre.unlink(missing_ok=True)

    print("4/4 Contrôle des sorties vs PyTorch ...")
    import torch
    from transformers import AutoModelForImageClassification

    ref = AutoModelForImageClassification.from_pretrained(MODEL_ID, cache_dir=args.cache_dir).eval()
    probe = calib[:8]
    with torch.inference_mode():
        ref_logits = [ref(pixel_values=torch.from_numpy(to_model_input(im))).logits.numpy() for im in probe]

    report = {}
    for path in (fp32, dyn, sta):
        sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        outs = [sess.run(None, {"pixel_values": to_model_input(im)})[0] for im in probe]
        report[path.name] = {
            "taille_mo": round(path.stat().st_size / 1_048_576, 1),
            "ecart_max_logits": round(float(max(np.abs(o - r).max() for o, r in zip(outs, ref_logits))), 4),
            "top1_identique": sum(int(o.argmax() == r.argmax()) for o, r in zip(outs, ref_logits)) / len(probe),
        }
    (OUT_DIR / "export_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
