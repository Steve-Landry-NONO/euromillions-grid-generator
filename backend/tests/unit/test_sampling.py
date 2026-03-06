"""
test_sampling.py — U2 : Sampling sans doublons (OracleStats + SmartGrid)
=========================================================================

Objectif : garantir que les grilles générées respectent les règles
EuroMillions fondamentales (R6 du Risk Register).

Couvre :
  ✓ 5 numéros uniques [1..50]
  ✓ 2 étoiles uniques [1..12]
  ✓ Respect des listes "avoid"
  ✓ Reproductibilité avec seed
  ✓ Robustesse sur N générations consécutives
"""

import pytest
import numpy as np
from app.services.oracle_stats import OracleStats, OracleStatsConfig
from app.services.smart_grid import SmartGrid, SmartGridConfig


# ─────────────────────────────────────────────
# Helpers de validation
# ─────────────────────────────────────────────

def assert_valid_ticket_numbers(numbers, context=""):
    """Vérifie les règles EuroMillions pour les numéros."""
    assert len(numbers) == 5, f"{context} : attendu 5 numéros, obtenu {len(numbers)}"
    assert len(set(numbers)) == 5, f"{context} : numéros non-uniques → {numbers}"
    assert all(1 <= n <= 50 for n in numbers), (
        f"{context} : numéro hors plage [1..50] → {[n for n in numbers if not 1 <= n <= 50]}"
    )

def assert_valid_ticket_stars(stars, context=""):
    """Vérifie les règles EuroMillions pour les étoiles."""
    assert len(stars) == 2, f"{context} : attendu 2 étoiles, obtenu {len(stars)}"
    assert len(set(stars)) == 2, f"{context} : étoiles non-uniques → {stars}"
    assert all(1 <= s <= 12 for s in stars), (
        f"{context} : étoile hors plage [1..12] → {[s for s in stars if not 1 <= s <= 12]}"
    )


# ─────────────────────────────────────────────
# U2 — OracleStats
# ─────────────────────────────────────────────

class TestOracleStatsSampling:

    def test_oraclestats_sampling_numbers_unique(self, oracle_model):
        """Les 5 numéros de chaque ticket OracleStats sont tous distincts."""
        tickets = oracle_model.generate(n_tickets=10)
        for i, t in enumerate(tickets):
            assert_valid_ticket_numbers(t.numbers, f"OracleStats ticket {i+1}")

    def test_oraclestats_sampling_stars_unique(self, oracle_model):
        """Les 2 étoiles de chaque ticket OracleStats sont distinctes."""
        tickets = oracle_model.generate(n_tickets=10)
        for i, t in enumerate(tickets):
            assert_valid_ticket_stars(t.stars, f"OracleStats ticket {i+1}")

    def test_sampling_respects_ranges(self, oracle_model):
        """Tous les numéros et étoiles sont dans les plages EuroMillions."""
        tickets = oracle_model.generate(n_tickets=10)
        for i, t in enumerate(tickets):
            assert_valid_ticket_numbers(t.numbers, f"Ticket {i+1}")
            assert_valid_ticket_stars(t.stars, f"Ticket {i+1}")

    def test_oraclestats_reproducible_with_seed(self, data_path):
        """
        Avec le même seed, OracleStats doit générer exactement les mêmes tickets.
        Critique pour la traçabilité et les tests de régression.
        """
        config = OracleStatsConfig(seed=123, window_size=100)
        model_a = OracleStats(data_path, config)
        model_b = OracleStats(data_path, config)

        tickets_a = model_a.generate(n_tickets=5)
        tickets_b = model_b.generate(n_tickets=5)

        for i, (ta, tb) in enumerate(zip(tickets_a, tickets_b)):
            assert ta.numbers == tb.numbers, (
                f"Ticket {i+1} non reproductible : {ta.numbers} != {tb.numbers}"
            )
            assert ta.stars == tb.stars, (
                f"Étoiles ticket {i+1} non reproductibles : {ta.stars} != {tb.stars}"
            )

    def test_oraclestats_robustness_100_generations(self, oracle_model):
        """
        Stress test : génère 100 tickets consécutifs et vérifie
        qu'aucun n'est invalide. Détecte les bugs de sampling rare.
        """
        # Générer 10 lots de 10 tickets
        all_tickets = []
        for _ in range(10):
            all_tickets.extend(oracle_model.generate(n_tickets=10))

        for i, t in enumerate(all_tickets):
            assert_valid_ticket_numbers(t.numbers, f"Stress ticket {i+1}")
            assert_valid_ticket_stars(t.stars, f"Stress ticket {i+1}")

    def test_oraclestats_distribution_sums_to_one(self, oracle_model):
        """
        Les distributions de probabilités doivent sommer à 1.0
        (condition nécessaire pour un sampling valide).
        """
        import numpy as np
        prob_num = oracle_model._prob_numbers
        prob_star = oracle_model._prob_stars

        assert abs(prob_num.sum() - 1.0) < 1e-9, (
            f"Distribution numéros ne somme pas à 1 : {prob_num.sum()}"
        )
        assert abs(prob_star.sum() - 1.0) < 1e-9, (
            f"Distribution étoiles ne somme pas à 1 : {prob_star.sum()}"
        )

    def test_oraclestats_all_values_positive(self, oracle_model):
        """
        Grâce au lissage de Laplace, toutes les probabilités
        doivent être strictement positives (aucun numéro à p=0).
        """
        assert (oracle_model._prob_numbers > 0).all(), (
            "Certains numéros ont une probabilité nulle (lissage insuffisant)."
        )
        assert (oracle_model._prob_stars > 0).all(), (
            "Certaines étoiles ont une probabilité nulle (lissage insuffisant)."
        )


# ─────────────────────────────────────────────
# U2 — SmartGrid
# ─────────────────────────────────────────────

class TestSmartGridSampling:

    def test_smartgrid_sampling_numbers_unique(self, smartgrid_model):
        """Les 5 numéros de chaque ticket SmartGrid sont tous distincts."""
        tickets = smartgrid_model.generate(n_tickets=5)
        for i, t in enumerate(tickets):
            assert_valid_ticket_numbers(t.numbers, f"SmartGrid ticket {i+1}")

    def test_smartgrid_sampling_stars_unique(self, smartgrid_model):
        """Les 2 étoiles de chaque ticket SmartGrid sont distinctes."""
        tickets = smartgrid_model.generate(n_tickets=5)
        for i, t in enumerate(tickets):
            assert_valid_ticket_stars(t.stars, f"SmartGrid ticket {i+1}")

    def test_sampling_respects_avoid_numbers(self, seed):
        """
        Les numéros dans avoid_numbers ne doivent jamais apparaître
        dans les tickets générés.
        """
        avoid = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        config = SmartGridConfig(
            n_candidates=5_000,
            avoid_numbers=avoid,
            seed=seed,
        )
        sg = SmartGrid(config)
        tickets = sg.generate(n_tickets=5)

        for i, t in enumerate(tickets):
            forbidden_present = [n for n in t.numbers if n in avoid]
            assert len(forbidden_present) == 0, (
                f"Ticket {i+1} contient des numéros interdits : {forbidden_present}"
            )

    def test_sampling_respects_avoid_stars(self, seed):
        """
        Les étoiles dans avoid_stars ne doivent jamais apparaître
        dans les tickets générés.
        """
        avoid_stars = [1, 2, 3]
        config = SmartGridConfig(
            n_candidates=5_000,
            avoid_stars=avoid_stars,
            seed=seed,
        )
        sg = SmartGrid(config)
        tickets = sg.generate(n_tickets=5)

        for i, t in enumerate(tickets):
            forbidden_present = [s for s in t.stars if s in avoid_stars]
            assert len(forbidden_present) == 0, (
                f"Ticket {i+1} contient des étoiles interdites : {forbidden_present}"
            )

    def test_smartgrid_raises_on_too_many_avoid_numbers(self, seed):
        """
        Si avoid_numbers vide le pool (< 5 numéros disponibles),
        SmartGrid doit lever une ValueError claire.
        """
        config = SmartGridConfig(
            n_candidates=1_000,
            avoid_numbers=list(range(1, 48)),   # ne laisse que 3 numéros (48,49,50)
            seed=seed,
        )
        sg = SmartGrid(config)
        with pytest.raises(ValueError, match="Trop de numéros à éviter"):
            sg.generate(n_tickets=1)

    def test_smartgrid_reproducible_with_seed(self, seed):
        """Avec le même seed, SmartGrid génère exactement les mêmes tickets."""
        config = SmartGridConfig(n_candidates=5_000, seed=seed)
        tickets_a = SmartGrid(config).generate(n_tickets=5)
        tickets_b = SmartGrid(config).generate(n_tickets=5)

        for i, (ta, tb) in enumerate(zip(tickets_a, tickets_b)):
            assert ta.numbers == tb.numbers, (
                f"SmartGrid ticket {i+1} non reproductible : {ta.numbers} != {tb.numbers}"
            )
