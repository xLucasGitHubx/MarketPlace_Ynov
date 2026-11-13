"""Schémas Pydantic des réponses de l'API (affichés dans Swagger)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    version: str = Field(examples=["0.6.0"])
    modele: str | None = Field(default=None, examples=["resnet50-onnx-int8"])
    modele_charge: bool = Field(examples=[True])
    modeles_charges: list[str] = Field(
        default_factory=list,
        description="Identifiants des modèles réellement chargés en mémoire",
        examples=[["resnet50-onnx-int8"]],
    )


class ModelInfo(BaseModel):
    id: str = Field(examples=["resnet50-onnx-int8"])
    label: str = Field(examples=["ResNet-50 ONNX int8 (prod)"])
    source: str = Field(examples=["models/onnx/resnet50-int8-static.onnx"])
    statut: Literal["ready", "building", "space_only"] = Field(examples=["ready"])
    charge: bool = Field(examples=[True], description="True si le predictor est chargé en mémoire")
    accuracy: float | None = Field(default=None, examples=[0.685])
    p50_ms: float | None = Field(default=None, examples=[21.5])
    p95_ms: float | None = Field(default=None, examples=[28.6])
    taille_mo: float | None = Field(default=None, examples=[24.9])
    cout_estime_usd_par_million: float | None = Field(default=None, examples=[1.8])
    space_only: bool = Field(default=False)


class ModelsResponse(BaseModel):
    defaut: str = Field(examples=["resnet50-onnx-int8"])
    modeles: list[ModelInfo]


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
    modele: str = Field(examples=["resnet50-onnx-int8"])
    latence_ms: float = Field(examples=[48.2], description="Temps d'inférence + logique métier")
    cout_estime_usd_par_million: float | None = Field(
        default=None,
        examples=[1.8],
        description="Coût Azure estimé ($ / million d'images) si les métriques du modèle sont connues",
    )


class ErrorResponse(BaseModel):
    detail: str = Field(examples=["Format non supporté. Formats acceptés : JPEG, PNG, WebP."])
