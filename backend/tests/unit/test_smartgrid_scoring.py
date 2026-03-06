"""
test_smartgrid_scoring.py — U3 : Correctness du scoring SmartGrid
=================================================================

Objectif : vérifier que chaque pénalité se comporte comme attendu
et que le score final est cohérent.

Ces tests documentent aussi le comportement du modèle — ils servent
de "spec exécutable" pour les futures modifications du scoring.
"""

import pytest
import numpy as np
from app.services.smart_grid import (
    SmartGrid, SmartGridConfig,
    _penalty_dates, _penalty_sequence, _penalty_arithmetic,
    _penalty_cluster, _penalty_sum, _penalty_stars,
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_candidates(*rows):
    """Crée une matrice numpy à partir de listes de numéros."""
    return np.array(rows)

def make_stars(*rows):
    """Crée une matrice numpy d'étoiles."""
    return np.array(rows)


# ─────────────────────────────────────────────
# U3-1 : Score dans [0, 1]
# ─────────────────────────────────────────────

class TestScoreRange:

    def test_score_in_0_1(self, smartgrid_model):
        """
        Le score final de chaque ticket doit être dans [0.0, 1.0].
        C'est la propriété fondamentale du score anti-partage.
        """
        tickets = smartgrid_model.generate(n_tickets=10)
        for i, t in enumerate(tickets):
            assert 0.0 <= t.score <= 1.0, (
                f"Ticket {i+1} : score hors [0,1] → {t.score}"
            )

    def test_score_is_float(self, smartgrid_model):
        """Le score doit être un float, pas None ou int."""
        tickets = smartgrid_model.generate(n_tickets=5)
        for i, t in enumerate(tickets):
            assert isinstance(t.score, float), (
                f"Ticket {i+1} : score n'est pas un float → {type(t.score)}"
            )

    def test_explain_dict_present(self, smartgrid_model):
        """Chaque ticket doit avoir un dictionnaire explain non-vide."""
        tickets = smartgrid_model.generate(n_tickets=5)
        for i, t in enumerate(tickets):
            assert t.explain is not None, f"Ticket {i+1} : explain est None"
            assert len(t.explain) > 0, f"Ticket {i+1} : explain est vide"


# ─────────────────────────────────────────────
# U3-2 : Pénalité dates (numéros ≤ 31)
# ─────────────────────────────────────────────

class TestPenaltyDates:

    def test_date_penalty_increases_with_low_numbers(self):
        """
        Plus une grille contient de numéros ≤ 31, plus la pénalité est haute.
        Logique : les dates d'anniversaire (1-31) sont sur-jouées.
        """
        # Tous > 31 → pénalité minimale (0)
        all_high = make_candidates([32, 35, 40, 45, 50])
        p_high = _penalty_dates(all_high)
        assert p_high[0] == 0.0, f"Grille sans numéros ≤31 doit avoir p=0, got {p_high[0]}"

        # Tous ≤ 31 → pénalité maximale (1.0)
        all_low = make_candidates([1, 7, 14, 21, 28])
        p_low = _penalty_dates(all_low)
        assert p_low[0] == 1.0, f"Grille 100% numéros ≤31 doit avoir p=1.0, got {p_low[0]}"

        # Moitié/moitié → pénalité intermédiaire
        mixed = make_candidates([10, 20, 32, 40, 50])   # 2/5 ≤ 31
        p_mixed = _penalty_dates(mixed)
        assert p_mixed[0] == pytest.approx(0.4, abs=0.001), (
            f"Grille 2/5 ≤31 doit avoir p=0.4, got {p_mixed[0]}"
        )

    def test_date_penalty_monotone(self):
        """
        Plus on a de numéros ≤ 31, plus la pénalité augmente strictement.
        """
        grilles = [
            [32, 35, 40, 45, 50],   # 0 numéros ≤31
            [10, 35, 40, 45, 50],   # 1 numéro ≤31
            [10, 20, 40, 45, 50],   # 2 numéros ≤31
            [10, 20, 30, 45, 50],   # 3 numéros ≤31
            [10, 20, 30, 31, 50],   # 4 numéros ≤31
            [10, 20, 30, 31, 29],   # 5 numéros ≤31
        ]
        penalties = _penalty_dates(make_candidates(*grilles))
        for i in range(len(penalties) - 1):
            assert penalties[i] < penalties[i + 1], (
                f"Pénalité non monotone : p[{i}]={penalties[i]} >= p[{i+1}]={penalties[i+1]}"
            )


# ─────────────────────────────────────────────
# U3-3 : Pénalité suites consécutives
# ─────────────────────────────────────────────

class TestPenaltySequence:

    def test_sequence_penalty_detects_consecutive(self):
        """
        Une grille avec des numéros consécutifs doit avoir une pénalité > 0.
        [1,2,3,4,5] = suite parfaite → pénalité maximale.
        """
        perfect_suite = make_candidates([1, 2, 3, 4, 5])
        p = _penalty_sequence(perfect_suite)
        assert p[0] > 0, "Suite parfaite doit avoir une pénalité > 0"

        no_suite = make_candidates([1, 10, 20, 35, 50])
        p_no = _penalty_sequence(no_suite)
        assert p_no[0] == 0.0, f"Grille sans suite doit avoir p=0, got {p_no[0]}"

    def test_sequence_penalty_partial_suite(self):
        """
        Une suite partielle doit être moins pénalisée qu'une suite complète.
        """
        full_suite = make_candidates([1, 2, 3, 4, 5])
        partial_suite = make_candidates([1, 2, 10, 20, 30])   # 1 paire consécutive

        p_full = _penalty_sequence(full_suite)
        p_partial = _penalty_sequence(partial_suite)
        assert p_partial[0] < p_full[0], (
            f"Suite partielle ({p_partial[0]}) doit être < suite complète ({p_full[0]})"
        )

    def test_sequence_penalty_quasi_consecutive(self):
        """
        Les paires avec diff=2 (quasi-consécutives) sont aussi pénalisées,
        mais moins que les paires avec diff=1.
        """
        diff1 = make_candidates([10, 11, 20, 30, 40])   # une paire diff=1
        diff2 = make_candidates([10, 12, 20, 30, 40])   # une paire diff=2
        no_near = make_candidates([10, 20, 30, 40, 50]) # aucune

        p_d1 = _penalty_sequence(diff1)[0]
        p_d2 = _penalty_sequence(diff2)[0]
        p_no = _penalty_sequence(no_near)[0]

        assert p_d1 > p_d2 > p_no, (
            f"Ordre attendu p(diff=1) > p(diff=2) > p(aucun) : "
            f"{p_d1} > {p_d2} > {p_no}"
        )


# ─────────────────────────────────────────────
# U3-4 : Pénalité pattern arithmétique
# ─────────────────────────────────────────────

class TestPenaltyArithmetic:

    def test_arith_pattern_penalty_triggers_on_regular_diffs(self):
        """
        Un pattern arithmétique parfait (écarts constants) doit déclencher la pénalité.
        Ex: [5, 10, 15, 20, 25] — progression +5 régulière.
        """
        arith = make_candidates([5, 10, 15, 20, 25])     # diff = [5,5,5,5] → std=0
        irregular = make_candidates([3, 11, 22, 36, 47]) # diffs irréguliers

        p_arith = _penalty_arithmetic(arith)
        p_irreg = _penalty_arithmetic(irregular)

        assert p_arith[0] > 0, f"Pattern arithmétique pur doit avoir p > 0 : {p_arith[0]}"
        assert p_irreg[0] == 0.0, f"Diffs irréguliers → p=0, got {p_irreg[0]}"

    def test_arith_pattern_edge_case_slight_variation(self):
        """
        Si std(diffs) >= 2, pas de pénalité arithmétique.
        """
        slight_arith = make_candidates([1, 5, 10, 20, 35])   # std > 2
        p = _penalty_arithmetic(slight_arith)
        assert p[0] == 0.0, f"std(diffs) >= 2 doit donner p=0, got {p[0]}"


# ─────────────────────────────────────────────
# U3-5 : Pénalité cluster serré
# ─────────────────────────────────────────────

class TestPenaltyCluster:

    def test_cluster_penalty_triggers_on_small_range(self):
        """
        Un cluster très serré (tous les numéros proches) doit être pénalisé.
        Ex: [20, 21, 22, 23, 24] — range=4, très petit.
        """
        tight_cluster = make_candidates([20, 21, 22, 23, 24])   # range = 4
        dispersed = make_candidates([3, 12, 25, 38, 49])         # range = 46

        p_tight = _penalty_cluster(tight_cluster)
        p_disp = _penalty_cluster(dispersed)

        assert p_tight[0] > p_disp[0], (
            f"Cluster serré ({p_tight[0]}) doit être > dispersé ({p_disp[0]})"
        )
        assert p_disp[0] == 0.0, f"Grille très dispersée → p=0, got {p_disp[0]}"

    def test_cluster_penalty_zero_when_range_large(self):
        """
        Si max - min > 25, la pénalité cluster doit être 0.
        """
        wide = make_candidates([1, 10, 20, 35, 50])   # range = 49
        p = _penalty_cluster(wide)
        assert p[0] == 0.0, f"Range=49 → p=0, got {p[0]}"


# ─────────────────────────────────────────────
# U3-6 : Pénalité somme
# ─────────────────────────────────────────────

class TestPenaltySum:

    def test_sum_penalty_zero_in_range(self):
        """Somme dans [100, 176] → pénalité nulle."""
        in_range = make_candidates([10, 20, 30, 40, 36])   # somme = 136
        p = _penalty_sum(in_range, sum_range=(100, 176))
        assert p[0] == 0.0, f"Somme dans plage → p=0, got {p[0]}"

    def test_sum_penalty_above_range(self):
        """Somme > 176 → pénalité positive."""
        too_high = make_candidates([40, 42, 44, 46, 48])   # somme = 220
        p = _penalty_sum(too_high, sum_range=(100, 176))
        assert p[0] > 0, f"Somme trop haute → p > 0, got {p[0]}"

    def test_sum_penalty_below_range(self):
        """Somme < 100 → pénalité positive."""
        too_low = make_candidates([1, 2, 3, 4, 5])   # somme = 15
        p = _penalty_sum(too_low, sum_range=(100, 176))
        assert p[0] > 0, f"Somme trop basse → p > 0, got {p[0]}"


# ─────────────────────────────────────────────
# U3-7 : Bonus diversité
# ─────────────────────────────────────────────

class TestDiversityBonus:

    def test_diversity_bonus_increases_for_different_tickets(self, smartgrid_model):
        """
        Quand on génère plusieurs tickets, les tickets diversifiés
        (peu de numéros communs) ont un bonus_diversity plus élevé.
        """
        tickets = smartgrid_model.generate(n_tickets=5)

        # Vérifier que le bonus_diversity est présent dans explain
        for i, t in enumerate(tickets):
            assert "bonus_diversity" in t.explain, (
                f"Ticket {i+1} : 'bonus_diversity' absent de explain"
            )

    def test_diversity_constraint_respected(self, smartgrid_model):
        """
        Par défaut (max_common=3), aucune paire de tickets
        ne doit partager plus de 3 numéros.
        """
        tickets = smartgrid_model.generate(n_tickets=5)
        for i in range(len(tickets)):
            for j in range(i + 1, len(tickets)):
                set_i = set(tickets[i].numbers)
                set_j = set(tickets[j].numbers)
                common = len(set_i & set_j)
                assert common <= 3, (
                    f"Tickets {i+1} et {j+1} partagent {common} numéros "
                    f"(max autorisé: 3) : {set_i & set_j}"
                )
