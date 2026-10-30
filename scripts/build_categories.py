"""Génère app/categories.json à partir du mapping manuel data/imagenet_mapping.tsv.

Le JSON produit contient les 1000 classes ImageNet (label anglais, catégorie
d'annonce, titre suggéré en français). Il est versionné : l'API n'a pas besoin
de ce script à l'exécution.

Usage : python scripts/build_categories.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TSV = ROOT / "data" / "imagenet_mapping.tsv"
OUT = ROOT / "app" / "categories.json"

CODES = {
    "E": "Électronique",
    "M": "Maison et meubles",
    "A": "Électroménager",
    "V": "Vêtements et accessoires",
    "S": "Sport et loisirs",
    "J": "Jeux et jouets",
    "H": "Véhicules et pièces",
    "B": "Bricolage et jardin",
    "L": "Livres et musique",
}
OTHER = "Autre"


def load_imagenet_labels() -> dict[int, str]:
    """Labels ImageNet tels que définis dans la config du modèle microsoft/resnet-50."""
    from transformers import AutoConfig

    cfg = AutoConfig.from_pretrained("microsoft/resnet-50")
    return {int(k): v for k, v in cfg.id2label.items()}


def main() -> None:
    labels = load_imagenet_labels()
    mapping: dict[int, tuple[str, str]] = {}
    for line in TSV.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        idx, code, title = line.split("\t")
        if code not in CODES:
            raise ValueError(f"Code inconnu {code!r} pour la classe {idx}")
        mapping[int(idx)] = (CODES[code], title.strip())

    classes = []
    for idx in range(len(labels)):
        label = labels[idx].split(",")[0].strip()
        category, title = mapping.get(idx, (OTHER, label[:1].upper() + label[1:]))
        classes.append({"id": idx, "label": label, "categorie": category, "titre": title})

    payload = {
        "version": "1.0",
        "source": "ImageNet-1k (microsoft/resnet-50) — mapping manuel data/imagenet_mapping.tsv",
        "categories": list(CODES.values()) + [OTHER],
        "classes": classes,
    }
    # Une classe par ligne : fichier lisible et diffs Git propres
    head = {k: v for k, v in payload.items() if k != "classes"}
    lines = json.dumps(head, ensure_ascii=False, indent=2)[:-2]
    body = ",\n".join("    " + json.dumps(c, ensure_ascii=False) for c in classes)
    OUT.write_text(f'{lines},\n  "classes": [\n{body}\n  ]\n}}\n', encoding="utf-8")
    json.loads(OUT.read_text(encoding="utf-8"))  # garde-fou : JSON valide

    counts: dict[str, int] = {}
    for c in classes:
        counts[c["categorie"]] = counts.get(c["categorie"], 0) + 1
    print(f"{OUT.relative_to(ROOT)} : {len(classes)} classes")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:<26} {n}")


if __name__ == "__main__":
    main()
