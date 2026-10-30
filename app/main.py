"""Point d'entrée FastAPI de l'API de catégorisation Marketplace."""

from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.config import get_settings
from app.preprocessing import ImageValidationError, validate_image
from app.schemas import ErrorResponse, HealthResponse, ImageMetadata

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Une photo d'objet → une catégorie d'annonce, un titre suggéré et un niveau de confiance.\n\n"
        "Projet Ynov — Industrialisation de l'IA dans le Cloud (thème Marketplace)."
    ),
)

ERROR_RESPONSES = {
    413: {"model": ErrorResponse, "description": "Fichier trop volumineux"},
    415: {"model": ErrorResponse, "description": "Format non supporté"},
    422: {"model": ErrorResponse, "description": "Image illisible"},
}


@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
def health() -> HealthResponse:
    """Vérifie que l'API répond."""
    return HealthResponse(status="ok", version=settings.app_version)


@app.post("/predict", response_model=ImageMetadata, responses=ERROR_RESPONSES, tags=["prediction"])
async def predict(file: UploadFile = File(..., description="Photo de l'objet (JPEG, PNG ou WebP, 5 Mo max)")):
    """Reçoit une image et renvoie ses métadonnées (itération 1 : pas encore de modèle)."""
    data = await file.read()
    try:
        validated = validate_image(data, settings.max_upload_bytes, settings.allowed_mime_types)
    except ImageValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    finally:
        del data

    return ImageMetadata(
        filename=file.filename,
        mime_type=validated.mime_type,
        taille_octets=validated.size_bytes,
        largeur=validated.width,
        hauteur=validated.height,
    )
