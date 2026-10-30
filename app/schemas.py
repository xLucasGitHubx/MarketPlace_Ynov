"""Schémas Pydantic des réponses de l'API (affichés dans Swagger)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    version: str = Field(examples=["0.2.0"])
    modele: str | None = Field(default=None, examples=["resnet50-pytorch-fp32"])
    modele_charge: bool = Field(examples=[True])


class TopClass(BaseModel):
    label: str = Field(examples=["laptop"])
    categorie: str = Field(examples=["Électronique"])
    score: float = Field(examples=[0.92])


class CategoryProposal(BaseModel):
    categorie: str = Field(examples=["Électronique"])
    score: float = Field(examples=[0.95])
    titre: str = Field(examples=["Ordinateur portable"])


class PredictionResponse(BaseModel):
    categorie: str = Field(examples=["Électronique"])
    titre_suggere: str = Field(examples=["Ordinateur portable"])
    confiance: float = Field(ge=0, le=1, examples=[0.92])
    statut: Literal["auto", "a_confirmer"] = Field(
        examples=["auto"],
        description="`auto` : catégorie pré-remplie ; `a_confirmer` : le vendeur choisit parmi `propositions`.",
    )
    top3: list[TopClass] = Field(description="3 classes brutes les plus probables du modèle")
    propositions: list[CategoryProposal] = Field(description="Jusqu'à 3 catégories d'annonce classées par score")
    modele: str = Field(examples=["resnet50-pytorch-fp32"])
    latence_ms: float = Field(examples=[48.2], description="Temps d'inférence + logique métier")


class ErrorResponse(BaseModel):
    detail: str = Field(examples=["Format non supporté. Formats acceptés : JPEG, PNG, WebP."])
