"""Construit le jeu de test « proxy » étiqueté (20 photos × 10 catégories).

Pourquoi un proxy : le LLM Council (docs/llm-council/) a relevé qu'un jeu de test
étiqueté par l'étudiant lui-même est biaisé. On part donc de deux jeux publics,
étiquetés par des tiers, et on fixe la correspondance classe source → catégorie
d'annonce AVANT de regarder les prédictions :

- Stanford Online Products (photos réelles d'annonces eBay) : meubles, électroménager, vélos ;
- Caltech-256 (split test) : le reste des catégories.

Les photos réelles de Lucas pourront s'ajouter dans data/test_set/real/<categorie>/.

Sortie : data/test_set/<slug>/<fichier>.jpg (non versionné) + data/test_set/manifest.csv (versionné).

Usage : python scripts/build_test_set.py [--per-category 20] [--caltech PATH_PARQUET]
"""

from __future__ import annotations

import argparse
import csv
import io
import random
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "test_set"
SEED = 42

HF = "https://huggingface.co/datasets"
SOP_REPO = f"{HF}/pawlo2013/StanfordOnlineProducts/resolve/main/Stanford_Online_Products"
CALTECH_URL = f"{HF}/ilee0022/Caltech-256/resolve/main/data/test-00000-of-00001.parquet"

# Catégorie d'annonce -> (classes Stanford Online Products, classes Caltech-256)
PLAN: dict[str, tuple[list[str], list[str]]] = {
    "Électronique": ([], ["laptop-101", "computer-keyboard", "computer-monitor", "computer-mouse", "ipod",
                         "head-phones", "boom-box", "calculator", "video-projector", "joy-stick"]),
    "Maison et meubles": (["chair", "sofa", "table", "lamp", "cabinet", "mug"],
                          ["teapot", "frying-pan", "coffee-mug", "mattress", "chandelier-101"]),
    "Électroménager": (["coffee_maker", "kettle", "toaster", "fan"],
                       ["microwave", "refrigerator", "washing-machine", "toaster", "breadmaker"]),
    "Vêtements et accessoires": ([], ["sneaker", "tennis-shoes", "t-shirt", "socks", "necktie", "cowboy-hat",
                                     "top-hat", "watch-101", "eyeglasses", "backpack"]),
    "Sport et loisirs": (["bicycle"], ["tennis-racket", "soccer-ball", "golf-ball", "baseball-bat", "baseball-glove",
                                       "bowling-ball", "boxing-glove", "dumb-bell", "skateboard", "kayak"]),
    "Jeux et jouets": ([], ["teddy-bear", "chess-board", "dice", "playing-card", "yo-yo", "pez-dispenser"]),
    "Véhicules et pièces": ([], ["car-side-101", "motorbikes-101", "car-tire", "school-bus", "fire-truck",
                                "snowmobile", "speed-boat", "steering-wheel"]),
    "Bricolage et jardin": ([], ["screwdriver", "wheelbarrow", "self-propelled-lawn-mower", "ladder", "flashlight",
                                "welding-mask", "mailbox", "birdbath"]),
    "Livres et musique": ([], ["electric-guitar-101", "grand-piano-101", "harmonica", "harp", "french-horn",
                              "mandolin", "tambourine", "xylophone", "sheet-music", "cd"]),
    "Autre": ([], ["dog", "horse", "butterfly", "giraffe", "rainbow", "waterfall", "pyramid", "sushi",
                  "mushroom", "cake"]),
}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "-".join(text.lower().replace("&", "et").split())


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (URL fixe)
        return r.read()


def sop_candidates() -> dict[str, list[str]]:
    """Une image (_0) par produit eBay du split test, par super-classe."""
    lines = fetch(f"{SOP_REPO}/Ebay_test.txt").decode().splitlines()[1:]
    by_class: dict[str, list[str]] = {}
    for line in lines:
        path = line.split()[3]
        if not path.endswith("_0.JPG"):
            continue
        cls = path.split("/")[0].removesuffix("_final")
        by_class.setdefault(cls, []).append(path)
    return by_class


def round_robin(pools: list[list], n: int, rng: random.Random, load) -> list:
    """Tire n éléments en alternant les sous-classes (équilibre).

    `load(item)` renvoie les octets de l'image, ou None si elle est indisponible
    (quelques fichiers du miroir HF de Stanford Online Products manquent) :
    on passe alors au candidat suivant de la même sous-classe.
    """
    pools = [rng.sample(p, len(p)) for p in pools if p]
    picked: list = []
    while len(picked) < n and any(pools):
        for p in pools:
            while p and len(picked) < n:
                item = p.pop()
                data = load(item)
                if data is not None:
                    picked.append((item, data))
                    break
    return picked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-category", type=int, default=20)
    ap.add_argument("--caltech", type=Path, default=None, help="parquet Caltech-256 déjà téléchargé")
    args = ap.parse_args()

    import pandas as pd
    from PIL import Image

    rng = random.Random(SEED)
    caltech_src = args.caltech or io.BytesIO(fetch(CALTECH_URL))
    caltech = pd.read_parquet(caltech_src)
    sop = sop_candidates()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for category, (sop_classes, caltech_classes) in PLAN.items():
        pools: list[list] = [[("sop", c, p) for p in sop.get(c, [])] for c in sop_classes]
        pools += [[("caltech", c, i) for i in caltech.index[caltech["text"] == c]] for c in caltech_classes]
        for c, pool in zip(sop_classes + caltech_classes, pools):
            if not pool:
                raise SystemExit(f"Classe source vide : {c}")
        def load(item):
            source, cls, ref = item
            if source == "caltech":
                return caltech.loc[ref, "image"]["bytes"]
            try:
                return fetch(f"{SOP_REPO}/{ref}")
            except urllib.error.HTTPError:
                return None

        chosen = round_robin(pools, args.per_category, rng, load)

        folder = OUT_DIR / slugify(category)
        folder.mkdir(exist_ok=True)
        for (source, cls, ref), data in chosen:
            name = f"sop_{Path(ref).stem}.jpg" if source == "sop" else f"caltech_{cls}_{ref}.jpg"
            img = Image.open(io.BytesIO(data)).convert("RGB")
            img.save(folder / name, format="JPEG", quality=92)
            rows.append({"fichier": f"{folder.name}/{name}", "categorie": category,
                         "source": source, "classe_source": cls})
        print(f"{category:<26} {len(chosen)} images")

    with (OUT_DIR / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["fichier", "categorie", "source", "classe_source"])
        w.writeheader()
        w.writerows(rows)
    print(f"Total : {len(rows)} images -> {OUT_DIR.relative_to(ROOT)}/manifest.csv")


if __name__ == "__main__":
    main()
