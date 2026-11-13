"""Itération 4 : export ONNX de ResNet-50 et quantization int8.

Produit dans models/onnx/ :
- resnet50-fp32.onnx         : export direct du modèle PyTorch (même précision) ;
- resnet50-int8-dynamic.onnx : quantization dynamique (poids int8, activations à la volée) ;
- resnet50-int8-static.onnx  : quantization statique QDQ (poids + activations int8),
                               calibrée sur des images HORS jeu de test ;
- export_report.json         : tailles et écart des sorties vs PyTorch.

Pour EfficientNet-B0 / MobileNetV3-Small : `python scripts/export_catalog.py`.

Usage :
    python scripts/export_onnx.py [--calib-parquet chemin/caltech_test.parquet] [--calib-size 64]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from onnx_quant import OUT_DIR, export_and_quantize  # noqa: E402

MODEL_ID = "microsoft/resnet-50"
STEM = "resnet50"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default="models/hf")
    ap.add_argument("--calib-parquet", type=Path, default=None)
    ap.add_argument("--calib-size", type=int, default=64)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("1–4 Export ResNet-50 fp32 + int8 dynamique + int8 statique ...")
    report = export_and_quantize(
        hf_model_id=MODEL_ID,
        stem=STEM,
        cache_dir=args.cache_dir,
        calib_parquet=args.calib_parquet,
        calib_size=args.calib_size,
        do_dynamic=True,
    )
    (OUT_DIR / "export_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
