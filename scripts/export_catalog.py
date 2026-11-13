"""Export ONNX int8 statique du catalogue multi-modèles (hors ResNet déjà couvert).

Modèles ciblés (IDs catalogue Phase 1) :
- efficientnet-b0-onnx-int8  ← HF google/efficientnet-b0
- mobilenet-v3-small-onnx-int8 ← HF facebook/mobilenet_v3_small

Produit dans models/onnx/ pour chaque stem :
- {stem}-fp32.onnx
- {stem}-int8-static.onnx   (retenu prod / registre)
- optionnel {stem}-int8-dynamic.onnx si --dynamic
- catalog_export_report.json

Le student KD (`student-kd-mobilenet-int8`) est produit par `scripts/distill_student.py`,
pas par ce script.

Usage :
    python scripts/export_catalog.py
    python scripts/export_catalog.py --only efficientnet-b0
    python scripts/export_catalog.py --cache-dir models/hf --calib-size 64
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

# Aligné sur app.registry.CATALOG (onnx_filenames *int8-static*).
CATALOG_EXPORTS: tuple[dict, ...] = (
    {
        "catalog_id": "efficientnet-b0-onnx-int8",
        "hf_model_id": "google/efficientnet-b0",
        "stem": "efficientnet-b0",
    },
    {
        "catalog_id": "mobilenet-v3-small-onnx-int8",
        "hf_model_id": "facebook/mobilenet_v3_small",
        "stem": "mobilenet-v3-small",
    },
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Export ONNX int8 du catalogue (EfficientNet / MobileNet)")
    ap.add_argument("--cache-dir", default="models/hf")
    ap.add_argument("--calib-parquet", type=Path, default=None)
    ap.add_argument("--calib-size", type=int, default=64)
    ap.add_argument(
        "--only",
        choices=[e["stem"] for e in CATALOG_EXPORTS],
        default=None,
        help="Exporter un seul stem (défaut : tous)",
    )
    ap.add_argument(
        "--dynamic",
        action="store_true",
        help="Aussi produire l'int8 dynamique (lent / peu utile pour CNN, défaut off)",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=OUT_DIR,
        help="Répertoire de sortie ONNX (défaut models/onnx/)",
    )
    args = ap.parse_args()

    targets = [e for e in CATALOG_EXPORTS if args.only is None or e["stem"] == args.only]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    full_report: dict = {"models": {}}
    for entry in targets:
        print(f"\n=== {entry['catalog_id']} ({entry['hf_model_id']}) ===")
        try:
            report = export_and_quantize(
                hf_model_id=entry["hf_model_id"],
                stem=entry["stem"],
                cache_dir=args.cache_dir,
                calib_parquet=args.calib_parquet,
                calib_size=args.calib_size,
                do_dynamic=args.dynamic,
                out_dir=args.out_dir,
            )
            full_report["models"][entry["catalog_id"]] = {
                "hf_model_id": entry["hf_model_id"],
                "stem": entry["stem"],
                "status": "ok",
                "files": report,
            }
        except Exception as exc:
            print(f"  ÉCHEC : {exc}")
            full_report["models"][entry["catalog_id"]] = {
                "hf_model_id": entry["hf_model_id"],
                "stem": entry["stem"],
                "status": "error",
                "error": str(exc),
            }

    report_path = args.out_dir / "catalog_export_report.json"
    report_path.write_text(json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRapport → {report_path}")
    print(json.dumps(full_report, indent=2, ensure_ascii=False))

    failed = [k for k, v in full_report["models"].items() if v.get("status") != "ok"]
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
