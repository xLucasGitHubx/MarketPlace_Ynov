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


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# Seuil de confiance par défaut pour chaque backend (calibré après mesure,
# voir docs/preuves). Surchargé globalement par CONFIDENCE_THRESHOLD.
DEFAULT_THRESHOLDS = {
    "pytorch": 0.6,
    "onnx": 0.6,
}


@dataclass(frozen=True)
class Settings:
    app_name: str = "Marketplace Vision API"
    app_version: str = "0.5.0"

    # Upload
    max_upload_mb: float = field(default_factory=lambda: _env_float("MAX_UPLOAD_MB", 5))
    allowed_mime_types: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")

    # Sécurité : un ou plusieurs tokens séparés par des virgules (rotation sans coupure)
    api_tokens: tuple[str, ...] = field(
        default_factory=lambda: tuple(t.strip() for t in os.getenv("API_TOKEN", "").split(",") if t.strip())
    )

    # Modèle
    model_backend: str = field(default_factory=lambda: os.getenv("MODEL_BACKEND", "pytorch").lower())
    model_cache_dir: str | None = field(default_factory=lambda: os.getenv("MODEL_CACHE_DIR") or None)
    hf_token: str | None = field(default_factory=lambda: os.getenv("HF_TOKEN") or None)
    onnx_model_path: str | None = field(default_factory=lambda: os.getenv("ONNX_MODEL_PATH") or None)

    # MLOps : suivi des requêtes dans MLflow (désactivé si vide)
    mlflow_tracking_uri: str | None = field(default_factory=lambda: os.getenv("MLFLOW_TRACKING_URI") or None)

    # Logique métier
    top_k: int = field(default_factory=lambda: _env_int("TOP_K", 5))
    _threshold_override: str | None = field(default_factory=lambda: os.getenv("CONFIDENCE_THRESHOLD") or None)

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @property
    def confidence_threshold(self) -> float:
        if self._threshold_override is not None:
            try:
                return float(self._threshold_override)
            except ValueError:
                pass
        return DEFAULT_THRESHOLDS.get(self.model_backend, 0.6)


@lru_cache
def get_settings() -> Settings:
    return Settings()
