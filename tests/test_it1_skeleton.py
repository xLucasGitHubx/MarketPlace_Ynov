"""Itération 1 : squelette de l'API (health, upload, validation des entrées)."""

from __future__ import annotations

import pytest


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_swagger_disponible(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/predict" in schema["paths"]


@pytest.mark.parametrize("fixture,mime", [
    ("jpeg_bytes", "image/jpeg"),
    ("png_bytes", "image/png"),
    ("webp_bytes", "image/webp"),
])
def test_predict_formats_acceptes(client, request, fixture, mime):
    data = request.getfixturevalue(fixture)
    r = client.post("/predict", files={"file": ("photo", data, "application/octet-stream")})
    assert r.status_code == 200, r.text
    assert r.json()["categorie"]


def test_type_reel_et_pas_extension(client, pdf_bytes):
    # Un PDF renommé en .jpg avec un Content-Type mensonger doit être rejeté
    r = client.post("/predict", files={"file": ("faux.jpg", pdf_bytes, "image/jpeg")})
    assert r.status_code == 415


def test_gif_refuse(client, gif_bytes):
    r = client.post("/predict", files={"file": ("anim.gif", gif_bytes, "image/gif")})
    assert r.status_code == 415


def test_fichier_trop_lourd(client):
    big = b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024 + 10)
    r = client.post("/predict", files={"file": ("gros.jpg", big, "image/jpeg")})
    assert r.status_code == 413


def test_fichier_vide(client):
    r = client.post("/predict", files={"file": ("vide.jpg", b"", "image/jpeg")})
    assert r.status_code == 422


def test_image_tronquee(client, jpeg_bytes):
    r = client.post("/predict", files={"file": ("cassee.jpg", jpeg_bytes[: len(jpeg_bytes) // 2], "image/jpeg")})
    assert r.status_code == 422


def test_champ_file_obligatoire(client):
    r = client.post("/predict")
    assert r.status_code == 422
