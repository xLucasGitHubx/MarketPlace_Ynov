"""Schémas Pydantic des réponses de l'API (affichés dans Swagger)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    version: str = Field(examples=["0.1.0"])


class ImageMetadata(BaseModel):
    filename: str | None = Field(default=None, examples=["velo.jpg"])
    mime_type: str = Field(examples=["image/jpeg"])
    taille_octets: int = Field(examples=[245_123])
    largeur: int = Field(examples=[1024])
    hauteur: int = Field(examples=[768])


class ErrorResponse(BaseModel):
    detail: str = Field(examples=["Format non supporté. Formats acceptés : JPEG, PNG, WebP."])
