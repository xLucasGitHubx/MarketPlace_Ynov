"""SPA : index servi par FastAPI lorsque app/static/index.html existe."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import AUTH, FakePredictor


def _client_with_static(tmp_path: Path, monkeypatch):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text(
        "<!doctype html><html><body><h1>MarketPlace Vision SPA</h1></body></html>",
        encoding="utf-8",
    )
    assets = static_dir / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('spa');", encoding="utf-8")

    import app.main as main_mod
    from app.main import app
    from app.security import RateLimiter
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main_mod, "STATIC_DIR", static_dir)
    app.state.predictor = FakePredictor()
    app.state.registry = None
    app.state.rate_limiter = RateLimiter(max_per_minute=10_000)
    return TestClient(app, headers=AUTH)


def test_spa_index_servi_quand_static_present(tmp_path, monkeypatch):
    client = _client_with_static(tmp_path, monkeypatch)
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "MarketPlace Vision SPA" in r.text


def test_spa_fallback_client_route(tmp_path, monkeypatch):
    client = _client_with_static(tmp_path, monkeypatch)
    r = client.get("/comparateur")
    assert r.status_code == 200
    assert "MarketPlace Vision SPA" in r.text


def test_spa_asset_file_via_fallback(tmp_path, monkeypatch):
    client = _client_with_static(tmp_path, monkeypatch)
    # /assets peut être un Mount (si présent au boot) ou le fallback FileResponse
    r = client.get("/assets/app.js")
    assert r.status_code == 200
    assert "console.log" in r.text


def test_api_toujours_prioritaire_avec_spa(tmp_path, monkeypatch):
    client = _client_with_static(tmp_path, monkeypatch)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/models").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200


def test_sans_index_spa_404(make_client, monkeypatch, tmp_path):
    import app.main as main_mod

    empty = tmp_path / "empty_static"
    empty.mkdir()
    monkeypatch.setattr(main_mod, "STATIC_DIR", empty)

    client = make_client()
    r = client.get("/")
    assert r.status_code == 404
    assert "SPA" in r.json()["detail"]
