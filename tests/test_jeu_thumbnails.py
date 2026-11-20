"""Le pack de vignettes suit le manifeste, sans les JPEG d'origine."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "test_set" / "manifest.csv"
INDEX = ROOT / "web" / "src" / "parcours" / "jeuPhotos.json"
PUBLIC = ROOT / "web" / "public"


def test_vignettes_suivent_le_manifeste():
    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    pack = json.loads(INDEX.read_text(encoding="utf-8"))
    assert pack["total"] == len(rows) == 200
    assert pack["missing"] == 0
    assert pack["present"] == 200
    photos = [photo for group in pack["categories"] for photo in group["photos"]]
    assert len(photos) == 200
    assert [group["label"] for group in pack["categories"]] == list(
        dict.fromkeys(row["categorie"] for row in rows)
    )
    for group in pack["categories"]:
        assert group["count"] == 20
        assert len(group["photos"]) == 20
    for photo in photos:
        src = photo["src"]
        assert src.startswith("/jeu/")
        assert ".." not in src
        path = PUBLIC / src.lstrip("/")
        assert path.is_file()
        assert path.suffix == ".webp"
        assert 0 < path.stat().st_size < 80_000
