"""Phase 1 : ModelRegistry, sélection de modèle, allowlist, rate-limit, heuristiques."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.registry import (
    CATALOG,
    CATALOG_BY_ID,
    DEFAULT_MODEL_ID,
    apply_metrics_to_spec,
    build_registry,
    estimate_cost_usd_per_million,
    load_catalog_metrics,
)
from app.security import RateLimiter
from tests.conftest import FakePredictor, make_image_bytes


def test_catalogue_contient_les_ids_attendus():
    ids = {s.id for s in CATALOG}
    assert ids == {
        "resnet50-onnx-int8",
        "efficientnet-b0-onnx-int8",
        "mobilenet-v3-small-onnx-int8",
        "student-kd-mobilenet-int8",
        "clip-vit-b32",
    }
    assert CATALOG_BY_ID["clip-vit-b32"].space_only is True


def test_build_registry_sans_fichiers_marque_building_et_space_only(tmp_path: Path):
    reg = build_registry(onnx_dir=tmp_path, load_models=True, azure_runtime=True)
    assert reg.entries["clip-vit-b32"].status == "space_only"
    assert reg.entries["clip-vit-b32"].loaded is False
    assert reg.entries["efficientnet-b0-onnx-int8"].status == "building"
    assert reg.loaded_ids() == []


def test_build_registry_charge_onnx_si_present(tmp_path: Path, monkeypatch):
    onnx_dir = tmp_path / "onnx"
    onnx_dir.mkdir()
    target = onnx_dir / "resnet50-int8-static.onnx"
    target.write_bytes(b"not-a-real-onnx")

    class StubOnnx:
        def __init__(self, model_path, num_threads=None, name=None):
            self.name = name or "stub"
            self.path = model_path

        def predict_proba(self, image):
            raise NotImplementedError

    monkeypatch.setattr("app.registry.OnnxPredictor", StubOnnx)
    reg = build_registry(onnx_dir=onnx_dir, enabled_models=("resnet50-onnx-int8",), load_models=True)
    assert "resnet50-onnx-int8" in reg.loaded_ids()
    assert reg.entries["resnet50-onnx-int8"].status == "ready"
    assert reg.get_predictor("resnet50-onnx-int8").name == "resnet50-onnx-int8"


def test_get_models_public(client):
    for path in ("/models", "/api/models"):
        r = client.get(path)
        assert r.status_code == 200, path
        body = r.json()
        assert body["defaut"] == DEFAULT_MODEL_ID
        ids = [m["id"] for m in body["modeles"]]
        assert "resnet50-onnx-int8" in ids
        assert "clip-vit-b32" in ids
        clip = next(m for m in body["modeles"] if m["id"] == "clip-vit-b32")
        assert clip["statut"] == "space_only"
        assert clip["space_only"] is True


def test_health_liste_modeles_charges(make_client):
    c = make_client(with_registry=True)
    body = c.get("/health").json()
    assert body["modele_charge"] is True
    assert DEFAULT_MODEL_ID in body["modeles_charges"]
    assert body["modele"] == DEFAULT_MODEL_ID
    assert c.get("/api/health").json()["modeles_charges"] == body["modeles_charges"]


def test_predict_modele_invalide_400(make_client, jpeg_bytes):
    c = make_client(with_registry=True)
    r = c.post(
        "/predict",
        files={"file": ("x.jpg", jpeg_bytes, "image/jpeg")},
        data={"modele": "microsoft/resnet-50"},
    )
    assert r.status_code == 400
    assert "autorisé" in r.json()["detail"].lower() or "inconnu" in r.json()["detail"].lower()


def test_predict_modele_building_400(make_client, jpeg_bytes):
    c = make_client(with_registry=True)
    r = c.post(
        "/api/predict",
        files={"file": ("x.jpg", jpeg_bytes, "image/jpeg")},
        data={"modele": "efficientnet-b0-onnx-int8"},
    )
    assert r.status_code == 400
    assert "efficientnet" in r.json()["detail"]


def test_predict_space_only_refuse_400(make_client, jpeg_bytes):
    c = make_client(with_registry=True)
    r = c.post(
        "/predict",
        files={"file": ("x.jpg", jpeg_bytes, "image/jpeg")},
        data={"modele": "clip-vit-b32"},
    )
    assert r.status_code == 400
    assert "space" in r.json()["detail"].lower()


def test_predict_modele_defaut_et_cout(make_client, jpeg_bytes):
    c = make_client(with_registry=True)
    r = c.post("/predict", files={"file": ("x.jpg", jpeg_bytes, "image/jpeg")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["modele"] == DEFAULT_MODEL_ID
    assert body["cout_estime_usd_par_million"] == pytest.approx(1.8)
    assert body["categorie"] == "Électronique"


def test_predict_modele_explicite(make_client, jpeg_bytes):
    from app.main import app

    c = make_client(with_registry=True)
    # Deuxième modèle factice prêt
    other = FakePredictor(name="mobilenet-v3-small-onnx-int8")
    entry = app.state.registry.entries["mobilenet-v3-small-onnx-int8"]
    entry.predictor = other
    entry.loaded = True
    entry.status = "ready"

    r = c.post(
        "/api/predict",
        files={"file": ("x.jpg", jpeg_bytes, "image/jpeg")},
        data={"modele": "mobilenet-v3-small-onnx-int8"},
    )
    assert r.status_code == 200
    assert r.json()["modele"] == "mobilenet-v3-small-onnx-int8"


def test_allowlist_refuse_id_hors_catalogue():
    reg = build_registry(load_models=False)
    assert not reg.is_allowed("openai/clip-vit-base-patch32")
    assert not reg.is_allowed("totally-fake")
    assert reg.is_allowed("resnet50-onnx-int8")


def test_estimate_cost_ratio_baseline():
    assert estimate_cost_usd_per_million(28.6) == 1.8
    assert estimate_cost_usd_per_million(14.3) == 0.9
    assert estimate_cost_usd_per_million(None) is None


def test_load_catalog_metrics_applique_au_registre(tmp_path: Path):
    metrics_file = tmp_path / "catalog_metrics.json"
    metrics_file.write_text(
        """
        {
          "version": "1.0",
          "models": {
            "efficientnet-b0-onnx-int8": {
              "accuracy": 0.71,
              "p50_ms": 11.0,
              "p95_ms": 14.0,
              "size_mb": 5.2,
              "cout_estime_usd_par_million": 0.88
            }
          }
        }
        """,
        encoding="utf-8",
    )
    loaded = load_catalog_metrics(metrics_file)
    assert loaded["efficientnet-b0-onnx-int8"]["accuracy"] == 0.71

    reg = build_registry(load_models=False, metrics_path=metrics_file)
    spec = reg.entries["efficientnet-b0-onnx-int8"].spec
    assert spec.accuracy == 0.71
    assert spec.p95_ms == 14.0
    assert spec.cout_estime_usd_par_million == 0.88
    assert reg.entries["resnet50-onnx-int8"].spec.accuracy == 0.685


def test_apply_metrics_calcule_cout_si_absent():
    base = CATALOG_BY_ID["mobilenet-v3-small-onnx-int8"]
    updated = apply_metrics_to_spec(base, {"p95_ms": 9.0, "accuracy": 0.61})
    assert updated.accuracy == 0.61
    assert updated.cout_estime_usd_par_million == estimate_cost_usd_per_million(9.0)


def test_get_models_expose_cout_et_metriques(make_client):
    c = make_client(with_registry=True)
    body = c.get("/api/models").json()
    resnet = next(m for m in body["modeles"] if m["id"] == DEFAULT_MODEL_ID)
    assert resnet["accuracy"] == 0.685
    assert resnet["cout_estime_usd_par_million"] == 1.8
    assert resnet["taille_mo"] == 24.9
    eff = next(m for m in body["modeles"] if m["id"] == "efficientnet-b0-onnx-int8")
    assert eff["cout_estime_usd_par_million"] is not None


def test_rate_limit_429(make_client, jpeg_bytes):
    c = make_client(with_registry=True, rate_limit=2)
    files = {"file": ("x.jpg", jpeg_bytes, "image/jpeg")}
    assert c.post("/predict", files=files).status_code == 200
    assert c.post("/predict", files=files).status_code == 200
    r = c.post("/predict", files=files)
    assert r.status_code == 429
    assert "Trop de requêtes" in r.json()["detail"]


def test_rate_limiter_unitaire():
    lim = RateLimiter(max_per_minute=2, window_seconds=60)
    assert lim.allow("t") and lim.allow("t")
    assert not lim.allow("t")
    assert lim.allow("autre-token")


def test_heuristique_image_uniforme_422(client):
    data = make_image_bytes("JPEG", uniform=True)
    r = client.post("/predict", files={"file": ("plat.jpg", data, "image/jpeg")})
    assert r.status_code == 422
    assert "uniforme" in r.json()["detail"].lower() or "structure" in r.json()["detail"].lower()


def test_heuristique_image_trop_petite_422(client):
    data = make_image_bytes("JPEG", size=(32, 32))
    r = client.post("/predict", files={"file": ("mini.jpg", data, "image/jpeg")})
    assert r.status_code == 422
    assert "petite" in r.json()["detail"].lower()


def test_swagger_expose_api_prefix(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/predict" in paths
    assert "/api/predict" in paths
    assert "/api/models" in paths
    assert "/models" in paths
