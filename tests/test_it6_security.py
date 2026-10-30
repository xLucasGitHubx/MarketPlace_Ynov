"""Itération 6 : authentification Bearer et aucune image conservée (RGPD)."""

from __future__ import annotations

import logging
import tempfile

import numpy as np
import pytest
from PIL import Image

from tests.conftest import TEST_TOKEN


def _post(client, data, headers=None):
    return client.post("/predict", files={"file": ("objet.jpg", data, "image/jpeg")}, headers=headers)


def test_401_sans_token(make_client, jpeg_bytes):
    r = _post(make_client(auth=False), jpeg_bytes)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("header", [
    "Bearer mauvais-token",
    f"Basic {TEST_TOKEN}",
    "Bearer",
    TEST_TOKEN,
])
def test_401_token_invalide(make_client, jpeg_bytes, header):
    r = _post(make_client(auth=False), jpeg_bytes, headers={"Authorization": header})
    assert r.status_code == 401


def test_200_avec_token(client, jpeg_bytes):
    assert _post(client, jpeg_bytes).status_code == 200


def test_auth_verifiee_avant_la_taille(make_client):
    # Sans token, même un fichier énorme renvoie 401 : on ne lit pas le corps
    r = _post(make_client(auth=False), b"0" * (8 * 1024 * 1024))
    assert r.status_code == 401


def test_413_avant_lecture_du_corps(client):
    r = _post(client, b"0" * (8 * 1024 * 1024))
    assert r.status_code == 413


def test_health_et_docs_restent_publics(make_client):
    c = make_client(auth=False)
    assert c.get("/health").status_code == 200
    assert c.get("/docs").status_code == 200


def test_swagger_declare_le_bearer(client):
    schema = client.get("/openapi.json").json()
    assert any(s.get("scheme") == "bearer" for s in schema["components"]["securitySchemes"].values())


def test_fail_closed_si_aucun_token_configure(jpeg_bytes):
    from app.config import Settings
    from app.security import is_valid_token

    s = Settings(api_tokens=())
    assert not is_valid_token("nimporte-quoi", s)
    assert not is_valid_token("", s)


def test_rotation_plusieurs_tokens():
    from app.config import Settings
    from app.security import is_valid_token

    s = Settings(api_tokens=("ancien", "nouveau"))
    assert is_valid_token("ancien", s) and is_valid_token("nouveau", s)
    assert not is_valid_token("autre", s)


def test_aucun_fichier_temporaire_pour_une_grosse_image(client, monkeypatch):
    """Une image de ~4,5 Mo reste en RAM : Starlette ne bascule jamais sur disque."""
    rolled = []
    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", lambda self: rolled.append(True))
    noise = (np.random.default_rng(0).random((1300, 1200, 3)) * 255).astype("uint8")
    import io
    buf = io.BytesIO()
    Image.fromarray(noise).save(buf, format="PNG")
    data = buf.getvalue()
    assert 4 * 1024 * 1024 < len(data) < 5 * 1024 * 1024
    r = client.post("/predict", files={"file": ("grosse.png", data, "image/png")})
    assert r.status_code == 200
    assert rolled == []


def test_logs_sans_contenu_ni_nom_de_fichier(client, jpeg_bytes, caplog):
    caplog.set_level(logging.DEBUG)
    client.post("/predict", files={"file": ("photo_jean_dupont.jpg", jpeg_bytes, "image/jpeg")})
    text = caplog.text
    assert "jean_dupont" not in text
    assert "prediction categorie=" in text  # on logue bien les métadonnées utiles
    assert jpeg_bytes[:20].hex() not in text
