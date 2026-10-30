"""Évalue un backend de modèle sur le jeu de test étiqueté.

Mesure : accuracy catégorie (globale et par catégorie), taux de statut `auto`,
précision quand `auto`, latence d'inférence (p50/p95) et balayage du seuil de
confiance pour le calibrer. Les mêmes images servent à comparer les backends.

Usage :
    python scripts/evaluate.py --backend pytorch
    python scripts/evaluate.py --backend onnx --mlflow   # (itération 8)
"""

from __future__ import annotations

import argparse
import csv
import json
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

TEST_DIR = ROOT / "data" / "test_set"
THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def load_manifest(test_dir: Path) -> list[dict]:
    with (test_dir / "manifest.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def evaluate(backend: str, test_dir: Path = TEST_DIR, top_k: int = 5, warmup: int = 3,
             onnx_path: str | None = None) -> dict:
    settings = get_settings()
    onnx_path = onnx_path or settings.onnx_model_path
    predictor = load_predictor(backend, cache_dir=settings.model_cache_dir, hf_token=settings.hf_token, onnx_path=onnx_path)
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

    def score(threshold: float) -> dict:
        n = len(records)
        correct = auto = auto_correct = 0
        per_cat: dict[str, list[int]] = {}
        errors = []
        for rec in records:
            s = suggest(rec["probs"], threshold=threshold, top_k=top_k)
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
            "seuil": threshold,
            "accuracy": correct / n,
            "taux_auto": auto / n,
            "precision_auto": (auto_correct / auto) if auto else 0.0,
            "par_categorie": {k: round(v[0] / v[1], 3) for k, v in sorted(per_cat.items())},
            "erreurs": errors,
        }

    default = score(settings.confidence_threshold)
    return {
        "backend": backend,
        "modele": predictor.name,
        "n_images": len(records),
        "top_k": top_k,
        "accuracy": round(default["accuracy"], 4),
        "taux_auto": round(default["taux_auto"], 4),
        "precision_auto": round(default["precision_auto"], 4),
        "seuil": settings.confidence_threshold,
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default=get_settings().model_backend)
    ap.add_argument("--test-dir", type=Path, default=TEST_DIR)
    ap.add_argument("--top-k", type=int, default=get_settings().top_k)
    ap.add_argument("--onnx-path", default=None, help="modèle ONNX à évaluer (backend onnx)")
    ap.add_argument("--out", type=Path, default=None, help="fichier JSON de résultats")
    args = ap.parse_args()

    res = evaluate(args.backend, args.test_dir, args.top_k, onnx_path=args.onnx_path)
    summary = {k: v for k, v in res.items() if k != "erreurs"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n{len(res['erreurs'])} erreurs (détail dans --out)")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
