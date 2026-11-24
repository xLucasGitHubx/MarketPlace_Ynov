"""Project the two jury protocols into a small SPA payload.

Source of truth stays in docs/preuves/eval/. The proxy of 200 photos and the
focus manifest stay in separate accuracies. MobileNet and the student keep no
defended accuracy. ResNet has no score on the focus set.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "docs" / "preuves" / "eval"
OUT = ROOT / "web" / "src" / "data" / "jury-eval.json"
THUMBS = ROOT / "web" / "public" / "jeu"

COMPARE_PROXY = "compare-models-200.json"
COMPARE_FOCUS = "compare-models-focus.json"
QUAL_PROXY = "cas-qualitatifs.json"
QUAL_FOCUS = "cas-qualitatifs-focus.json"

PROXY_CATS = ("Véhicules et pièces", "Jeux et jouets", "Électroménager")
FOCUS_CATS = ("Véhicules et pièces", "Jeux et jouets")
GRID_ORDER = ("Jeux et jouets", "Électroménager")
GRID_CAP = 4

SHORT = {
    "resnet50-onnx-int8": "ResNet",
    "efficientnet-b0-onnx-int8": "EfficientNet",
    "clip-vit-b32": "CLIP",
}
PAIR_PREF = (
    ("efficientnet-b0-onnx-int8", "resnet50-onnx-int8"),
    ("clip-vit-b32", "resnet50-onnx-int8"),
    ("clip-vit-b32", "efficientnet-b0-onnx-int8"),
)


def load(name: str) -> dict:
    return json.loads((EVAL / name).read_text(encoding="utf-8"))


def rows(name: str) -> list[dict]:
    out = []
    with (EVAL / name).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def num(value: object, digits: int = 4) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return round(float(value), digits)


def thumb(fichier: str) -> str | None:
    rel = fichier.replace("\\", "/").lstrip("/")
    if rel.startswith("jeu/"):
        rel = rel[4:]
    stem = rel.rsplit(".", 1)[0]
    webp = f"{stem}.webp"
    if not (THUMBS / webp).is_file():
        return None
    return f"/jeu/{webp}"


def pred_view(model_id: str, row: dict, attendu: str) -> dict:
    predit = row.get("predit")
    top1 = row.get("top1")
    return {
        "id": model_id,
        "label": SHORT.get(model_id, model_id),
        "predit": predit if isinstance(predit, str) else "—",
        "confiance": num(row.get("confiance")),
        "top1": top1 if isinstance(top1, str) and top1 else None,
        "correct": predit == attendu,
    }


def index_preds(name: str) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows(name):
        fichier = row.get("fichier")
        if isinstance(fichier, str):
            indexed[fichier.replace("\\", "/")] = row
    return indexed


def card_from_rows(fichier: str, trio: list[tuple[str, dict]], n_by_cat: dict[str, int]) -> dict | None:
    attendu = trio[0][1].get("attendu")
    if not isinstance(attendu, str):
        return None
    src = thumb(fichier)
    if src is None:
        return None
    return {
        "fichier": fichier,
        "src": src,
        "attendu": attendu,
        "n": n_by_cat.get(attendu),
        "mecanisme": None,
        "commentaire": None,
        "predictions": [pred_view(model_id, row, attendu) for model_id, row in trio],
    }


def interest(card: dict) -> tuple:
    preds = {item["id"]: item for item in card["predictions"]}
    clip = preds.get("clip-vit-b32")
    resnet = preds.get("resnet50-onnx-int8")
    eff = preds.get("efficientnet-b0-onnx-int8")
    clip_ok_cnns_wrong = bool(
        clip
        and resnet
        and eff
        and clip["correct"]
        and not resnet["correct"]
        and not eff["correct"]
    )
    flags = [item["correct"] for item in card["predictions"]]
    split = any(flags) and not all(flags)
    conf_wrong = sum(
        1
        for item in card["predictions"]
        if not item["correct"] and item["confiance"] is not None and item["confiance"] > 0.6
    )
    distinct = len({item["predit"] for item in card["predictions"]})
    return (int(clip_ok_cnns_wrong), int(split), conf_wrong, distinct)


def grid_from_predictions(n_by_cat: dict[str, int]) -> tuple[str, list[dict]]:
    by_model = {
        "resnet50-onnx-int8": index_preds("preds-resnet50-int8-historique-200.jsonl"),
        "efficientnet-b0-onnx-int8": index_preds("preds-efficientnet-b0-int8-200.jsonl"),
        "clip-vit-b32": index_preds("preds-clip-vit-b32-generique-200.jsonl"),
    }
    fichiers = set.intersection(*(set(table) for table in by_model.values()))
    grouped: dict[str, list[dict]] = {label: [] for label in GRID_ORDER}
    counts = {label: 0 for label in GRID_ORDER}
    order = (
        "resnet50-onnx-int8",
        "efficientnet-b0-onnx-int8",
        "clip-vit-b32",
    )
    for fichier in sorted(fichiers):
        trio = [(model_id, by_model[model_id][fichier]) for model_id in order]
        attendus = {row.get("attendu") for _, row in trio}
        if len(attendus) != 1:
            continue
        attendu = next(iter(attendus))
        if attendu not in grouped:
            continue
        predits = {row.get("predit") for _, row in trio}
        if len(predits) < 2:
            continue
        counts[attendu] += 1
        card = card_from_rows(fichier, trio, n_by_cat)
        if card is not None:
            grouped[attendu].append(card)

    groupes = []
    for label in GRID_ORDER:
        ranked = sorted(grouped[label], key=lambda card: card["fichier"])
        ranked.sort(key=interest, reverse=True)
        groupes.append(
            {
                "attendu": label,
                "n": n_by_cat.get(label),
                "desaccords": counts[label],
                "items": ranked[:GRID_CAP],
            }
        )
    source = "predictions" if any(group["items"] for group in groupes) else "absent"
    return source, groupes


def qualitative_predictions(item: dict, attendu: str) -> list[dict]:
    order = (
        "resnet50-onnx-int8",
        "efficientnet-b0-onnx-int8",
        "clip-vit-b32",
    )
    found: dict[str, dict] = {}
    for key in ("modeles", "models", "predictions", "preds", "reponses"):
        block = item.get(key)
        if isinstance(block, dict):
            for model_id, row in block.items():
                if isinstance(row, dict):
                    found[str(model_id)] = row
        elif isinstance(block, list):
            for row in block:
                if not isinstance(row, dict):
                    continue
                model_id = row.get("id") or row.get("model_id")
                if isinstance(model_id, str):
                    found[model_id] = row
    views = []
    for model_id in order:
        row = found.get(model_id)
        if row is None:
            continue
        views.append(pred_view(model_id, row, attendu))
    return views


def grid_from_qualitative(path: Path, n_by_cat: dict[str, int]) -> list[dict] | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(doc, list):
        cases = doc
    elif isinstance(doc, dict):
        cases = None
        for key in ("cas", "cases", "items", "vignettes", "desaccords"):
            if isinstance(doc.get(key), list):
                cases = doc[key]
                break
    else:
        cases = None
    if not cases:
        return None
    grouped: dict[str, list[dict]] = {}
    for item in cases:
        if not isinstance(item, dict):
            continue
        fichier = item.get("fichier") or item.get("file") or item.get("path")
        attendu = item.get("attendu") or item.get("categorie_attendue") or item.get("expected")
        if not isinstance(fichier, str) or not isinstance(attendu, str):
            continue
        src = thumb(fichier)
        if src is None:
            continue
        texte = item.get("texte") or item.get("commentaire") or item.get("note")
        mecanisme = item.get("mecanisme")
        grouped.setdefault(attendu, []).append(
            {
                "fichier": fichier.replace("\\", "/"),
                "src": src,
                "attendu": attendu,
                "n": n_by_cat.get(attendu),
                "mecanisme": mecanisme if isinstance(mecanisme, str) else None,
                "commentaire": texte if isinstance(texte, str) else None,
                "predictions": qualitative_predictions(item, attendu),
            }
        )
    if not grouped:
        return None
    labels = [label for label in GRID_ORDER if label in grouped]
    labels.extend(label for label in grouped if label not in labels)
    return [
        {
            "attendu": label,
            "n": n_by_cat.get(label),
            "desaccords": len(grouped[label]),
            "items": grouped[label][:12],
        }
        for label in labels
    ]


def role_of(card: dict) -> str:
    preds = {item["id"]: item for item in card["predictions"]}
    eff = preds.get("efficientnet-b0-onnx-int8")
    clip = preds.get("clip-vit-b32")
    if not eff or not clip:
        return "autre"
    if card["attendu"] == "Véhicules et pièces" and eff["correct"] and not clip["correct"]:
        return "eff_juste_clip_faux"
    if card["attendu"] == "Jeux et jouets" and clip["correct"] and not eff["correct"]:
        return "clip_juste_eff_faux"
    if not eff["correct"] and not clip["correct"]:
        return "double_echec"
    confident = any(
        (not item["correct"]) and item["confiance"] is not None and item["confiance"] > 0.6
        for item in (eff, clip)
    )
    if confident or card.get("mecanisme") == "erreur_confiante":
        return "erreur_confiante"
    return "autre"


def reorder_focus(groupes: list[dict]) -> list[dict]:
    rank = {
        "eff_juste_clip_faux": 0,
        "clip_juste_eff_faux": 0,
        "erreur_confiante": 1,
        "double_echec": 2,
        "autre": 3,
    }
    by_label = {group["attendu"]: group for group in groupes}
    ordered = []
    for label in FOCUS_CATS:
        group = by_label.get(label)
        if group is None:
            continue
        group["items"].sort(key=lambda card: (rank[role_of(card)], card["fichier"]))
        ordered.append(group)
    for group in groupes:
        if group["attendu"] not in FOCUS_CATS:
            ordered.append(group)
    return ordered


def focus_roles_present(groupes: list[dict]) -> bool:
    found = {role_of(card) for group in groupes for card in group["items"]}
    return {
        "eff_juste_clip_faux",
        "clip_juste_eff_faux",
        "erreur_confiante",
        "double_echec",
    }.issubset(found)


def grid_from_focus_jsonl(n_by_cat: dict[str, int]) -> list[dict]:
    by_model = {
        "efficientnet-b0-onnx-int8": index_preds("preds-efficientnet-b0-int8-focus.jsonl"),
        "clip-vit-b32": index_preds("preds-clip-vit-b32-generique-focus.jsonl"),
    }
    fichiers = set.intersection(*(set(table) for table in by_model.values()))
    grouped: dict[str, list[dict]] = {label: [] for label in FOCUS_CATS}
    order = ("efficientnet-b0-onnx-int8", "clip-vit-b32")
    for fichier in sorted(fichiers):
        if "focus_caltech_" not in fichier:
            continue
        pair = [(model_id, by_model[model_id][fichier]) for model_id in order]
        attendus = {row.get("attendu") for _, row in pair}
        if len(attendus) != 1:
            continue
        attendu = next(iter(attendus))
        if attendu not in grouped:
            continue
        card = card_from_rows(fichier, pair, n_by_cat)
        if card is None:
            continue
        if role_of(card) == "autre":
            continue
        grouped[attendu].append(card)
    groupes = [
        {
            "attendu": label,
            "n": n_by_cat.get(label),
            "desaccords": len(grouped[label]),
            "items": sorted(grouped[label], key=lambda card: card["fichier"])[:8],
        }
        for label in FOCUS_CATS
        if grouped[label]
    ]
    return reorder_focus(groupes)


def model_row(
    model_id: str,
    label: str,
    short: str,
    *,
    role: str,
    accuracy: float | None,
    n: int | None,
    metric_source: str,
    qualifier: str,
    p50_ms: float | None,
    banc: str | None,
    raison_id: str | None,
    scores: dict[str, float | None] | None = None,
) -> dict:
    return {
        "id": model_id,
        "label": label,
        "short": short,
        "role": role,
        "accuracy": accuracy,
        "n": n,
        "metric_source": metric_source,
        "qualifier": qualifier,
        "p50_ms": p50_ms,
        "banc": banc,
        "raison_id": raison_id,
        "scores": scores or {},
    }


def accord_rows(compare: dict, pairs: tuple[tuple[str, str], ...]) -> list[dict]:
    accords_by_pair = {}
    for row in compare["accord"]:
        accords_by_pair[(row["modele_a"], row["modele_b"])] = row
        accords_by_pair[(row["modele_b"], row["modele_a"])] = row
    accord = []
    for left, right in pairs:
        global_row = accords_by_pair[(left, right)]["global"]
        accord.append(
            {
                "modele_a": left,
                "modele_b": right,
                "label_a": SHORT[left],
                "label_b": SHORT[right],
                "n": global_row["n"],
                "part_meme_categorie": num(global_row["part_meme_categorie"]),
                "desaccord": global_row["desaccord"],
            }
        )
    return accord


def category_table(compare: dict, model_ids: tuple[str, ...], labels: tuple[str, ...]) -> dict[str, int]:
    n_by_cat: dict[str, int] = {}
    for label in labels:
        ns = []
        for model_id in model_ids:
            block = compare["modeles"][model_id]["categories_focales"][label]
            ns.append(int(block["n"]))
        if len(set(ns)) != 1:
            raise SystemExit(f"n diverge pour {label}: {ns}")
        n_by_cat[label] = ns[0]
    return n_by_cat


def score_map(compare: dict, model_id: str, labels: tuple[str, ...]) -> dict[str, float | None]:
    scores: dict[str, float | None] = {}
    for label in labels:
        block = compare["modeles"][model_id]["categories_focales"][label]
        scores[label] = num(block["accuracy"])
    return scores


def main() -> None:
    proxy = load(COMPARE_PROXY)
    focus = load(COMPARE_FOCUS)
    catalog = load("catalog_metrics.json")
    eff_proxy = load("eval-efficientnet-b0-int8-static-200.json")
    clip_proxy = load("eval-clip-vocab-generique-200.json")
    resnet_eval = load("eval-onnx-int8-static.json")
    eff_focus = load("eval-efficientnet-b0-int8-static-focus.json")
    clip_focus = load("eval-clip-vocab-generique-focus.json")
    clip_detail = load("eval-clip-vocab-detaille.json")
    proxy_models = proxy["modeles"]
    focus_models = focus["modeles"]

    proxy_n = category_table(
        proxy,
        ("resnet50-onnx-int8", "efficientnet-b0-onnx-int8", "clip-vit-b32"),
        PROXY_CATS,
    )
    focus_n = category_table(
        focus,
        ("efficientnet-b0-onnx-int8", "clip-vit-b32"),
        FOCUS_CATS,
    )

    comparable = [
        model_row(
            "resnet50-onnx-int8",
            "ResNet-50 int8",
            "ResNet",
            role="comparable",
            accuracy=num(proxy_models["resnet50-onnx-int8"]["accuracy"]),
            n=proxy_models["resnet50-onnx-int8"]["n"],
            metric_source="measured",
            qualifier="historique it. 4",
            p50_ms=num(resnet_eval["latence_p50_ms"], 1),
            banc="it4",
            raison_id=None,
        ),
        model_row(
            "efficientnet-b0-onnx-int8",
            "EfficientNet-B0 int8",
            "EfficientNet",
            role="comparable",
            accuracy=num(proxy_models["efficientnet-b0-onnx-int8"]["accuracy"]),
            n=proxy_models["efficientnet-b0-onnx-int8"]["n"],
            metric_source="measured",
            qualifier="ce run, jeu proxy",
            p50_ms=num(eff_proxy["latence_p50_ms"], 1),
            banc="ce_run",
            raison_id=None,
        ),
        model_row(
            "clip-vit-b32",
            "CLIP ViT-B/32 vocab générique",
            "CLIP générique",
            role="comparable",
            accuracy=num(proxy_models["clip-vit-b32"]["accuracy"]),
            n=proxy_models["clip-vit-b32"]["n"],
            metric_source="measured",
            qualifier="zero-shot, vocab générique",
            p50_ms=num(clip_proxy["latence_p50_ms"], 1),
            banc="ce_run_clip",
            raison_id=None,
        ),
    ]

    excluded_specs = (
        ("mobilenet-v3-small-onnx-int8", "MobileNetV3-Small int8", "MobileNet", "int8_ecarte"),
        ("student-kd-mobilenet-int8", "Student KD", "Student", "student_absent"),
    )
    excluded = []
    for model_id, label, short, raison_id in excluded_specs:
        metrics = catalog["models"][model_id]
        measured = metrics.get("metric_source") == "measured"
        excluded.append(
            model_row(
                model_id,
                label,
                short,
                role="comparable" if measured else "hors_resultat",
                accuracy=num(metrics.get("accuracy")) if measured else None,
                n=metrics.get("n_images") if measured else None,
                metric_source="measured" if measured else "excluded",
                qualifier="ce run" if measured else "pas un résultat",
                p50_ms=num(metrics.get("p50_ms"), 1) if measured else None,
                banc="ce_run" if measured else None,
                raison_id=None if measured else raison_id,
            )
        )

    focus_rows = [
        model_row(
            "efficientnet-b0-onnx-int8",
            "EfficientNet-B0 int8",
            "EfficientNet",
            role="comparable",
            accuracy=num(focus_models["efficientnet-b0-onnx-int8"]["accuracy"]),
            n=focus_models["efficientnet-b0-onnx-int8"]["n"],
            metric_source="measured",
            qualifier="ce run, jeu focal",
            p50_ms=num(eff_focus["latence_p50_ms"], 1),
            banc="ce_run",
            raison_id=None,
            scores=score_map(focus, "efficientnet-b0-onnx-int8", FOCUS_CATS),
        ),
        model_row(
            "clip-vit-b32",
            "CLIP ViT-B/32 vocab générique",
            "CLIP générique",
            role="comparable",
            accuracy=num(focus_models["clip-vit-b32"]["accuracy"]),
            n=focus_models["clip-vit-b32"]["n"],
            metric_source="measured",
            qualifier="zero-shot, vocab générique",
            p50_ms=num(clip_focus["latence_p50_ms"], 1),
            banc="ce_run_clip",
            raison_id=None,
            scores=score_map(focus, "clip-vit-b32", FOCUS_CATS),
        ),
        model_row(
            "resnet50-onnx-int8",
            "ResNet-50 int8",
            "ResNet",
            role="absent",
            accuracy=None,
            n=None,
            metric_source="unmeasured",
            qualifier="fichier ONNX absent",
            p50_ms=None,
            banc=None,
            raison_id="onnx_absent",
            scores={label: None for label in FOCUS_CATS},
        ),
    ]

    focus_groups = None
    focus_qual = EVAL / QUAL_FOCUS
    if focus_qual.is_file():
        focus_groups = grid_from_qualitative(focus_qual, focus_n)
    vignettes_source = "focus"
    if not focus_groups or not focus_roles_present(focus_groups):
        focus_groups = grid_from_focus_jsonl(focus_n)
        vignettes_source = "predictions"
    else:
        focus_groups = reorder_focus(focus_groups)
    if not focus_roles_present(focus_groups):
        raise SystemExit("Grille focale incomplète : véhicule, jouet, erreur confiante ou double échec manquant.")

    proxy_qual = EVAL / QUAL_PROXY
    archive_groups = grid_from_qualitative(proxy_qual, proxy_n) if proxy_qual.is_file() else None
    archive_source = "cas-qualitatifs" if archive_groups else None
    if archive_groups is None:
        archive_source, archive_groups = grid_from_predictions(proxy_n)

    clip_proxy_veh = proxy_models["clip-vit-b32"]["categories_focales"]["Véhicules et pièces"]
    clip_focus_veh = focus_models["clip-vit-b32"]["categories_focales"]["Véhicules et pièces"]
    clip_metrics = catalog["models"]["clip-vit-b32"]
    payload = {
        "source": [
            f"docs/preuves/eval/{COMPARE_FOCUS}",
            f"docs/preuves/eval/{COMPARE_PROXY}",
        ],
        "seuil": focus["seuil"],
        "avertissement_n20": {
            "modele": "CLIP générique",
            "categorie": "Véhicules et pièces",
            "n_proxy": int(clip_proxy_veh["n"]),
            "accuracy_proxy": num(clip_proxy_veh["accuracy"]),
            "n_focal": int(clip_focus_veh["n"]),
            "accuracy_focal": num(clip_focus_veh["accuracy"]),
        },
        "clip_detaille": {
            "accuracy": num(clip_detail["accuracy"]),
            "n": clip_detail["n_images"],
            "headline": False,
            "taille_mo": num(clip_metrics.get("size_mb"), 1),
        },
        "protocoles": [
            {
                "id": "focal",
                "titre": "Jeu focal",
                "detail": "Manifest séparé, 100 Véhicules + 100 Jeux, Caltech seulement.",
                "n": focus["n_manifest"],
                "headline": True,
                "categories": [{"label": label, "n": focus_n[label]} for label in FOCUS_CATS],
                "models": focus_rows,
                "accord": accord_rows(
                    focus,
                    (("clip-vit-b32", "efficientnet-b0-onnx-int8"),),
                ),
            },
            {
                "id": "proxy",
                "titre": "Jeu proxy",
                "detail": "200 photos, 20 × 10. Autre manifeste que le jeu focal.",
                "n": proxy["n_manifest"],
                "headline": False,
                "categories": [{"label": label, "n": proxy_n[label]} for label in PROXY_CATS],
                "models": comparable + excluded,
                "accord": accord_rows(proxy, PAIR_PREF),
            },
        ],
        "vignettes_source": vignettes_source,
        "groupes": focus_groups,
        "archive_proxy": {
            "vignettes_source": archive_source,
            "groupes": archive_groups,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shown = sum(len(group["items"]) for group in focus_groups)
    print(
        f"wrote {OUT.relative_to(ROOT)} source={vignettes_source} cards={shown} "
        f"archive={archive_source}"
    )


if __name__ == "__main__":
    main()
