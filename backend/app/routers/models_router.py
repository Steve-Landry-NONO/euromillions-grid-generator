"""
models_router.py — GET /api/v1/models
=======================================

Retourne la liste des modèles disponibles avec leurs descriptions,
disclaimers et métadonnées.

Utilisé par le frontend pour afficher les cartes modèles (US-A1).
"""

from fastapi import APIRouter

from app.models.schemas import ModelsResponse, ModelDTO
from app.services.generation_service import MODELS_CATALOG

router = APIRouter()


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="Liste des modèles",
    description="Retourne les modèles de génération disponibles avec leurs descriptions et disclaimers.",
    tags=["Modèles"],
)
def list_models() -> ModelsResponse:
    """
    Retourne OracleStats v1 et SmartGrid v1 avec toutes leurs métadonnées UI.
    """
    return ModelsResponse(
        models=[ModelDTO(**m) for m in MODELS_CATALOG]
    )
