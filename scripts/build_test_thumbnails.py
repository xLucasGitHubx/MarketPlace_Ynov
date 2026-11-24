"""Vignettes WebP du jeu de test déjà figé dans data/test_set/manifest.csv.

Les JPEG d'origine restent gitignorés. Ce script ne réécrit pas le manifeste :
il relit les 200 lignes et ne produit que de petites vignettes pour la SPA.

Sources, les mêmes que scripts/build_test_set.py :
- Caltech-256, split test (un parquet) ;
- Stanford Online Products, uniquement les fichiers cités par le manifeste.

Sortie :
- web/public/jeu/<chemin>.webp
- web/src/parcours/jeuPhotos.json

Usage : python scripts/build_test_thumbnails.py
         python scripts/build_test_thumbnails.py --focus
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "test_set" / "manifest.csv"
PUBLIC = ROOT / "web" / "public" / "jeu"
INDEX = ROOT / "web" / "src" / "parcours" / "jeuPhotos.json"
CACHE = ROOT / "models" / "cache" / "caltech-256-test.parquet"
CALTECH_URL = (
    "https://huggingface.co/datasets/ilee0022/Caltech-256"
    "/resolve/main/data/test-00000-of-00001.parquet"
)
SOP_REPO = (
    "https://huggingface.co/datasets/pawlo2013/StanfordOnlineProducts"
    "/resolve/main/Stanford_Online_Products"
)
MAX_EDGE = 160
WEBP_QUALITY = 55


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310
        return response.read()


def caltech_frame():
    import pandas as pd

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    if not CACHE.is_file():
        CACHE.write_bytes(fetch(CALTECH_URL))
    return pd.read_parquet(CACHE)


def source_bytes(row: dict[str, str], caltech) -> bytes | None:
    filename = Path(row["fichier"]).name
    if row["source"] == "caltech":
        index = int(filename.removesuffix(".jpg").rsplit("_", 1)[1])
        try:
            blob = caltech.loc[index, "image"]["bytes"]
        except KeyError:
            return None
        return bytes(blob)
    stem = filename.removeprefix("sop_").removesuffix(".jpg")
    url = f"{SOP_REPO}/{row['classe_source']}_final/{stem}.JPG"
    try:
        return fetch(url)
    except urllib.error.HTTPError:
        return None


def thumbnail(data: bytes) -> bytes:
    image = Image.open(io.BytesIO(data)).convert("RGB")
    image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    image.save(out, format="WEBP", quality=WEBP_QUALITY, method=4)
    return out.getvalue()


def write_focus_thumbnails() -> None:
    """Vignettes du jeu focal. Ne supprime pas les WebP historiques et n'écrit pas le JSON de la SPA."""
    manifest = ROOT / "data" / "test_set" / "focus_manifest.csv"
    if not manifest.is_file():
        raise SystemExit(f"Manifeste focal absent : {manifest}")
    rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
    written = 0
    missing = 0
    for row in rows:
        src = ROOT / "data" / "test_set" / row["fichier"]
        name = Path(row["fichier"]).name
        if not name.startswith("focus_"):
            raise SystemExit(f"Nom inattendu dans le jeu focal : {row['fichier']}")
        if not src.is_file():
            missing += 1
            print(f"JPEG absent : {row['fichier']}")
            continue
        rel = Path(row["fichier"]).with_suffix(".webp")
        dest = PUBLIC / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(thumbnail(src.read_bytes()))
        written += 1
    size = sum(p.stat().st_size for p in PUBLIC.rglob("*.webp"))
    print(f"Vignettes focales : {written} écrites, {missing} absentes, dossier {size / 1_048_576:.2f} Mo")
    if missing:
        raise SystemExit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--focus", action="store_true", help="vignettes de focus_manifest.csv, sans effacer les 200")
    args = ap.parse_args()
    if args.focus:
        write_focus_thumbnails()
        return

    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    caltech = caltech_frame()
    if PUBLIC.exists():
        for old in PUBLIC.rglob("*.webp"):
            old.unlink()
    categories: dict[str, dict] = {}
    missing = 0
    written = 0
    for row in rows:
        bucket = categories.setdefault(
            row["categorie"],
            {"label": row["categorie"], "count": 0, "photos": []},
        )
        bucket["count"] += 1
        data = source_bytes(row, caltech)
        if not data:
            missing += 1
            continue
        rel = Path(row["fichier"]).with_suffix(".webp")
        dest = PUBLIC / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(thumbnail(data))
        bucket["photos"].append(
            {
                "src": f"/jeu/{rel.as_posix()}",
                "source": row["source"],
                "classe": row["classe_source"],
            }
        )
        written += 1

    payload = {
        "manifestPath": "data/test_set/manifest.csv",
        "total": len(rows),
        "present": written,
        "missing": missing,
        "categories": list(categories.values()),
    }
    INDEX.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    size = sum(p.stat().st_size for p in PUBLIC.rglob("*.webp"))
    print(f"Vignettes : {written} écrites, {missing} absentes, {size / 1_048_576:.2f} Mo")


if __name__ == "__main__":
    main()
