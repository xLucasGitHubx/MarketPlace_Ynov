"""Point d'entrée FastAPI de l'API de catégorisation Marketplace.

Routes canoniques sous `/api/` (préfixe prévu pour la SPA) ; `/predict` et
`/health` restent disponibles en alias pour compatibilité.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.business import suggest
from app.config import get_settings
from app.model import load_predictor
from app.monitoring import NullTracker, create_tracker
from app.preprocessing import ImageValidationError, reject_non_object_image, validate_image
from app.registry import CATALOG_BY_ID, DEFAULT_MODEL_ID, ModelRegistry, build_registry
from app.schemas import ErrorResponse, HealthResponse, ModelsResponse, PredictionResponse
from app.security import RateLimiter, UploadGuardMiddleware, check_rate_limit, keep_uploads_in_memory, require_token

# Build SPA : `cd web && npm run build` puis copier `web/dist/` → `app/static/`.
STATIC_DIR = Path(__file__).resolve().parent / "static"
# Préfixes / fichiers réservés à l'API (ne pas renvoyer index.html SPA).
_SPA_RESERVED_PREFIXES = (
    "api",
    "docs",
    "redoc",
    "openapi.json",
    "health",
    "predict",
    "models",
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("app")
settings = get_settings()
keep_uploads_in_memory(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Registre + modèle(s) chargés une seule fois au démarrage.
    # Les tests peuvent injecter un faux predictor / registry via app.state.*.
    if not settings.api_tokens:
        logger.warning("API_TOKEN non défini : toutes les requêtes /predict seront refusées (401).")

    if getattr(app.state, "rate_limiter", None) is None:
        app.state.rate_limiter = RateLimiter(max_per_minute=settings.rate_limit_per_minute)

    if getattr(app.state, "registry", None) is None:
        app.state.registry = build_registry(
            onnx_dir=settings.onnx_models_dir,
            enabled_models=settings.enabled_models,
            hf_model_allowlist=settings.hf_model_allowlist,
            default_model_id=settings.default_model_id,
            cache_dir=settings.model_cache_dir,
            hf_token=settings.hf_token,
            onnx_model_path=settings.onnx_model_path,
            azure_runtime=settings.azure_runtime,
        )

    if getattr(app.state, "predictor", None) is None:
        registry: ModelRegistry = app.state.registry
        predictor = registry.default_predictor()
        if predictor is None:
            # Repli : backend legacy MODEL_BACKEND (dev / image PyTorch)
            predictor = load_predictor(
                settings.model_backend,
                cache_dir=settings.model_cache_dir,
                hf_token=settings.hf_token,
                onnx_path=settings.onnx_model_path,
            )
        app.state.predictor = predictor

    if getattr(app.state, "tracker", None) is None:
        app.state.tracker = create_tracker(
            settings.mlflow_tracking_uri, app.state.predictor.name, settings.app_version
        )
    yield
    tracker = getattr(app.state, "tracker", None)
    if tracker is not None:
        tracker.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Une photo d'objet → une catégorie d'annonce, un titre suggéré et un niveau de confiance.\n\n"
        "Projet Ynov — Industrialisation de l'IA dans le Cloud (thème Marketplace).\n\n"
        "API multi-modèles : sélection via le champ form `modele` (catalogue allowlisté). "
        "Routes préférées sous `/api/` ; `/predict` et `/health` restent des alias."
    ),
    lifespan=lifespan,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

app.add_middleware(UploadGuardMiddleware, settings=settings)

api = APIRouter(prefix="/api")

ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Modèle inconnu ou non disponible"},
    401: {"model": ErrorResponse, "description": "Token manquant ou invalide"},
    413: {"model": ErrorResponse, "description": "Fichier trop volumineux"},
    415: {"model": ErrorResponse, "description": "Format non supporté"},
    422: {"model": ErrorResponse, "description": "Image illisible ou rejetée par heuristique"},
    429: {"model": ErrorResponse, "description": "Rate-limit dépassé"},
    500: {"model": ErrorResponse, "description": "Erreur d'inférence"},
}


def _loaded_model_ids(request: Request) -> list[str]:
    registry = getattr(request.app.state, "registry", None)
    if registry is not None:
        ids = registry.loaded_ids()
        if ids:
            return ids
    predictor = getattr(request.app.state, "predictor", None)
    if predictor is not None:
        return [predictor.name]
    return []


def _resolve_predictor(request: Request, modele: str):
    """Sélectionne le predictor : registre allowlisté, sinon faux modèle de test."""
    registry: ModelRegistry | None = getattr(request.app.state, "registry", None)
    cost = None

    if registry is not None and registry.loaded_ids():
        if not registry.is_allowed(modele):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Modèle inconnu ou non autorisé : {modele!r}. "
                    "Consultez GET /api/models pour la liste allowlistée."
                ),
            )
        try:
            predictor = registry.get_predictor(modele)
        except LookupError:
            entry = registry.entries.get(modele)
            if entry and entry.spec.space_only:
                detail = (
                    f"Le modèle {modele!r} est réservé au Space Hugging Face (space_only) "
                    "et n'est pas chargé sur ce runtime."
                )
            else:
                detail = (
                    f"Le modèle {modele!r} n'est pas chargé (statut building ou fichier manquant)."
                )
            raise HTTPException(status_code=400, detail=detail) from None
        spec = CATALOG_BY_ID.get(modele)
        cost = spec.cout_estime_usd_par_million if spec else None
        return predictor, cost

    # Mode test / repli : un seul predictor injecté, sans catalogue chargé
    predictor = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise HTTPException(status_code=503, detail="Aucun modèle chargé.")
    return predictor, cost


def _health_payload(request: Request) -> HealthResponse:
    predictor = getattr(request.app.state, "predictor", None)
    loaded = _loaded_model_ids(request)
    registry = getattr(request.app.state, "registry", None)
    default_name = None
    if registry is not None and registry.loaded_ids():
        default_name = registry.default_id
    elif predictor is not None:
        default_name = predictor.name
    return HealthResponse(
        status="ok" if predictor is not None or loaded else "degraded",
        version=settings.app_version,
        modele=default_name,
        modele_charge=bool(loaded) or predictor is not None,
        modeles_charges=loaded,
    )


async def _predict_impl(
    request: Request,
    file: UploadFile,
    modele: str,
):
    data = await file.read()
    await file.close()
    try:
        validated = validate_image(data, settings.max_upload_bytes, settings.allowed_mime_types)
        reject_non_object_image(
            validated.image,
            min_side=settings.min_image_side,
            min_std=settings.min_image_std,
        )
    except ImageValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    finally:
        del data

    predictor, cost = _resolve_predictor(request, modele)
    start = time.perf_counter()
    try:
        probs = await run_in_threadpool(predictor.predict_proba, validated.image)
        result = suggest(probs, threshold=settings.confidence_threshold, top_k=settings.top_k)
    except Exception:
        logger.exception("Erreur d'inférence")
        raise HTTPException(status_code=500, detail="Erreur interne lors de l'analyse de l'image.") from None
    finally:
        validated.image.close()
        del validated
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    tracker = getattr(request.app.state, "tracker", None) or NullTracker()
    tracker.record(latency_ms, result.confidence, result.category, result.status)
    logger.info(
        "prediction categorie=%s confiance=%.3f statut=%s latence_ms=%.1f modele=%s",
        result.category, result.confidence, result.status, latency_ms, predictor.name,
    )
    return PredictionResponse(
        categorie=result.category,
        titre_suggere=result.title,
        confiance=result.confidence,
        statut=result.status,
        top3=result.top3,
        propositions=result.category_scores,
        modele=predictor.name,
        latence_ms=latency_ms,
        cout_estime_usd_par_million=cost,
    )


@api.get("/health", response_model=HealthResponse, tags=["monitoring"])
@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
def health(request: Request) -> HealthResponse:
    """Vérifie que l'API répond et liste les modèles chargés."""
    return _health_payload(request)


@api.get("/models", response_model=ModelsResponse, tags=["monitoring"])
@app.get("/models", response_model=ModelsResponse, tags=["monitoring"])
def list_models(request: Request) -> ModelsResponse:
    """Catalogue des modèles (allowlist) avec statut ready / building / space_only."""
    registry: ModelRegistry | None = getattr(request.app.state, "registry", None)
    if registry is None:
        registry = build_registry(load_models=False, default_model_id=settings.default_model_id)
    return ModelsResponse(defaut=registry.default_id, modeles=registry.list_public())


@api.post(
    "/predict",
    response_model=PredictionResponse,
    responses=ERROR_RESPONSES,
    tags=["prediction"],
    dependencies=[Depends(require_token), Depends(check_rate_limit)],
)
@app.post(
    "/predict",
    response_model=PredictionResponse,
    responses=ERROR_RESPONSES,
    tags=["prediction"],
    dependencies=[Depends(require_token), Depends(check_rate_limit)],
)
async def predict(
    request: Request,
    file: UploadFile = File(..., description="Photo de l'objet (JPEG, PNG ou WebP, 5 Mo max)"),
    modele: str = Form(
        default=DEFAULT_MODEL_ID,
        description="Identifiant catalogue allowlisté (voir GET /api/models). Défaut = prod int8.",
    ),
):
    """Catégorise la photo d'un objet et renvoie une suggestion d'annonce.

    L'image est traitée uniquement en mémoire puis libérée : rien n'est écrit sur disque
    et ni l'image ni son nom de fichier n'apparaissent dans les logs.
    """
    return await _predict_impl(request, file, modele)


app.include_router(api)


def _spa_index() -> Path | None:
    index = STATIC_DIR / "index.html"
    return index if index.is_file() else None


def _mount_spa(application: FastAPI) -> None:
    """Sert la SPA React lorsque `app/static/index.html` est présent (build Vite).

    Les handlers relisent `STATIC_DIR` à chaque requête (tests / déploiement).
    Ne masque pas `/api/*`, `/docs`, `/health`, `/predict`, `/models` déjà enregistrés.
    """

    @application.get("/", include_in_schema=False)
    async def spa_root() -> FileResponse:
        index = _spa_index()
        if index is None:
            raise HTTPException(status_code=404, detail="SPA non construite (app/static manquant).")
        return FileResponse(index)

    # Fichiers Vite sous /assets — montés seulement si le dossier existe au démarrage ;
    # sinon le catch-all ci-dessous sert les fichiers présents au moment de la requête.
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        application.mount("/assets", StaticFiles(directory=assets_dir), name="spa-assets")

    @application.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        first = full_path.split("/", 1)[0]
        if first in _SPA_RESERVED_PREFIXES or full_path in _SPA_RESERVED_PREFIXES:
            raise HTTPException(status_code=404, detail="Not Found")
        index = _spa_index()
        if index is None:
            raise HTTPException(status_code=404, detail="SPA non construite (app/static manquant).")
        candidate = (STATIC_DIR / full_path).resolve()
        try:
            candidate.relative_to(STATIC_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=404, detail="Not Found") from None
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


_mount_spa(app)
