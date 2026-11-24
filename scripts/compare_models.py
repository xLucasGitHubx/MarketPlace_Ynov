"""Compare des prédictions déjà produites par app.business.suggest.

Les JSONL d'entrée viennent de scripts/evaluate.py ou scripts/benchmark_clip.py
(--predictions). La catégorie et la confiance sont celles de suggest() ; le statut
`auto` est recalculé avec la même règle (confiance >= seuil).

Usage :
    python scripts/compare_models.py \
        --predictions docs/preuves/eval/preds-efficientnet-b0-int8-200.jsonl \
                      docs/preuves/eval/preds-clip-vit-b32-generique-200.jsonl \
        --manifest data/test_set/manifest.csv \
        --out docs/preuves/eval/compare-models-200.json

    python scripts/compare_models.py \
        --predictions docs/preuves/eval/preds-efficientnet-b0-int8-focus.jsonl \
                      docs/preuves/eval/preds-clip-vit-b32-generique-focus.jsonl \
        --manifest data/test_set/focus_manifest.csv \
        --out docs/preuves/eval/compare-models-focus.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.business import STATUS_AUTO, load_category_map  # noqa: E402

FOCAL = ("Véhicules et pièces", "Jeux et jouets", "Électroménager")


def _as_prediction_list(path: Path, data: object) -> list[dict]:
    if isinstance(data, dict):
        data = data.get("predictions")
    if not isinstance(data, list):
        raise SystemExit(f"{path} : liste de prédictions attendue")
    return data


def load_predictions(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if path.suffix == ".json" or text[0] == "[":
        return _as_prediction_list(path, json.loads(text))
    try:
        return _as_prediction_list(path, json.loads(text))
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]


def load_manifest(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def group_by_model(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        model_id = row.get("model_id") or row.get("modele")
        if not model_id:
            raise SystemExit("Prédiction sans model_id")
        groups.setdefault(str(model_id), []).append(row)
    return groups


def align(preds: list[dict], manifest: list[dict] | None) -> tuple[list[dict], list[str]]:
    """Aligne les prédictions sur le manifeste. L'attendu du manifeste fait foi."""
    by_file: dict[str, dict] = {}
    for row in preds:
        by_file[row["fichier"]] = row
    source = manifest if manifest is not None else preds
    aligned: list[dict] = []
    missing: list[str] = []
    for row in source:
        fichier = row["fichier"]
        attendu = row["categorie"] if manifest is not None else row["attendu"]
        pred = by_file.get(fichier)
        if pred is None:
            missing.append(fichier)
            continue
        raw_conf = pred.get("confiance")
        aligned.append({
            "fichier": fichier,
            "attendu": attendu,
            "predit": pred["predit"],
            "confiance": None if raw_conf is None else float(raw_conf),
            "top1": pred.get("top1") or "",
            "origine": pred.get("origine"),
        })
    return aligned, missing


def is_auto(confidence: float, threshold: float) -> bool:
    """Même règle que suggest() : statut auto si la confiance atteint le seuil."""
    return confidence >= threshold


def rates(rows: list[dict], threshold: float) -> dict:
    n = len(rows)
    if n == 0:
        return {"n": 0, "accuracy": None, "taux_auto": None, "precision_auto": None}
    correct = sum(row["predit"] == row["attendu"] for row in rows)
    result = {"n": n, "accuracy": round(correct / n, 4)}
    if any(row["confiance"] is None for row in rows):
        result["taux_auto"] = None
        result["precision_auto"] = None
        result["confiance_connue"] = sum(row["confiance"] is not None for row in rows)
        return result
    auto = auto_correct = 0
    for row in rows:
        if is_auto(row["confiance"], threshold):
            auto += 1
            auto_correct += int(row["predit"] == row["attendu"])
    result["taux_auto"] = round(auto / n, 4)
    result["precision_auto"] = round(auto_correct / auto, 4) if auto else 0.0
    return result


def confusion(rows: list[dict]) -> dict:
    cmap = load_category_map()
    seen = {row["attendu"] for row in rows} | {row["predit"] for row in rows}
    labels = list(cmap.categories)
    labels += sorted(seen - set(labels))
    matrix = {attendu: {predit: 0 for predit in labels} for attendu in labels}
    for row in rows:
        attendu, predit = row["attendu"], row["predit"]
        if attendu not in matrix:
            labels.append(attendu)
            for line in matrix.values():
                line[attendu] = 0
            matrix[attendu] = {label: 0 for label in labels}
        if predit not in matrix[attendu]:
            labels.append(predit)
            for line in matrix.values():
                line[predit] = 0
        matrix[attendu][predit] += 1
    return {"labels": labels, "lignes_attendu": matrix}


def _confident_part(errors: list[dict], threshold: float) -> dict:
    n_err = len(errors)
    known = [row for row in errors if row["confiance"] is not None]
    if n_err and len(known) != n_err:
        return {"n_erreurs": n_err, "n_erreurs_confiance_gt_seuil": None, "part": None}
    n_conf = sum(1 for row in known if row["confiance"] > threshold)
    return {
        "n_erreurs": n_err,
        "n_erreurs_confiance_gt_seuil": n_conf,
        "part": round(n_conf / n_err, 4) if n_err else None,
    }


def confident_errors(rows: list[dict], threshold: float) -> dict:
    errors = [row for row in rows if row["predit"] != row["attendu"]]
    per_cat = {
        category: _confident_part([row for row in errors if row["attendu"] == category], threshold)
        for category in FOCAL
    }
    return {
        "seuil": threshold,
        "comparaison": "confiance > seuil",
        **_confident_part(errors, threshold),
        "par_categorie": per_cat,
    }


def agreement(left: list[dict], right: list[dict]) -> dict:
    right_by_file = {row["fichier"]: row for row in right}
    n = same = both_wrong = disagree = 0
    for row in left:
        other = right_by_file.get(row["fichier"])
        if other is None:
            continue
        n += 1
        if row["predit"] == other["predit"]:
            same += 1
        else:
            disagree += 1
        if row["predit"] != row["attendu"] and other["predit"] != row["attendu"]:
            both_wrong += 1
    return {
        "n": n,
        "meme_categorie": same,
        "part_meme_categorie": round(same / n, 4) if n else None,
        "les_deux_faux": both_wrong,
        "part_les_deux_faux": round(both_wrong / n, 4) if n else None,
        "desaccord": disagree,
        "part_desaccord": round(disagree / n, 4) if n else None,
    }


def focal_slice(rows: list[dict], category: str) -> list[dict]:
    return [row for row in rows if row["attendu"] == category]


def model_report(rows: list[dict], threshold: float) -> dict:
    report = rates(rows, threshold)
    origines = sorted({row.get("origine") for row in rows if row.get("origine")})
    if origines:
        report["origine"] = origines[0] if len(origines) == 1 else origines
    report["par_categorie"] = {}
    report["categories_focales"] = {}
    seen = sorted({row["attendu"] for row in rows})
    for category in seen:
        report["par_categorie"][category] = rates(focal_slice(rows, category), threshold)
    for category in FOCAL:
        report["categories_focales"][category] = rates(focal_slice(rows, category), threshold)
    report["matrice_confusion"] = confusion(rows)
    report["erreurs_confiantes"] = confident_errors(rows, threshold)
    return report


def build_report(groups: dict[str, list[dict]], manifest: list[dict] | None, manifest_path: Path | None,
                 threshold: float) -> dict:
    aligned: dict[str, list[dict]] = {}
    missing: dict[str, list[str]] = {}
    for model_id, preds in groups.items():
        rows, absent = align(preds, manifest)
        aligned[model_id] = rows
        missing[model_id] = absent
    ids = sorted(aligned)
    accord = []
    for index, left_id in enumerate(ids):
        for right_id in ids[index + 1:]:
            block = {
                "modele_a": left_id,
                "modele_b": right_id,
                "global": agreement(aligned[left_id], aligned[right_id]),
                "par_categorie": {
                    category: agreement(
                        focal_slice(aligned[left_id], category),
                        focal_slice(aligned[right_id], category),
                    )
                    for category in FOCAL
                },
            }
            accord.append(block)
    n_manifest = len(manifest) if manifest is not None else None
    return {
        "seuil": threshold,
        "logique": (
            "Catégorie et confiance issues de app.business.suggest (top-k cumulé). "
            "Statut auto recalculé ici : confiance >= seuil. "
            "Part d'erreurs confiantes : confiance > seuil."
        ),
        "manifest": str(manifest_path) if manifest_path else None,
        "n_manifest": n_manifest,
        "modeles": {
            model_id: {
                **model_report(rows, threshold),
                "manquants": missing[model_id],
            }
            for model_id, rows in aligned.items()
        },
        "accord": accord,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Matrices, catégories focales et accord entre modèles")
    ap.add_argument("--predictions", type=Path, nargs="+", required=True, help="JSONL ou JSON de prédictions suggest()")
    ap.add_argument("--manifest", type=Path, default=None,
                    help="CSV fichier,categorie (défaut : aucun filtre). Ex. data/test_set/focus_manifest.csv")
    ap.add_argument("--threshold", type=float, default=0.6)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rows: list[dict] = []
    for path in args.predictions:
        rows.extend(load_predictions(path))
    manifest = load_manifest(args.manifest) if args.manifest else None
    report = build_report(group_by_model(rows), manifest, args.manifest, args.threshold)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        mid: {
            "n": block["n"],
            "accuracy": block["accuracy"],
            "taux_auto": block["taux_auto"],
            "precision_auto": block["precision_auto"],
            "part_erreurs_confiance_gt_seuil": block["erreurs_confiantes"]["part"],
            "focales": {
                cat: {k: block["categories_focales"][cat][k] for k in ("n", "accuracy", "taux_auto", "precision_auto")}
                for cat in FOCAL
            },
        }
        for mid, block in report["modeles"].items()
    }
    print(json.dumps({"out": str(args.out), "modeles": summary, "n_paires": len(report["accord"])},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
