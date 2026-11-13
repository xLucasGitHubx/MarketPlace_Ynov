"""Fixtures partagées : images générées en mémoire (aucun fichier de test binaire versionné)."""

from __future__ import annotations

import io
import os

import numpy as np
import pytest

# Token de test, défini AVANT l'import de l'app (Settings est mis en cache)
TEST_TOKEN = "test-token-0123456789"
os.environ["API_TOKEN"] = TEST_TOKEN
AUTH = {"Authorization": f"Bearer {TEST_TOKEN}"}
from PIL import Image


def make_image_bytes(
    fmt: str = "JPEG",
    size: tuple[int, int] = (320, 240),
    color=(200, 30, 30),
    *,
    uniform: bool = False,
    seed: int = 42,
) -> bytes:
    """Génère une image en mémoire.

    Par défaut : bruit léger pour passer les heuristiques anti-aplat.
    `uniform=True` : aplats purs (rejetés par reject_non_object_image).
    """
    buf = io.BytesIO()
    w, h = size
    arr = np.empty((h, w, 3), dtype=np.uint8)
    arr[:, :] = color
    if not uniform:
        rng = np.random.default_rng(seed)
        noise = rng.integers(-45, 46, size=(h, w, 3), dtype=np.int16)
        # Léger motif pour garantir des contours
        yy, xx = np.mgrid[0:h, 0:w]
        pattern = ((xx // 16 + yy // 16) % 2) * 30
        arr = np.clip(arr.astype(np.int16) + noise + pattern[..., None], 0, 255).astype(np.uint8)
    Image.fromarray(arr, "RGB").save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture
def jpeg_bytes() -> bytes:
    return make_image_bytes("JPEG")


@pytest.fixture
def png_bytes() -> bytes:
    return make_image_bytes("PNG")


@pytest.fixture
def webp_bytes() -> bytes:
    return make_image_bytes("WEBP")


@pytest.fixture
def gif_bytes() -> bytes:
    return make_image_bytes("GIF")


@pytest.fixture
def pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"


# --- Faux modèle : teste l'API sans télécharger ResNet-50 -------------------

from fastapi.testclient import TestClient  # noqa: E402

from app.registry import DEFAULT_MODEL_ID, ModelRegistry, build_registry  # noqa: E402


class FakePredictor:
    """Renvoie une distribution fixe : 'laptop' (620) très probable par défaut."""

    name = "fake-predictor"

    def __init__(self, peaks: dict[int, float] | None = None, name: str | None = None):
        self.peaks = peaks or {620: 0.92, 681: 0.05, 526: 0.01}
        if name:
            self.name = name

    def predict_proba(self, image):
        probs = np.full(1000, 0.0)
        for idx, p in self.peaks.items():
            probs[idx] = p
        rest = 1.0 - probs.sum()
        probs[probs == 0] = rest / (probs == 0).sum()
        return probs


class FailingPredictor:
    name = "failing-predictor"

    def predict_proba(self, image):
        raise RuntimeError("boom secret interne")


def inject_fake_registry(
    app,
    predictor: FakePredictor | None = None,
    model_id: str = DEFAULT_MODEL_ID,
) -> ModelRegistry:
    """Installe un registre de test avec un faux predictor sur l'ID catalogue donné."""
    predictor = predictor or FakePredictor(name=model_id)
    predictor.name = model_id
    registry = build_registry(load_models=False, default_model_id=model_id)
    entry = registry.entries[model_id]
    entry.predictor = predictor
    entry.loaded = True
    entry.status = "ready"
    app.state.registry = registry
    app.state.predictor = predictor
    return registry


@pytest.fixture
def make_client():
    from app.main import app
    from app.security import RateLimiter

    def _make(predictor=None, auth: bool = True, *, with_registry: bool = False, rate_limit: int | None = None):
        pred = predictor or FakePredictor()
        app.state.predictor = pred
        app.state.registry = None
        if with_registry:
            registry = build_registry(load_models=False, default_model_id=DEFAULT_MODEL_ID)
            entry = registry.entries[DEFAULT_MODEL_ID]
            entry.predictor = pred
            entry.loaded = True
            entry.status = "ready"
            pred.name = DEFAULT_MODEL_ID
            app.state.registry = registry
            app.state.predictor = pred
        if rate_limit is not None:
            app.state.rate_limiter = RateLimiter(max_per_minute=rate_limit)
        else:
            app.state.rate_limiter = RateLimiter(max_per_minute=10_000)
        return TestClient(app, headers=AUTH if auth else None)

    yield _make
    app.state.predictor = None
    app.state.registry = None
    app.state.rate_limiter = None


@pytest.fixture
def client(make_client):
    return make_client()
