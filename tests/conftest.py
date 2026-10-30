"""Fixtures partagées : images générées en mémoire (aucun fichier de test binaire versionné)."""

from __future__ import annotations

import io
import os

import pytest

# Token de test, défini AVANT l'import de l'app (Settings est mis en cache)
TEST_TOKEN = "test-token-0123456789"
os.environ["API_TOKEN"] = TEST_TOKEN
AUTH = {"Authorization": f"Bearer {TEST_TOKEN}"}
from PIL import Image


def make_image_bytes(fmt: str = "JPEG", size: tuple[int, int] = (320, 240), color=(200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    mode = "RGBA" if fmt == "PNG" else "RGB"
    Image.new(mode, size, color).save(buf, format=fmt)
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

import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class FakePredictor:
    """Renvoie une distribution fixe : 'laptop' (620) très probable par défaut."""

    name = "fake-predictor"

    def __init__(self, peaks: dict[int, float] | None = None):
        self.peaks = peaks or {620: 0.92, 681: 0.05, 526: 0.01}

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


@pytest.fixture
def make_client():
    from app.main import app

    def _make(predictor=None, auth: bool = True):
        app.state.predictor = predictor or FakePredictor()
        return TestClient(app, headers=AUTH if auth else None)

    yield _make
    app.state.predictor = None


@pytest.fixture
def client(make_client):
    return make_client()
