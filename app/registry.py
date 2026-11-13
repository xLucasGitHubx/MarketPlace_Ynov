"""Catalogue multi-modèles et registre chargé au démarrage de l'API.

Le client ne peut sélectionner qu'un ID du catalogue (allowlist stricte) :
aucun identifiant Hugging Face arbitraire n'est accepté depuis la requête.
Les modèles `space_only` restent en métadonnées et ne sont jamais chargés
sur le runtime Azure / API locale.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from app.model import OnnxPredictor, Predictor, PytorchPredictor

logger = logging.getLogger(__name__)

ModelStatus = Literal["ready", "building", "space_only"]

DEFAULT_MODEL_ID = "resnet50-onnx-int8"
DEFAULT_ONNX_DIR = Path("models/onnx")
DEFAULT_METRICS_PATH = Path("docs/preuves/eval/catalog_metrics.json")

# FinOps fort volume (aligné FINOPS.md / evaluate_catalog.py).
BASELINE_P95_MS = 28.6
BASELINE_USD_PER_MILLION = 1.8


def estimate_cost_usd_per_million(p95_ms: float | None) -> float | None:
    """USD / million d'images ≈ baseline ResNet × (p95 / p95_baseline)."""
    if p95_ms is None or p95_ms <= 0:
        return None
    return round(BASELINE_USD_PER_MILLION * (p95_ms / BASELINE_P95_MS), 2)


def load_catalog_metrics(path: Path | str | None = None) -> dict[str, dict[str, Any]]:
    """Charge `docs/preuves/eval/catalog_metrics.json` s'il est présent.

    Renvoie un dict `{model_id: {accuracy, p50_ms, ...}}`. Fichier absent → {}.
    """
    metrics_path = Path(path) if path else DEFAULT_METRICS_PATH
    if not metrics_path.is_file():
        return {}
    try:
        raw = json.loads(metrics_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Impossible de lire les métriques catalogue %s", metrics_path)
        return {}
    models = raw.get("models")
    if not isinstance(models, dict):
        logger.warning("catalog_metrics.json : clé 'models' manquante ou invalide")
        return {}
    out: dict[str, dict[str, Any]] = {}
    for mid, entry in models.items():
        if isinstance(entry, dict):
            out[str(mid)] = entry
    return out


def apply_metrics_to_spec(spec: ModelSpec, metrics: dict[str, Any] | None) -> ModelSpec:
    """Fusionne les champs perf/coût d'une entrée JSON dans un ModelSpec."""
    if not metrics:
        return spec
    kwargs: dict[str, Any] = {}
    if "accuracy" in metrics and metrics["accuracy"] is not None:
        kwargs["accuracy"] = float(metrics["accuracy"])
    if "p50_ms" in metrics and metrics["p50_ms"] is not None:
        kwargs["p50_ms"] = float(metrics["p50_ms"])
    if "p95_ms" in metrics and metrics["p95_ms"] is not None:
        kwargs["p95_ms"] = float(metrics["p95_ms"])
    if "size_mb" in metrics and metrics["size_mb"] is not None:
        kwargs["size_mb"] = float(metrics["size_mb"])
    if "cout_estime_usd_par_million" in metrics:
        cost = metrics["cout_estime_usd_par_million"]
        kwargs["cout_estime_usd_par_million"] = None if cost is None else float(cost)
    elif "p95_ms" in kwargs:
        kwargs["cout_estime_usd_par_million"] = estimate_cost_usd_per_million(kwargs["p95_ms"])
    return replace(spec, **kwargs) if kwargs else spec


@dataclass(frozen=True)
class ModelSpec:
    """Métadonnées figées du catalogue (indépendantes des fichiers présents)."""

    id: str
    label: str
    source: str
    onnx_filenames: tuple[str, ...] = ()
    hf_model_id: str | None = None
    space_only: bool = False
    accuracy: float | None = None
    p50_ms: float | None = None
    p95_ms: float | None = None
    size_mb: float | None = None
    cout_estime_usd_par_million: float | None = None


# Catalogue exposé par GET /models (même si le fichier ONNX n'existe pas encore).
CATALOG: tuple[ModelSpec, ...] = (
    ModelSpec(
        id="resnet50-onnx-int8",
        label="ResNet-50 ONNX int8 (prod)",
        source="models/onnx/resnet50-int8-static.onnx",
        onnx_filenames=("resnet50-int8-static.onnx", "resnet50-onnx-int8.onnx"),
        accuracy=0.685,
        p50_ms=21.5,
        p95_ms=28.6,
        size_mb=24.9,
        cout_estime_usd_par_million=1.8,
    ),
    ModelSpec(
        id="efficientnet-b0-onnx-int8",
        label="EfficientNet-B0 ONNX int8",
        source="HF google/efficientnet-b0 → ONNX int8",
        onnx_filenames=("efficientnet-b0-int8-static.onnx", "efficientnet-b0-onnx-int8.onnx"),
        hf_model_id="google/efficientnet-b0",
        # Estimations (remplacées si catalog_metrics.json présent).
        accuracy=0.66,
        p50_ms=10.0,
        p95_ms=13.0,
        size_mb=5.5,
        cout_estime_usd_par_million=0.82,
    ),
    ModelSpec(
        id="mobilenet-v3-small-onnx-int8",
        label="MobileNetV3-Small ONNX int8",
        source="HF facebook/mobilenet_v3_small → ONNX int8",
        onnx_filenames=("mobilenet-v3-small-int8-static.onnx", "mobilenet-v3-small-onnx-int8.onnx"),
        hf_model_id="facebook/mobilenet_v3_small",
        accuracy=0.60,
        p50_ms=6.5,
        p95_ms=9.0,
        size_mb=2.5,
        cout_estime_usd_par_million=0.57,
    ),
    ModelSpec(
        id="student-kd-mobilenet-int8",
        label="Student KD MobileNet int8",
        source="distillation ResNet-50 → MobileNetV3-Small",
        onnx_filenames=("student-kd-mobilenet-int8.onnx", "student-kd-mobilenet-int8-static.onnx"),
        accuracy=0.64,
        p50_ms=7.0,
        p95_ms=9.5,
        size_mb=2.5,
        cout_estime_usd_par_million=0.60,
    ),
    ModelSpec(
        id="clip-vit-b32",
        label="CLIP ViT-B/32 (Space ZeroGPU)",
        source="HF openai/clip-vit-base-patch32",
        hf_model_id="openai/clip-vit-base-patch32",
        space_only=True,
        accuracy=0.765,
        p50_ms=83.0,
        p95_ms=114.0,
        size_mb=577.0,
        cout_estime_usd_par_million=0.0,
    ),
)

CATALOG_BY_ID: dict[str, ModelSpec] = {s.id: s for s in CATALOG}


@dataclass
class ModelEntry:
    spec: ModelSpec
    status: ModelStatus
    loaded: bool = False
    predictor: Predictor | None = None
    resolved_path: str | None = None


@dataclass
class ModelRegistry:
    """Registre runtime : métadonnées catalogue + predictors chargés."""

    entries: dict[str, ModelEntry] = field(default_factory=dict)
    default_id: str = DEFAULT_MODEL_ID
    onnx_dir: Path = DEFAULT_ONNX_DIR
    allowlist: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.allowlist:
            self.allowlist = frozenset(CATALOG_BY_ID)

    def is_allowed(self, model_id: str) -> bool:
        return model_id in self.allowlist and model_id in CATALOG_BY_ID

    def get_entry(self, model_id: str) -> ModelEntry:
        if model_id not in self.entries:
            raise KeyError(model_id)
        return self.entries[model_id]

    def get_predictor(self, model_id: str) -> Predictor:
        """Renvoie le predictor chargé, ou lève KeyError / LookupError."""
        if not self.is_allowed(model_id):
            raise KeyError(model_id)
        entry = self.entries.get(model_id)
        if entry is None or not entry.loaded or entry.predictor is None:
            raise LookupError(model_id)
        if entry.spec.space_only:
            raise LookupError(model_id)
        return entry.predictor

    def loaded_ids(self) -> list[str]:
        return [mid for mid, e in self.entries.items() if e.loaded and e.predictor is not None]

    def default_predictor(self) -> Predictor | None:
        try:
            return self.get_predictor(self.default_id)
        except (KeyError, LookupError):
            loaded = self.loaded_ids()
            if not loaded:
                return None
            return self.entries[loaded[0]].predictor

    def list_public(self) -> list[dict]:
        """Payload JSON pour GET /models."""
        out = []
        for mid in CATALOG_BY_ID:
            entry = self.entries.get(mid)
            if entry is None:
                spec = CATALOG_BY_ID[mid]
                status: ModelStatus = "space_only" if spec.space_only else "building"
                loaded = False
            else:
                spec = entry.spec
                status = entry.status
                loaded = entry.loaded
            out.append(
                {
                    "id": spec.id,
                    "label": spec.label,
                    "source": spec.source,
                    "statut": status,
                    "charge": loaded,
                    "accuracy": spec.accuracy,
                    "p50_ms": spec.p50_ms,
                    "p95_ms": spec.p95_ms,
                    "taille_mo": spec.size_mb,
                    "cout_estime_usd_par_million": spec.cout_estime_usd_par_million,
                    "space_only": spec.space_only,
                }
            )
        return out


def _find_onnx_file(spec: ModelSpec, onnx_dir: Path) -> Path | None:
    for name in spec.onnx_filenames:
        path = onnx_dir / name
        if path.is_file():
            return path
    return None


def _initial_status(spec: ModelSpec, onnx_dir: Path) -> ModelStatus:
    if spec.space_only:
        return "space_only"
    if spec.onnx_filenames and _find_onnx_file(spec, onnx_dir) is not None:
        return "ready"
    return "building"


def build_registry(
    *,
    onnx_dir: str | Path | None = None,
    enabled_models: tuple[str, ...] = (),
    hf_model_allowlist: tuple[str, ...] = (),
    default_model_id: str = DEFAULT_MODEL_ID,
    load_models: bool = True,
    cache_dir: str | None = None,
    hf_token: str | None = None,
    onnx_model_path: str | None = None,
    azure_runtime: bool = False,
    metrics_path: str | Path | None = None,
) -> ModelRegistry:
    """Construit le registre et charge les predictors autorisés disponibles.

    - `enabled_models` vide : charge tout ONNX catalogue prêt (fichier présent).
    - `space_only` / runtime Azure : jamais chargés.
    - HF : uniquement si l'ID catalogue est activé ET `hf_model_id` ∈ HF_MODEL_ALLOWLIST
      (CLIP reste space_only → non chargé).
    - Métriques : si `docs/preuves/eval/catalog_metrics.json` (ou `metrics_path`)
      est présent, accuracy / latence / taille / $/M écrasent les valeurs figées.
    """
    directory = Path(onnx_dir) if onnx_dir else DEFAULT_ONNX_DIR
    # Allowlist stricte = IDs catalogue uniquement (jamais un HF id client).
    allowlist = frozenset(CATALOG_BY_ID)
    registry = ModelRegistry(default_id=default_model_id, onnx_dir=directory, allowlist=allowlist)

    enabled = set(enabled_models) if enabled_models else None
    hf_ok = set(hf_model_allowlist)
    catalog_metrics = load_catalog_metrics(metrics_path)

    # Chemin ONNX legacy (ONNX_MODEL_PATH) → resnet50-onnx-int8 si pertinent
    legacy_path = Path(onnx_model_path) if onnx_model_path else None

    for base_spec in CATALOG:
        spec = apply_metrics_to_spec(base_spec, catalog_metrics.get(base_spec.id))
        status = _initial_status(spec, directory)
        if legacy_path and spec.id == DEFAULT_MODEL_ID and legacy_path.is_file():
            status = "ready"
        entry = ModelEntry(spec=spec, status=status)
        registry.entries[spec.id] = entry

        if not load_models:
            continue
        # Jamais de chargement space_only (Azure ou local) : évite OOM / cold start 2 Go+.
        if spec.space_only:
            entry.status = "space_only"
            if azure_runtime:
                logger.debug("Registre Azure : %s ignoré (space_only)", spec.id)
            continue
        if enabled is not None and spec.id not in enabled:
            continue

        # ONNX local
        path = _find_onnx_file(spec, directory)
        if path is None and legacy_path and spec.id == DEFAULT_MODEL_ID and legacy_path.is_file():
            path = legacy_path
        if path is not None:
            try:
                predictor = OnnxPredictor(str(path), name=spec.id)
                entry.predictor = predictor
                entry.loaded = True
                entry.status = "ready"
                entry.resolved_path = str(path)
                logger.info("Registre : modèle chargé %s ← %s", spec.id, path)
            except Exception:
                logger.exception("Registre : échec chargement ONNX %s", spec.id)
                entry.status = "building"
            continue

        # Backend HF allowlisté (hors space_only) — réservé aux futurs modèles CPU HF
        if (
            spec.hf_model_id
            and not spec.space_only
            and spec.hf_model_id in hf_ok
            and (enabled is None or spec.id in enabled)
        ):
            try:
                predictor = PytorchPredictor(
                    model_id=spec.hf_model_id, cache_dir=cache_dir, hf_token=hf_token
                )
                predictor.name = spec.id
                entry.predictor = predictor
                entry.loaded = True
                entry.status = "ready"
                logger.info("Registre : modèle HF chargé %s ← %s", spec.id, spec.hf_model_id)
            except Exception:
                logger.exception("Registre : échec chargement HF %s", spec.id)
                entry.status = "building"

    if registry.default_id not in registry.entries or not registry.entries[registry.default_id].loaded:
        loaded = registry.loaded_ids()
        if loaded:
            registry.default_id = loaded[0]

    return registry
