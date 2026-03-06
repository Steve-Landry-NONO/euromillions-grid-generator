"""
generate.py — POST /api/v1/generate
=====================================

L'endpoint principal : reçoit une requête de génération,
délègue au GenerationService, retourne les grilles.

FLUX COMPLET :
    Client → POST /generate (JSON)
           → Pydantic valide le payload (422 si invalide)
           → GenerationService.generate()
               → OracleStats ou SmartGrid
           → GenerateResponse (JSON)

GESTION D'ERREURS :
    422 Unprocessable Entity : payload invalide (Pydantic automatique)
    400 Bad Request          : contraintes impossibles
    500 Internal Server Error: erreur inattendue (loguée, pas stacktrace)
"""

import logging
from fastapi import APIRouter, HTTPException

from app.models.schemas import GenerateRequest, GenerateResponse
from app.services.generation_service import GenerationService
from app.core.config import DATA_PATH

logger = logging.getLogger(__name__)
router = APIRouter()

# Instance unique du service (créée au démarrage du module)
_generation_service = GenerationService(data_path=DATA_PATH)


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Générer des grilles EuroMillions",
    description=(
        "Génère 1, 5 ou 10 grilles EuroMillions selon le modèle choisi. "
        "Retourne les tickets avec leurs explications et la date cible du tirage. "
        "**Aucune garantie de gain. EuroMillions est un jeu de hasard.**"
    ),
    tags=["Génération"],
    responses={
        200: {"description": "Grilles générées avec succès."},
        400: {"description": "Contraintes impossibles (ex: trop de numéros à éviter)."},
        422: {"description": "Payload invalide (model_id inconnu, n_tickets hors {1,5,10}, etc.)."},
        500: {"description": "Erreur interne du serveur."},
    },
)
def generate_tickets(request: GenerateRequest) -> GenerateResponse:
    """
    Génère des grilles EuroMillions.

    **Exemple de body :**
    ```json
    {
        "model_id": "smartgrid_v1",
        "n_tickets": 5,
        "mode": "friday_only",
        "options": {
            "avoid_numbers": [7, 13],
            "seed": 42
        }
    }
    ```
    """
    logger.info(
        f"[generate] model={request.model_id} n_tickets={request.n_tickets} "
        f"mode={request.mode}"
    )

    try:
        response = _generation_service.generate(request)

        logger.info(
            f"[generate] ✅ OK — {response.n_tickets} tickets "
            f"en {response.generation_time_ms}ms"
        )
        return response

    except ValueError as e:
        # Erreur de contrainte métier (ex: trop de numéros à éviter)
        logger.warning(f"[generate] 400 — {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Erreur inattendue : on logue mais on n'expose pas la stacktrace
        logger.error(f"[generate] 500 — {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erreur interne lors de la génération. Réessaie dans quelques instants.",
        )
