"""Itération 8 : journalisation MLflow des requêtes (étape 9 du pipeline)."""

from __future__ import annotations

import pytest

from app.monitoring import NullTracker, create_tracker, slug

mlflow = pytest.importorskip("mlflow")


def test_slug_categories():
    assert slug("Vêtements et accessoires") == "vetements_et_accessoires"
    assert slug("Électroménager") == "electromenager"


def test_desactive_sans_tracking_uri():
    assert isinstance(create_tracker(None, "m", "0"), NullTracker)


def test_mlflow_indisponible_ne_casse_pas_l_api():
    # URI invalide : on retombe sur NullTracker au lieu de lever une exception
    assert isinstance(create_tracker("invalid-scheme://nope", "m", "0"), NullTracker)


def test_requetes_journalisees_sans_donnee_personnelle(tmp_path, make_client, jpeg_bytes):
    from mlflow.tracking import MlflowClient

    from app.main import app

    uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    tracker = create_tracker(uri, "fake-predictor", "test")
    app.state.tracker = tracker
    try:
        c = make_client()
        for _ in range(5):
            assert c.post("/predict", files={"file": ("jean_dupont.jpg", jpeg_bytes, "image/jpeg")}).status_code == 200
    finally:
        tracker.close()
        app.state.tracker = None

    client = MlflowClient(uri)
    run = client.get_run(tracker.run_id)
    assert run.data.metrics["nb_requetes"] == 5
    assert run.data.metrics["nb_electronique"] == 5
    assert len(client.get_metric_history(tracker.run_id, "latence_ms")) == 5
    assert run.data.params["modele"] == "fake-predictor"
    # Rien qui ressemble à un nom de fichier ou à une image dans le run
    blob = str(run.data.params) + str(run.data.tags) + str(run.data.metrics)
    assert "jean_dupont" not in blob


def test_serveur_http_injoignable_desactive_le_suivi():
    assert isinstance(create_tracker("http://127.0.0.1:9", "m", "0"), NullTracker)
