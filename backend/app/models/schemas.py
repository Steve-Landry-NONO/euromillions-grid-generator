"""
schemas.py — Schémas Pydantic (validation des données API)
===========================================================

Pydantic est la bibliothèque qui valide automatiquement les données
entrantes et sortantes de l'API.

COMMENT ÇA MARCHE :
- Chaque classe hérite de BaseModel.
- FastAPI utilise ces classes pour :
  1. Valider les données reçues (payload JSON → erreur 422 si invalide)
  2. Sérialiser les réponses (objet Python → JSON propre)
  3. Générer automatiquement la doc OpenAPI (/docs)

ORGANISATION :
- Les "Request" schemas valident ce que l'utilisateur envoie.
- Les "Response" schemas décrivent ce que l'API renvoie.
"""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────
# Enums / constantes métier
# ─────────────────────────────────────────────

ModelId = Literal["oraclestats_v1", "smartgrid_v1"]
DrawMode = Literal["friday_only"]
NTickets = Literal[1, 5, 10]


# ─────────────────────────────────────────────
# Sous-schémas partagés
# ─────────────────────────────────────────────

class TicketDTO(BaseModel):
    """
    Représente une grille EuroMillions dans les réponses API.

    numbers     : liste de 5 entiers entre 1 et 50
    stars       : liste de 2 entiers entre 1 et 12
    score       : score anti-partage SmartGrid (None pour OracleStats)
    explain     : détails du score (pénalités/bonus)
    explanation : texte d'explication lisible par l'utilisateur
    """
    numbers: list[int] = Field(
        ...,
        description="5 numéros uniques entre 1 et 50",
        min_length=5,
        max_length=5,
    )
    stars: list[int] = Field(
        ...,
        description="2 étoiles uniques entre 1 et 12",
        min_length=2,
        max_length=2,
    )
    score: Optional[float] = Field(
        None,
        description="Score anti-partage SmartGrid (0=faible, 1=excellent). Absent pour OracleStats.",
        ge=0.0,
        le=1.0,
    )
    explain: Optional[dict] = Field(
        None,
        description="Détail des pénalités/bonus SmartGrid.",
    )
    explanation: Optional[str] = Field(
        None,
        description="Texte explicatif lisible par l'utilisateur.",
    )
    diversity_relaxed: Optional[bool] = Field(
        None,
        description="True si la contrainte de diversité a été assouplie (SmartGrid uniquement).",
    )

    @field_validator("numbers")
    @classmethod
    def validate_numbers(cls, v: list[int]) -> list[int]:
        if len(set(v)) != 5:
            raise ValueError("Les 5 numéros doivent être distincts.")
        if not all(1 <= n <= 50 for n in v):
            raise ValueError("Chaque numéro doit être entre 1 et 50.")
        return sorted(v)

    @field_validator("stars")
    @classmethod
    def validate_stars(cls, v: list[int]) -> list[int]:
        if len(set(v)) != 2:
            raise ValueError("Les 2 étoiles doivent être distinctes.")
        if not all(1 <= s <= 12 for s in v):
            raise ValueError("Chaque étoile doit être entre 1 et 12.")
        return sorted(v)


class DrawTargetDTO(BaseModel):
    """Date cible du prochain tirage."""
    date: str = Field(..., description="Date ISO du prochain tirage (ex: '2026-03-07')")
    mode: DrawMode = Field(..., description="Mode de tirage")
    label: str = Field(..., description="Label lisible (ex: 'Vendredi 7 mars 2026')")


class ModelDTO(BaseModel):
    """Description d'un modèle de génération."""
    model_id: ModelId
    name: str
    type: str
    short_description: str
    what_it_does: str
    what_it_does_not: str
    disclaimer: str
    version: str = "v1"


# ─────────────────────────────────────────────
# Request schemas (entrées API)
# ─────────────────────────────────────────────

class GenerateRequest(BaseModel):
    """
    Payload pour POST /api/v1/generate

    Exemple de body JSON valide :
    {
        "model_id": "smartgrid_v1",
        "n_tickets": 5,
        "mode": "friday_only",
        "options": {
            "avoid_numbers": [7, 13],
            "avoid_stars": [1],
            "seed": 42
        }
    }
    """
    model_id: ModelId = Field(
        ...,
        description="Identifiant du modèle à utiliser.",
    )
    n_tickets: NTickets = Field(
        1,
        description="Nombre de grilles à générer : 1, 5 ou 10.",
    )
    mode: DrawMode = Field(
        "friday_only",
        description="Mode de tirage cible.",
    )
    options: Optional[GenerateOptions] = Field(
        None,
        description="Options avancées (optionnelles).",
    )


class GenerateOptions(BaseModel):
    """
    Options avancées pour la génération.
    Toutes optionnelles — on utilise les valeurs par défaut si absent.
    """
    avoid_numbers: list[int] = Field(
        default_factory=list,
        description="Numéros à exclure des grilles générées.",
    )
    avoid_stars: list[int] = Field(
        default_factory=list,
        description="Étoiles à exclure des grilles générées.",
    )
    seed: Optional[int] = Field(
        None,
        description="Graine aléatoire pour reproductibilité.",
    )
    # OracleStats uniquement
    window_size: Optional[int] = Field(
        None,
        description="[OracleStats] Nombre de tirages historiques à analyser.",
        ge=10,
        le=2000,
    )
    # SmartGrid uniquement
    sum_range_min: Optional[int] = Field(
        None,
        description="[SmartGrid] Somme minimale des 5 numéros.",
        ge=15,
        le=250,
    )
    sum_range_max: Optional[int] = Field(
        None,
        description="[SmartGrid] Somme maximale des 5 numéros.",
        ge=15,
        le=250,
    )

    @model_validator(mode="after")
    def validate_avoid_lists(self) -> GenerateOptions:
        """Vérifie que les listes 'avoid' ne vident pas le pool."""
        if len(self.avoid_numbers) > 45:
            raise ValueError(
                "avoid_numbers ne peut pas contenir plus de 45 numéros "
                "(il faut au moins 5 numéros disponibles)."
            )
        if len(self.avoid_stars) > 10:
            raise ValueError(
                "avoid_stars ne peut pas contenir plus de 10 étoiles "
                "(il faut au moins 2 étoiles disponibles)."
            )
        if self.sum_range_min and self.sum_range_max:
            if self.sum_range_min >= self.sum_range_max:
                raise ValueError("sum_range_min doit être < sum_range_max.")
        return self


# Nécessaire car GenerateRequest référence GenerateOptions avant sa définition
GenerateRequest.model_rebuild()


# ─────────────────────────────────────────────
# Response schemas (sorties API)
# ─────────────────────────────────────────────

class GenerateResponse(BaseModel):
    """
    Réponse de POST /api/v1/generate

    Contient les tickets générés + métadonnées.
    """
    model_id: ModelId
    model_name: str
    draw_target: DrawTargetDTO
    n_tickets: int
    tickets: list[TicketDTO]
    generation_time_ms: float = Field(
        ...,
        description="Temps de génération en millisecondes.",
    )
    disclaimer: str = Field(
        ...,
        description="Disclaimer légal obligatoire.",
    )


class HealthResponse(BaseModel):
    """Réponse de GET /api/v1/health"""
    status: str = "ok"
    version: str
    data_version: str
    dataset_rows: int
    dataset_last_date: str


class ModelsResponse(BaseModel):
    """Réponse de GET /api/v1/models"""
    models: list[ModelDTO]


class DrawsNextResponse(BaseModel):
    """Réponse de GET /api/v1/draws/next"""
    draw_target: DrawTargetDTO


class ErrorResponse(BaseModel):
    """Format standard des erreurs API."""
    error: str
    detail: Optional[str] = None
