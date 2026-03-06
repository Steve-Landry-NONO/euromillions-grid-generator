"""
health.py — GET /api/v1/health
================================

Endpoint de healthcheck utilisé pour :
- Vérifier que l'API est vivante (monitoring, load balancer)
- Confirmer que le dataset est chargé
- Exposer la version de l'app et du dataset
"""

from fastapi import APIRouter, Depends

from app.models.schemas import HealthResponse
from app.services.data_loader import DataLoader, get_loader
from app.core.config import APP_VERSION

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Healthcheck",
    description="Vérifie que l'API fonctionne et que le dataset est chargé.",
    tags=["Infra"],
)
def health_check(loader: DataLoader = Depends(get_loader)) -> HealthResponse:
    """
    Retourne le statut de l'application.

    Utilisé par le monitoring et le Runbook (Incident A).
    """
    meta = loader.get_metadata()
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        data_version=meta.get("data_version", "unknown"),
        dataset_rows=meta.get("rows", 0),
        dataset_last_date=meta.get("last_date", "unknown"),
    )
