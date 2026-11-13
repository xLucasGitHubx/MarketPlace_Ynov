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


def _env_csv(name: str, default: str = "") -> tuple[str, ...]:
    raw = os.getenv(name, default)
    if raw is None:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# Seuil de confiance par défaut pour chaque backend (calibré après mesure,
# voir docs/preuves). Surchargé globalement par CONFIDENCE_THRESHOLD.
DEFAULT_THRESHOLDS = {
    "pytorch": 0.6,
    "onnx": 0.6,
}


@dataclass(frozen=True)
class Settings:
    app_name: str = "Marketplace Vision API"
    app_version: str = "0.6.0"

    # Upload
    max_upload_mb: float = field(default_factory=lambda: _env_float("MAX_UPLOAD_MB", 5))
    allowed_mime_types: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")
    min_image_side: int = field(default_factory=lambda: _env_int("MIN_IMAGE_SIDE", 64))
    min_image_std: float = field(default_factory=lambda: _env_float("MIN_IMAGE_STD", 8.0))

    # Sécurité : un ou plusieurs tokens séparés par des virgules (rotation sans coupure)
    api_tokens: tuple[str, ...] = field(
        default_factory=lambda: tuple(t.strip() for t in os.getenv("API_TOKEN", "").split(",") if t.strip())
    )
    rate_limit_per_minute: int = field(default_factory=lambda: _env_int("RATE_LIMIT_PER_MINUTE", 60))
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: _env_csv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
    )

    # Modèle / registre
    model_backend: str = field(default_factory=lambda: os.getenv("MODEL_BACKEND", "pytorch").lower())
    model_cache_dir: str | None = field(default_factory=lambda: os.getenv("MODEL_CACHE_DIR") or None)
    hf_token: str | None = field(default_factory=lambda: os.getenv("HF_TOKEN") or None)
    onnx_model_path: str | None = field(default_factory=lambda: os.getenv("ONNX_MODEL_PATH") or None)
    onnx_models_dir: str = field(default_factory=lambda: os.getenv("ONNX_MODELS_DIR", "models/onnx"))
    default_model_id: str = field(
        default_factory=lambda: os.getenv("DEFAULT_MODEL_ID", "resnet50-onnx-int8")
    )
    # Vide = charger tous les ONNX catalogue prêts ; sinon liste d'IDs catalogue
    enabled_models: tuple[str, ...] = field(default_factory=lambda: _env_csv("ENABLED_MODELS"))
    # IDs Hugging Face autorisés pour un éventuel chargement HF (pas depuis le client)
    hf_model_allowlist: tuple[str, ...] = field(default_factory=lambda: _env_csv("HF_MODEL_ALLOWLIST"))
    # True sur Azure Container Apps : les modèles space_only ne démarrent jamais
    azure_runtime: bool = field(default_factory=lambda: _env_bool("AZURE_RUNTIME", False))

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
