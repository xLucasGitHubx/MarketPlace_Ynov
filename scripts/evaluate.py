"""Évalue un backend de modèle sur le jeu de test étiqueté.

Mesure : accuracy catégorie (globale et par catégorie), taux de statut `auto`,
précision quand `auto`, latence d'inférence (p50/p95) et balayage du seuil de
confiance pour le calibrer. Les mêmes images servent à comparer les backends.

Usage :
    python scripts/evaluate.py --backend pytorch
    python scripts/evaluate.py --backend onnx --onnx-path models/onnx/resnet50-int8-static.onnx --mlflow
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from app.business import STATUS_AUTO, suggest  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.model import load_predictor  # noqa: E402
from app.monitoring import slug  # noqa: E402

TEST_DIR = ROOT / "data" / "test_set"
EVAL_EXPERIMENT = "marketplace-evaluation"
THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def load_manifest(test_dir: Path) -> list[dict]:
    with (test_dir / "manifest.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def evaluate_predictor(predictor, suggest_fn, threshold: float, test_dir: Path = TEST_DIR, warmup: int = 3) -> dict:
    """Évaluation générique : `suggest_fn(probs, threshold)` renvoie une Suggestion (business.py)."""
    rows = load_manifest(test_dir)
    images = [Image.open(test_dir / r["fichier"]).convert("RGB") for r in rows]
    for img in images[:warmup]:
        predictor.predict_proba(img)

    latencies, records = [], []
    for row, img in zip(rows, images):
        t0 = time.perf_counter()
        probs = predictor.predict_proba(img)
        latencies.append((time.perf_counter() - t0) * 1000)
        records.append({"row": row, "probs": probs})

    def score(t: float) -> dict:
        n = len(records)
        correct = auto = auto_correct = 0
        per_cat: dict[str, list[int]] = {}
        errors = []
        for rec in records:
            s = suggest_fn(rec["probs"], t)
            truth = rec["row"]["categorie"]
            ok = s.category == truth
            correct += ok
            per_cat.setdefault(truth, [0, 0])
            per_cat[truth][0] += ok
            per_cat[truth][1] += 1
            if s.status == STATUS_AUTO:
                auto += 1
                auto_correct += ok
            if not ok:
                errors.append({"fichier": rec["row"]["fichier"], "attendu": truth, "predit": s.category,
                               "confiance": s.confidence, "top1": s.top3[0]["label"]})
        return {
            "seuil": t,
            "accuracy": correct / n,
            "taux_auto": auto / n,
            "precision_auto": (auto_correct / auto) if auto else 0.0,
            "par_categorie": {k: round(v[0] / v[1], 3) for k, v in sorted(per_cat.items())},
            "erreurs": errors,
        }

    default = score(threshold)
    return {
        "modele": predictor.name,
        "n_images": len(records),
        "accuracy": round(default["accuracy"], 4),
        "taux_auto": round(default["taux_auto"], 4),
        "precision_auto": round(default["precision_auto"], 4),
        "seuil": threshold,
        "latence_p50_ms": round(statistics.median(latencies), 1),
        "latence_p95_ms": round(percentile(latencies, 95), 1),
        "latence_moy_ms": round(statistics.mean(latencies), 1),
        "par_categorie": default["par_categorie"],
        "balayage_seuil": [
            {k: round(v, 4) if isinstance(v, float) else v for k, v in score(t).items()
             if k in ("seuil", "taux_auto", "precision_auto")}
            for t in THRESHOLDS
        ],
        "erreurs": default["erreurs"],
    }


def model_size_mb(backend: str, onnx_path: str | None, cache_dir: str | None) -> float | None:
    if backend == "onnx":
        return round(Path(onnx_path).stat().st_size / 1_048_576, 1)
    files = list(Path(cache_dir or Path.home() / ".cache/huggingface/hub").rglob("*resnet-50*/**/model.safetensors"))
    return round(files[0].resolve().stat().st_size / 1_048_576, 1) if files else None


def evaluate(backend: str, test_dir: Path = TEST_DIR, top_k: int = 5, warmup: int = 3,
             onnx_path: str | None = None) -> dict:
    from app.model import DEFAULT_ONNX_PATH

    settings = get_settings()
    onnx_path = onnx_path or settings.onnx_model_path or DEFAULT_ONNX_PATH
    predictor = load_predictor(backend, cache_dir=settings.model_cache_dir, hf_token=settings.hf_token,
                               onnx_path=onnx_path)
    res = evaluate_predictor(
        predictor, lambda p, t: suggest(p, threshold=t, top_k=top_k), settings.confidence_threshold, test_dir, warmup
    )
    res.update({"backend": backend, "top_k": top_k,
                "taille_modele_mo": model_size_mb(backend, onnx_path, settings.model_cache_dir)})
    return res


def log_to_mlflow(res: dict, tracking_uri: str, extra_params: dict | None = None) -> str:
    """Un run par évaluation dans l'expérience « marketplace-evaluation »."""
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(EVAL_EXPERIMENT)
    with mlflow.start_run(run_name=res["modele"]) as run:
        params = {"modele": res["modele"], "backend": res.get("backend"), "n_images": res["n_images"],
                  "seuil": res["seuil"], "top_k": res.get("top_k"), "jeu_de_test": "proxy-sop-caltech-200"}
        params.update(extra_params or {})
        mlflow.log_params({k: v for k, v in params.items() if v is not None})
        metrics = {k: res[k] for k in ("accuracy", "taux_auto", "precision_auto", "latence_p50_ms",
                                       "latence_p95_ms", "latence_moy_ms")}
        if res.get("taille_modele_mo"):
            metrics["taille_modele_mo"] = res["taille_modele_mo"]
        metrics.update({f"acc_{slug(k)}": v for k, v in res["par_categorie"].items()})
        mlflow.log_metrics(metrics)
        for i, row in enumerate(res["balayage_seuil"]):  # courbe précision / taux auto selon le seuil
            mlflow.log_metrics({"balayage_precision_auto": row["precision_auto"],
                                "balayage_taux_auto": row["taux_auto"]}, step=int(row["seuil"] * 100))
        mlflow.log_dict(res, "evaluation.json")
        mlflow.set_tags({"type": "evaluation"})
        return run.info.run_id


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default=get_settings().model_backend)
    ap.add_argument("--test-dir", type=Path, default=TEST_DIR)
    ap.add_argument("--top-k", type=int, default=get_settings().top_k)
    ap.add_argument("--onnx-path", default=None, help="modèle ONNX à évaluer (backend onnx)")
    ap.add_argument("--out", type=Path, default=None, help="fichier JSON de résultats")
    ap.add_argument("--mlflow", action="store_true", help="journalise le run dans MLflow")
    ap.add_argument("--tracking-uri", default=os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
    args = ap.parse_args()

    res = evaluate(args.backend, args.test_dir, args.top_k, onnx_path=args.onnx_path)
    summary = {k: v for k, v in res.items() if k != "erreurs"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n{len(res['erreurs'])} erreurs (détail dans --out)")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.mlflow:
        run_id = log_to_mlflow(res, args.tracking_uri)
        print(f"Run MLflow {run_id} -> {args.tracking_uri}")


if __name__ == "__main__":
    main()
