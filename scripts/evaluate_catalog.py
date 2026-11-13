"""Évalue les modèles ONNX du catalogue et écrit catalog_metrics.json.

Pour chaque ID catalogue dont le fichier int8 est présent sous models/onnx/ :
accuracy + latence (même jeu proxy que evaluate.py) + coût Azure estimé $/M
(formule : baseline ResNet × ratio p95).

Usage :
    python scripts/evaluate_catalog.py
    python scripts/evaluate_catalog.py --seed-only   # régénère le JSON estimé sans inférence
    python scripts/evaluate_catalog.py --out docs/preuves/eval/catalog_metrics.json --mlflow
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from app.business import suggest  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.model import OnnxPredictor  # noqa: E402
from app.registry import (  # noqa: E402
    BASELINE_P95_MS,
    BASELINE_USD_PER_MILLION,
    CATALOG,
    CATALOG_BY_ID,
    DEFAULT_MODEL_ID,
    estimate_cost_usd_per_million,
)
from evaluate import evaluate_predictor, log_to_mlflow  # noqa: E402

DEFAULT_OUT = ROOT / "docs" / "preuves" / "eval" / "catalog_metrics.json"
TEST_DIR = ROOT / "data" / "test_set"
ONNX_DIR = ROOT / "models" / "onnx"

BASELINE_MODEL_ID = DEFAULT_MODEL_ID

# Estimations raisonnables tant que l'export+éval n'a pas tourné localement.
# Sources : tailles ImageNet typiques, ratios de latence CPU CNN, accuracy proxy
# attendue vs ResNet-50 int8 (68,5 %). CLIP = mesures bench existantes (vocab générique).
SEED_ESTIMATES: dict[str, dict] = {
    "resnet50-onnx-int8": {
        "accuracy": 0.685,
        "p50_ms": 21.5,
        "p95_ms": 28.6,
        "size_mb": 24.9,
        "metric_source": "measured",
        "notes": "Mesures it.4 (200 photos proxy) — prod référence",
    },
    "efficientnet-b0-onnx-int8": {
        "accuracy": 0.66,
        "p50_ms": 10.0,
        "p95_ms": 13.0,
        "size_mb": 5.5,
        "metric_source": "estimated",
        "notes": (
            "Estimé : ~5,3 M params, int8 ≈ 5–6 Mo ; latence CPU ~0,45× ResNet-50 ; "
            "accuracy catégorie légèrement sous ResNet (−2 à −3 pts)"
        ),
    },
    "mobilenet-v3-small-onnx-int8": {
        "accuracy": 0.60,
        "p50_ms": 6.5,
        "p95_ms": 9.0,
        "size_mb": 2.5,
        "metric_source": "estimated",
        "notes": (
            "Estimé : ~2,5 M params, int8 ≈ 2–3 Mo ; latence ~0,30× ResNet-50 ; "
            "accuracy proxy plus basse (classes ImageNet moins discriminantes)"
        ),
    },
    "student-kd-mobilenet-int8": {
        "accuracy": 0.64,
        "p50_ms": 7.0,
        "p95_ms": 9.5,
        "size_mb": 2.5,
        "metric_source": "estimated",
        "notes": (
            "Estimé post-KD : latence type MobileNet ; accuracy entre MobileNet brut "
            "et ResNet grâce à la distillation (à remplacer après distill_student.py)"
        ),
    },
    "clip-vit-b32": {
        "accuracy": 0.765,
        "p50_ms": 83.0,
        "p95_ms": 114.0,
        "size_mb": 577.0,
        "metric_source": "measured",
        "notes": "Bench CLIP zero-shot vocab générique ; runtime Space ZeroGPU (pas Azure)",
        "cout_estime_usd_par_million": 0.0,
        "zerogpu_opportunity": True,
    },
}


def _find_onnx(spec) -> Path | None:
    for name in spec.onnx_filenames:
        path = ONNX_DIR / name
        if path.is_file():
            return path
    return None


def _entry_from_eval(catalog_id: str, eval_res: dict, size_mb: float) -> dict:
    p50 = eval_res["latence_p50_ms"]
    p95 = eval_res["latence_p95_ms"]
    return {
        "accuracy": eval_res["accuracy"],
        "p50_ms": p50,
        "p95_ms": p95,
        "size_mb": size_mb,
        "cout_estime_usd_par_million": estimate_cost_usd_per_million(p95),
        "metric_source": "measured",
        "n_images": eval_res["n_images"],
        "taux_auto": eval_res["taux_auto"],
        "precision_auto": eval_res["precision_auto"],
        "notes": f"Évalué via evaluate_catalog.py sur {eval_res['n_images']} images",
    }


def _entry_from_seed(catalog_id: str) -> dict:
    seed = dict(SEED_ESTIMATES[catalog_id])
    if "cout_estime_usd_par_million" not in seed:
        seed["cout_estime_usd_par_million"] = estimate_cost_usd_per_million(seed.get("p95_ms"))
    return seed


def build_metrics_document(models: dict[str, dict], *, mixed: bool) -> dict:
    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "mixed" if mixed else "estimated",
        "schema": {
            "accuracy": "float 0–1, accuracy catégorie proxy (200 photos si measured)",
            "p50_ms": "latence inférence p50 (ms)",
            "p95_ms": "latence inférence p95 (ms)",
            "size_mb": "taille fichier modèle (Mo)",
            "cout_estime_usd_par_million": (
                "USD / million d'images Azure CPU fort volume ; "
                f"formule = {BASELINE_USD_PER_MILLION} × (p95_ms / {BASELINE_P95_MS})"
            ),
            "metric_source": "measured | estimated",
        },
        "finops": {
            "baseline_model_id": BASELINE_MODEL_ID,
            "baseline_p95_ms": BASELINE_P95_MS,
            "baseline_usd_per_million": BASELINE_USD_PER_MILLION,
            "formula": "cout = baseline_usd_per_million * (p95_ms / baseline_p95_ms)",
            "zerogpu_note": (
                "CLIP et jobs lourds : 0 $ crédits école ZeroGPU (40 min/j), "
                "coût d'opportunité = minutes GPU restantes, pas de $/M Azure"
            ),
        },
        "models": models,
    }


def seed_only_document() -> dict:
    models = {mid: _entry_from_seed(mid) for mid in CATALOG_BY_ID}
    return build_metrics_document(models, mixed=False)


def evaluate_available(*, top_k: int, threshold: float, warmup: int) -> dict[str, dict]:
    models: dict[str, dict] = {}
    for spec in CATALOG:
        if spec.space_only:
            models[spec.id] = _entry_from_seed(spec.id)
            continue
        path = _find_onnx(spec)
        if path is None:
            models[spec.id] = _entry_from_seed(spec.id)
            continue
        print(f"Évaluation {spec.id} ← {path} ...")
        predictor = OnnxPredictor(str(path), name=spec.id)
        res = evaluate_predictor(
            predictor,
            lambda p, t: suggest(p, threshold=t, top_k=top_k),
            threshold,
            TEST_DIR,
            warmup,
        )
        size_mb = round(path.stat().st_size / 1_048_576, 1)
        models[spec.id] = _entry_from_eval(spec.id, res, size_mb)
        models[spec.id]["_eval_full"] = res
    return models


def main() -> None:
    settings = get_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--seed-only",
        action="store_true",
        help="Écrit le JSON estimé (ResNet mesuré + estimations) sans charger de modèle",
    )
    ap.add_argument("--top-k", type=int, default=settings.top_k)
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--mlflow", action="store_true")
    ap.add_argument("--tracking-uri", default=os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
    args = ap.parse_args()

    if args.seed_only or not TEST_DIR.exists():
        if not args.seed_only and not TEST_DIR.exists():
            print(f"Jeu de test absent ({TEST_DIR}) → mode seed-only")
        doc = seed_only_document()
        eval_fulls: dict[str, dict] = {}
    else:
        raw = evaluate_available(
            top_k=args.top_k,
            threshold=settings.confidence_threshold,
            warmup=args.warmup,
        )
        eval_fulls = {}
        models = {}
        any_measured = False
        for mid, entry in raw.items():
            full = entry.pop("_eval_full", None)
            if full is not None:
                eval_fulls[mid] = full
            if entry.get("metric_source") == "measured":
                any_measured = True
            models[mid] = entry
        # Si aucun ONNX catalogue évalué, rester sur estimated (seed ResNet inclus).
        mixed = any_measured and any(
            e.get("metric_source") == "estimated" for e in models.values()
        )
        source_measured_only = any_measured and not mixed
        doc = build_metrics_document(models, mixed=mixed or not source_measured_only)
        if source_measured_only:
            doc["source"] = "measured"
        elif mixed:
            doc["source"] = "mixed"
        else:
            doc["source"] = "estimated"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Écrit {args.out}")
    summary = {
        mid: {
            k: v[k]
            for k in (
                "accuracy",
                "p50_ms",
                "p95_ms",
                "size_mb",
                "cout_estime_usd_par_million",
                "metric_source",
            )
            if k in v
        }
        for mid, v in doc["models"].items()
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.mlflow and eval_fulls:
        for mid, res in eval_fulls.items():
            res = dict(res)
            res["backend"] = "onnx"
            res["top_k"] = args.top_k
            res["taille_modele_mo"] = doc["models"][mid].get("size_mb")
            run_id = log_to_mlflow(res, args.tracking_uri, extra_params={"catalog_id": mid})
            print(f"MLflow {mid} → {run_id}")


if __name__ == "__main__":
    main()
