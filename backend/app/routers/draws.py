"""
draws.py — GET /api/v1/draws/next
===================================

Retourne la date du prochain tirage EuroMillions.

En mode "friday_only" (MVP) : calcule le prochain vendredi
en timezone Europe/Paris.
"""

from fastapi import APIRouter, Query

from app.models.schemas import DrawsNextResponse, DrawTargetDTO
from app.services.draw_calendar import get_next_friday

router = APIRouter()


@router.get(
    "/draws/next",
    response_model=DrawsNextResponse,
    summary="Prochain tirage",
    description="Retourne la date du prochain tirage EuroMillions (mode vendredi uniquement en MVP).",
    tags=["Tirages"],
)
def get_next_draw(
    mode: str = Query(
        default="friday_only",
        description="Mode de tirage. Seul 'friday_only' est supporté en MVP.",
    )
) -> DrawsNextResponse:
    """
    Calcule et retourne le prochain vendredi en Europe/Paris.

    Règle métier :
    - Si on est vendredi avant 21h → tirage ce soir
    - Sinon → vendredi prochain
    """
    if mode != "friday_only":
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Mode '{mode}' non supporté en MVP. Utilisez 'friday_only'.",
        )

    return DrawsNextResponse(
        draw_target=DrawTargetDTO(**get_next_friday())
    )
