"""Fixtures partagées : images générées en mémoire (aucun fichier de test binaire versionné)."""

from __future__ import annotations

import io

import pytest
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
