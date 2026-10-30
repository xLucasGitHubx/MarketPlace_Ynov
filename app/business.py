"""Logique métier : des probabilités ImageNet à une suggestion d'annonce.

C'est ce module qui transforme « label ImageNet brut » en produit de marketplace :
- regroupement des classes du modèle en catégories d'annonce (categories.json) ;
- score cumulé par catégorie sur le top-K des classes ;
- titre suggéré = titre FR de la classe la plus probable de la catégorie gagnante ;
- statut `auto` si la confiance dépasse le seuil, sinon `a_confirmer` avec 3 propositions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

CATEGORIES_PATH = Path(__file__).with_name("categories.json")
STATUS_AUTO = "auto"
STATUS_TO_CONFIRM = "a_confirmer"


@dataclass(frozen=True)
class ClassInfo:
    label: str
    category: str
    title: str


@dataclass(frozen=True)
class CategoryMap:
    categories: tuple[str, ...]
    classes: tuple[ClassInfo, ...]


@lru_cache
def load_category_map(path: Path = CATEGORIES_PATH) -> CategoryMap:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    classes = tuple(ClassInfo(c["label"], c["categorie"], c["titre"]) for c in raw["classes"])
    return CategoryMap(categories=tuple(raw["categories"]), classes=classes)


@dataclass
class Suggestion:
    category: str
    title: str
    confidence: float
    status: str
    top3: list[dict]  # classes brutes : label, categorie, score
    category_scores: list[dict]  # 3 meilleures catégories : categorie, score, titre


def suggest(probs: np.ndarray, threshold: float, top_k: int = 5, cmap: CategoryMap | None = None) -> Suggestion:
    """Construit la suggestion d'annonce à partir du vecteur de probabilités (softmax)."""
    cmap = cmap or load_category_map()
    probs = np.asarray(probs, dtype=np.float64).ravel()
    if probs.shape[0] != len(cmap.classes):
        raise ValueError(f"Vecteur de {probs.shape[0]} probabilités, {len(cmap.classes)} classes attendues")

    order = np.argsort(probs)[::-1]
    top_idx = order[: max(top_k, 3)]

    # Score cumulé par catégorie sur le top-K ; on retient la meilleure classe de chaque catégorie
    scores: dict[str, float] = {}
    best_class: dict[str, int] = {}
    for i in top_idx[:top_k]:
        info = cmap.classes[i]
        scores[info.category] = scores.get(info.category, 0.0) + float(probs[i])
        best_class.setdefault(info.category, int(i))  # order décroissant : la 1re vue est la meilleure

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    category, confidence = ranked[0]
    title = cmap.classes[best_class[category]].title
    status = STATUS_AUTO if confidence >= threshold else STATUS_TO_CONFIRM

    top3 = [
        {"label": cmap.classes[i].label, "categorie": cmap.classes[i].category, "score": round(float(probs[i]), 4)}
        for i in top_idx[:3]
    ]
    category_scores = [
        {"categorie": cat, "score": round(sc, 4), "titre": cmap.classes[best_class[cat]].title}
        for cat, sc in ranked[:3]
    ]
    return Suggestion(
        category=category,
        title=title,
        confidence=round(float(confidence), 4),
        status=status,
        top3=top3,
        category_scores=category_scores,
    )
