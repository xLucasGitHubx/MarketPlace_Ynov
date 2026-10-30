"""Itération 2 : logique métier et réponse /predict."""

from __future__ import annotations

import numpy as np
import pytest

from app.business import STATUS_AUTO, STATUS_TO_CONFIRM, load_category_map, suggest
from tests.conftest import FailingPredictor, FakePredictor


def probs_with(peaks: dict[int, float]) -> np.ndarray:
    return FakePredictor(peaks).predict_proba(None)


def test_categories_json_complet():
    cmap = load_category_map()
    assert len(cmap.classes) == 1000
    assert len(cmap.categories) == 10
    assert {c.category for c in cmap.classes} <= set(cmap.categories)
    assert cmap.classes[620].category == "Électronique"
    assert cmap.classes[671].category == "Sport et loisirs"  # VTT
    assert cmap.classes[831].category == "Maison et meubles"  # canapé


def test_statut_auto_au_dessus_du_seuil():
    s = suggest(probs_with({620: 0.92, 681: 0.05}), threshold=0.6)
    assert s.category == "Électronique"
    assert s.title == "Ordinateur portable"
    assert s.status == STATUS_AUTO
    assert s.confidence == pytest.approx(0.97, abs=1e-3)  # 620 + 681 cumulés


def test_score_cumule_par_categorie():
    # Aucune classe seule ne dépasse le seuil, mais la catégorie cumulée oui
    s = suggest(probs_with({508: 0.35, 673: 0.30, 526: 0.25}), threshold=0.6)
    assert s.category == "Électronique"  # clavier + souris = 0.65
    assert s.title == "Clavier d'ordinateur"
    assert s.status == STATUS_AUTO


def test_statut_a_confirmer_et_trois_propositions():
    s = suggest(probs_with({831: 0.30, 620: 0.25, 671: 0.20}), threshold=0.6)
    assert s.status == STATUS_TO_CONFIRM
    assert [p["categorie"] for p in s.category_scores] == [
        "Maison et meubles", "Électronique", "Sport et loisirs",
    ]


def test_top3_brut():
    s = suggest(probs_with({620: 0.92, 681: 0.05, 526: 0.01}), threshold=0.6)
    assert [t["label"] for t in s.top3] == ["laptop", "notebook", "desk"]


def test_seuil_configurable():
    p = probs_with({620: 0.55})
    assert suggest(p, threshold=0.5).status == STATUS_AUTO
    assert suggest(p, threshold=0.6).status == STATUS_TO_CONFIRM


def test_vecteur_de_mauvaise_taille():
    with pytest.raises(ValueError):
        suggest(np.ones(10) / 10, threshold=0.6)


def test_reponse_predict_conforme_a_la_spec(client, jpeg_bytes):
    r = client.post("/predict", files={"file": ("pc.jpg", jpeg_bytes, "image/jpeg")})
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"categorie", "titre_suggere", "confiance", "statut", "top3", "propositions", "modele", "latence_ms"}
    assert body["categorie"] == "Électronique"
    assert body["titre_suggere"] == "Ordinateur portable"
    assert body["statut"] == "auto"
    assert len(body["top3"]) == 3
    assert body["modele"] == "fake-predictor"


def test_erreur_inference_sans_stack_trace(make_client, jpeg_bytes):
    c = make_client(FailingPredictor())
    r = c.post("/predict", files={"file": ("x.jpg", jpeg_bytes, "image/jpeg")})
    assert r.status_code == 500
    assert "boom" not in r.text and "Traceback" not in r.text


def test_health_indique_le_modele(client):
    body = client.get("/health").json()
    assert body["modele_charge"] is True
    assert body["modele"] == "fake-predictor"
