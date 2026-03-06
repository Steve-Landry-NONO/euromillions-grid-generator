"""
generation_service.py — Pont entre l'API et les modules ML
============================================================

Ce service fait le lien entre :
- Les requêtes API (GenerateRequest avec model_id, n_tickets, options)
- Les modules ML (OracleStats, SmartGrid)
- Les réponses API (GenerateResponse avec tickets, métadonnées)

C'est ici qu'on traduit le vocabulaire "API" en vocabulaire "ML"
et inversement.
"""

import time
from pathlib import Path

from app.core.config import (
    DATA_PATH,
    ORACLE_STATS_DEFAULTS,
    SMART_GRID_DEFAULTS,
)
from app.models.schemas import (
    GenerateRequest,
    GenerateResponse,
    GenerateOptions,
    TicketDTO,
    DrawTargetDTO,
)
from app.services.draw_calendar import get_next_friday

# Import des modules ML (dans le même package services/)
from app.services.oracle_stats import OracleStats, OracleStatsConfig
from app.services.smart_grid import SmartGrid, SmartGridConfig


# ─────────────────────────────────────────────
# Métadonnées des modèles (pour /models endpoint)
# ─────────────────────────────────────────────

MODELS_CATALOG = [
    {
        "model_id": "oraclestats_v1",
        "name": "OracleStats (Science)",
        "type": "predictive_distribution",
        "short_description": "Approche probabiliste basée sur l'historique",
        "what_it_does": (
            "Analyse les tirages passés pour construire une distribution de probabilités, "
            "puis génère des grilles par échantillonnage pondéré."
        ),
        "what_it_does_not": (
            "Ne prédit pas les numéros gagnants. "
            "N'augmente pas la probabilité de gagner. "
            "EuroMillions reste un jeu de hasard indépendant."
        ),
        "disclaimer": (
            "OracleStats produit une distribution de probabilités à partir de l'historique "
            "et génère des grilles par échantillonnage. "
            "Cela ne rend pas le tirage prédictible et ne garantit aucun gain."
        ),
        "version": "v1",
    },
    {
        "model_id": "smartgrid_v1",
        "name": "SmartGrid (Optimiseur)",
        "type": "grid_optimizer",
        "short_description": "Anti-partage & diversification",
        "what_it_does": (
            "Génère des grilles 'moins humaines' (anti-dates, anti-motifs) "
            "et diversifiées, afin de réduire le risque de partager un gain si vous gagnez."
        ),
        "what_it_does_not": (
            "N'essaie pas de prédire le tirage. "
            "N'augmente pas la probabilité de gagner. "
            "Le score affiché est un score anti-partage, pas une probabilité de gain."
        ),
        "disclaimer": (
            "SmartGrid n'essaie pas de prédire le tirage. "
            "Il optimise des grilles 'moins humaines' et diversifiées "
            "afin de réduire le risque de partager un gain si vous gagnez. "
            "Cela n'augmente pas la probabilité de gagner."
        ),
        "version": "v1",
    },
]

GLOBAL_DISCLAIMER = (
    "EuroMillions est un jeu de hasard. "
    "Les résultats sont aléatoires et indépendants. "
    "Cette application génère des grilles à titre informatif/pédagogique "
    "et n'offre aucune garantie de gain."
)


# ─────────────────────────────────────────────
# Service de génération
# ─────────────────────────────────────────────

class GenerationService:
    """
    Orchestre la génération de grilles selon le modèle demandé.

    Ce service est instancié une fois au démarrage et réutilisé
    pour toutes les requêtes (stateless sauf le cache OracleStats).
    """

    def __init__(self, data_path: Path = DATA_PATH):
        self.data_path = data_path
        # OracleStats garde le dataset en mémoire → on le réutilise
        self._oracle: OracleStats | None = None

    def _get_oracle(self, options: GenerateOptions | None) -> OracleStats:
        """
        Retourne une instance OracleStats.
        Si les options sont les valeurs par défaut, on réutilise l'instance cachée.
        Sinon on en crée une nouvelle (seed ou window_size personnalisé).
        """
        has_custom_options = options and (
            options.seed is not None or
            options.window_size is not None
        )

        if has_custom_options or self._oracle is None:
            config = OracleStatsConfig(
                window_size=options.window_size if options and options.window_size
                            else ORACLE_STATS_DEFAULTS["window_size"],
                alpha=ORACLE_STATS_DEFAULTS["alpha"],
                lambda_uniform=ORACLE_STATS_DEFAULTS["lambda_uniform"],
                seed=options.seed if options else None,
            )
            oracle = OracleStats(self.data_path, config)
            # Si pas d'options custom, on met en cache pour les prochaines requêtes
            if not has_custom_options:
                self._oracle = oracle
            return oracle

        return self._oracle

    def _get_smart_grid(self, options: GenerateOptions | None) -> SmartGrid:
        """Crée une instance SmartGrid avec les options de la requête."""
        sum_min = options.sum_range_min if options and options.sum_range_min \
                  else SMART_GRID_DEFAULTS["sum_range"][0]
        sum_max = options.sum_range_max if options and options.sum_range_max \
                  else SMART_GRID_DEFAULTS["sum_range"][1]

        config = SmartGridConfig(
            n_candidates=SMART_GRID_DEFAULTS["n_candidates"],
            sum_range=(sum_min, sum_max),
            avoid_numbers=options.avoid_numbers if options else [],
            avoid_stars=options.avoid_stars if options else [],
            max_common=SMART_GRID_DEFAULTS["max_common"],
            seed=options.seed if options else None,
        )
        return SmartGrid(config)

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        """
        Point d'entrée principal du service.

        1. Récupère le modèle demandé
        2. Lance la génération
        3. Construit et retourne la réponse API standardisée
        """
        t_start = time.perf_counter()
        options = request.options

        # ── Génération selon le modèle ──────────────
        if request.model_id == "oraclestats_v1":
            model = self._get_oracle(options)
            raw_tickets = model.generate(n_tickets=request.n_tickets)

            tickets_dto = [
                TicketDTO(
                    numbers=t.numbers,
                    stars=t.stars,
                    score=None,
                    explain=None,
                    explanation=t.explanation,
                    diversity_relaxed=None,
                )
                for t in raw_tickets
            ]
            model_name = "OracleStats (Science)"

        elif request.model_id == "smartgrid_v1":
            model = self._get_smart_grid(options)
            raw_tickets = model.generate(n_tickets=request.n_tickets)

            tickets_dto = [
                TicketDTO(
                    numbers=t.numbers,
                    stars=t.stars,
                    score=t.score,
                    explain=t.explain,
                    explanation=t._main_reasons(),
                    diversity_relaxed=t.diversity_relaxed,
                )
                for t in raw_tickets
            ]
            model_name = "SmartGrid (Optimiseur)"

        else:
            # Ce cas ne devrait jamais arriver (Pydantic valide model_id en amont)
            raise ValueError(f"Modèle inconnu : {request.model_id}")

        # ── Métadonnées de réponse ───────────────────
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        draw_target = DrawTargetDTO(**get_next_friday())

        # Disclaimer spécifique au modèle
        model_info = next(m for m in MODELS_CATALOG if m["model_id"] == request.model_id)

        return GenerateResponse(
            model_id=request.model_id,
            model_name=model_name,
            draw_target=draw_target,
            n_tickets=len(tickets_dto),
            tickets=tickets_dto,
            generation_time_ms=round(elapsed_ms, 1),
            disclaimer=model_info["disclaimer"],
        )
