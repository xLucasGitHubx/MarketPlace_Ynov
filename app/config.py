"""Configuration de l'API, lue depuis les variables d'environnement.

Aucun secret n'est codé en dur : tout passe par l'environnement (ou un .env
chargé par le lanceur). Les valeurs par défaut conviennent au développement local.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str = "Marketplace Vision API"
    app_version: str = "0.1.0"

    # Upload
    max_upload_mb: float = field(default_factory=lambda: _env_float("MAX_UPLOAD_MB", 5))
    allowed_mime_types: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)


@lru_cache
def get_settings() -> Settings:
    return Settings()
