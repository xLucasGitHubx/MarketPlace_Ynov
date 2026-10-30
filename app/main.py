"""Point d'entrée FastAPI de l'API de catégorisation Marketplace."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.business import suggest
from app.config import get_settings
from app.model import load_predictor
from app.preprocessing import ImageValidationError, validate_image
from app.schemas import ErrorResponse, HealthResponse, PredictionResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("app")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Le modèle est chargé une seule fois au démarrage (pas à chaque requête).
    # Les tests peuvent injecter un faux modèle via app.state.predictor.
    if getattr(app.state, "predictor", None) is None:
        app.state.predictor = load_predictor(
            settings.model_backend, cache_dir=settings.model_cache_dir, hf_token=settings.hf_token
        )
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Une photo d'objet → une catégorie d'annonce, un titre suggéré et un niveau de confiance.\n\n"
        "Projet Ynov — Industrialisation de l'IA dans le Cloud (thème Marketplace)."
    ),
    lifespan=lifespan,
)

ERROR_RESPONSES = {
    413: {"model": ErrorResponse, "description": "Fichier trop volumineux"},
    415: {"model": ErrorResponse, "description": "Format non supporté"},
    422: {"model": ErrorResponse, "description": "Image illisible"},
    500: {"model": ErrorResponse, "description": "Erreur d'inférence"},
}


@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
def health(request: Request) -> HealthResponse:
    """Vérifie que l'API répond et que le modèle est chargé."""
    predictor = getattr(request.app.state, "predictor", None)
    return HealthResponse(
        status="ok" if predictor is not None else "degraded",
        version=settings.app_version,
        modele=getattr(predictor, "name", None),
        modele_charge=predictor is not None,
    )


@app.post("/predict", response_model=PredictionResponse, responses=ERROR_RESPONSES, tags=["prediction"])
async def predict(
    request: Request,
    file: UploadFile = File(..., description="Photo de l'objet (JPEG, PNG ou WebP, 5 Mo max)"),
):
    """Catégorise la photo d'un objet et renvoie une suggestion d'annonce."""
    data = await file.read()
    try:
        validated = validate_image(data, settings.max_upload_bytes, settings.allowed_mime_types)
    except ImageValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    finally:
        del data

    predictor = request.app.state.predictor
    start = time.perf_counter()
    try:
        probs = await run_in_threadpool(predictor.predict_proba, validated.image)
        result = suggest(probs, threshold=settings.confidence_threshold, top_k=settings.top_k)
    except Exception:
        # Jamais de stack trace exposée au client ; on log le type d'erreur seulement.
        logger.exception("Erreur d'inférence")
        raise HTTPException(status_code=500, detail="Erreur interne lors de l'analyse de l'image.") from None
    finally:
        validated.image.close()
        del validated
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

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
    )
