"""
conftest.py — Fixtures partagées entre tous les tests
======================================================

Les fixtures pytest sont des "usines" réutilisables qui fournissent
des objets préconfigurés à chaque test.

COMMENT ÇA MARCHE :
    def test_quelquechose(load_dataset):  ← pytest injecte la fixture automatiquement
        df = load_dataset
        assert len(df) > 0

FIXTURES DISPONIBLES :
    data_path       → chemin Path vers le CSV de test
    load_dataset    → DataFrame pandas prêt à l'emploi
    seed            → graine reproductible (42)
    oracle_model    → instance OracleStats configurée
    smartgrid_model → instance SmartGrid configurée
"""

import sys
import os
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

# ── Ajout du chemin backend au PYTHONPATH ──────────────────────
# Permet d'importer app.services.* depuis les tests
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.oracle_stats import OracleStats, OracleStatsConfig
from app.services.smart_grid import SmartGrid, SmartGridConfig


# ─────────────────────────────────────────────
# Chemins
# ─────────────────────────────────────────────

@pytest.fixture(scope="session")
def data_path() -> Path:
    """
    Chemin vers le CSV de test.
    scope="session" → calculé une seule fois pour toute la session pytest.
    """
    path = Path(__file__).parent.parent / "app" / "data" / "euromillions_history.csv"
    assert path.exists(), (
        f"Dataset de test introuvable : {path}\n"
        f"Génère-le avec : python tests/generate_test_data.py"
    )
    return path


@pytest.fixture(scope="session")
def load_dataset(data_path) -> pd.DataFrame:
    """
    DataFrame pandas chargé depuis le CSV.
    scope="session" → chargé une seule fois, réutilisé par tous les tests.
    """
    df = pd.read_csv(data_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


@pytest.fixture(scope="session")
def seed() -> int:
    """Graine aléatoire fixe pour des tests reproductibles."""
    return 42


@pytest.fixture(scope="session")
def oracle_model(data_path, seed) -> OracleStats:
    """
    Instance OracleStats prête à l'emploi.
    scope="session" → construite une seule fois (calcul de distribution).
    """
    config = OracleStatsConfig(
        window_size=200,
        alpha=1.0,
        lambda_uniform=0.25,
        seed=seed,
    )
    return OracleStats(data_path, config)


@pytest.fixture(scope="function")
def smartgrid_model(seed) -> SmartGrid:
    """
    Instance SmartGrid fraîche pour chaque test.
    scope="function" → nouvelle instance à chaque test (seed fixe = reproductible).
    Réduit n_candidates pour la vitesse des tests (sauf tests @slow).
    """
    config = SmartGridConfig(
        n_candidates=10_000,   # Réduit pour vitesse des tests unitaires
        seed=seed,
    )
    return SmartGrid(config)


@pytest.fixture(scope="function")
def smartgrid_model_full(seed) -> SmartGrid:
    """
    SmartGrid avec 100k candidats — utilisé pour les tests de performance.
    """
    config = SmartGridConfig(
        n_candidates=100_000,
        seed=seed,
    )
    return SmartGrid(config)
