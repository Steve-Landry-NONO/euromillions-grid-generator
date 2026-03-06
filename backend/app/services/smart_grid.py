"""
SmartGrid v1 — Optimiseur anti-partage EuroMillions
=====================================================

COMMENT ÇA MARCHE (version simple) :
--------------------------------------
SmartGrid ne prédit PAS les numéros gagnants.
Son objectif est différent : générer des grilles "moins humaines".

Pourquoi ? Beaucoup de joueurs choisissent des numéros selon des
patterns prévisibles : leurs dates d'anniversaire (≤31), des suites
(1-2-3-4-5), des patterns symétriques, etc.

Si tu gagnes avec les mêmes numéros que d'autres, tu PARTAGES le jackpot.
SmartGrid essaie de te donner des grilles plus "originales" pour réduire
ce risque de partage — mais ne change PAS ta probabilité de gagner.

ALGORITHME :
1. Générer X candidats aléatoires (ex: 100 000 grilles).
2. Scorer chaque candidat avec des pénalités :
   - Trop de numéros ≤31 (dates de calendrier)
   - Numéros consécutifs (suites)
   - Pattern arithmétique régulier (1,4,7,10,13...)
   - Cluster trop serré (tous entre 20 et 25)
   - Somme hors plage raisonnable
   - Étoiles trop basses (≤7, très jouées)
3. Sélectionner les K meilleures grilles en garantissant
   qu'elles sont diversifiées entre elles.

DISCLAIMER : Ce score ne représente pas une probabilité de gagner.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
# Structures de données
# ─────────────────────────────────────────────

@dataclass
class SmartTicket:
    """Représente une grille optimisée par SmartGrid."""
    numbers: list[int]   # 5 numéros entre 1 et 50
    stars: list[int]     # 2 étoiles entre 1 et 12
    score: float = 0.0   # Score anti-partage (0=mauvais, 1=excellent)
    explain: dict = field(default_factory=dict)   # Détails du score
    diversity_relaxed: bool = False  # True si on a dû assouplir la diversité

    def __str__(self):
        nums = " ".join(f"{n:02d}" for n in self.numbers)
        strs = " ".join(f"{s:02d}" for s in self.stars)
        reasons = self._main_reasons()
        return (
            f"Numéros : {nums}  |  Étoiles : {strs}  |  "
            f"Score anti-partage : {self.score:.2f}  |  {reasons}"
        )

    def _main_reasons(self) -> str:
        """Retourne les 2-3 principales raisons du score en texte lisible."""
        reasons = []
        e = self.explain

        if e.get("penalty_dates", 0) < 0.1:
            reasons.append("Peu de numéros ≤31")
        if e.get("penalty_sequence", 0) < 0.05:
            reasons.append("Pas de suite")
        if e.get("penalty_cluster", 0) < 0.05:
            reasons.append("Bonne dispersion")
        if e.get("bonus_diversity", 0) > 0.05:
            reasons.append("Bien diversifiée")

        return " | ".join(reasons) if reasons else "Grille équilibrée"


@dataclass
class SmartGridConfig:
    """
    Paramètres du moteur SmartGrid.

    n_candidates    : nombre de grilles candidates à générer (défaut 100_000).
                      Plus c'est élevé, meilleure est la sélection,
                      mais plus c'est lent. 50_000–100_000 est un bon compromis.
    sum_range       : plage de somme acceptable des 5 numéros.
                      Défaut (100, 176) couvre environ 80% des tirages réels.
    avoid_numbers   : liste de numéros à ne pas inclure.
    avoid_stars     : liste d'étoiles à ne pas inclure.
    max_common      : nombre maximum de numéros communs entre 2 grilles.
                      Défaut 3. Plus c'est faible, plus les grilles diffèrent.
    seed            : graine aléatoire pour reproductibilité.
    penalty_weights : dictionnaire pour ajuster les poids des pénalités.
    """
    n_candidates: int = 100_000
    sum_range: tuple[int, int] = (100, 176)
    avoid_numbers: list[int] = field(default_factory=list)
    avoid_stars: list[int] = field(default_factory=list)
    max_common: int = 3
    seed: Optional[int] = None
    penalty_weights: dict = field(default_factory=lambda: {
        "dates":    0.30,   # pénalité numéros ≤ 31
        "sequence": 0.20,   # pénalité suites consécutives
        "arith":    0.25,   # pénalité pattern arithmétique
        "cluster":  0.20,   # pénalité cluster serré
        "sum":      0.20,   # pénalité somme hors plage
        "stars":    0.15,   # pénalité étoiles basses
        "diversity":0.15,   # bonus diversité (récompense)
    })


# ─────────────────────────────────────────────
# Fonctions de scoring (vectorisées)
# ─────────────────────────────────────────────
#
# Ces fonctions travaillent sur des matrices numpy pour traiter
# des milliers de candidats en une seule opération (vectorisation).
# candidates : matrice (N, 5) — N grilles de 5 numéros chacune

def _penalty_dates(candidates: np.ndarray) -> np.ndarray:
    """
    Pénalité pour les numéros de calendrier (≤ 31).
    Beaucoup de joueurs jouent leurs anniversaires, donc les numéros
    1..31 sont sur-représentés dans les combinaisons humaines.

    Retourne un score de pénalité entre 0 et 1 pour chaque candidat.
    """
    # count(n <= 31) / 5 : proportion de numéros "dates"
    return (candidates <= 31).sum(axis=1) / 5.0


def _penalty_sequence(candidates: np.ndarray) -> np.ndarray:
    """
    Pénalité pour les suites consécutives.
    Ex: [1,2,3,4,5] ou [10,11,20,21,22] sont très "humains".

    On pénalise les paires de numéros consécutifs (diff=1)
    et quasi-consécutifs (diff=2).
    """
    # On trie chaque ligne pour calculer les différences
    sorted_c = np.sort(candidates, axis=1)
    diffs = np.diff(sorted_c, axis=1)  # différences entre numéros adjacents

    # Pénalité : 0.20 par paire consécutive + 0.10 par paire quasi-consécutive
    penalty = (diffs == 1).sum(axis=1) * 0.20 + (diffs == 2).sum(axis=1) * 0.10
    return np.clip(penalty, 0, 1)


def _penalty_arithmetic(candidates: np.ndarray) -> np.ndarray:
    """
    Pénalité pour les patterns arithmétiques réguliers.
    Ex: [5,10,15,20,25] ou [3,13,23,33,43] — écart constant.

    On mesure la régularité des écarts entre numéros consécutifs.
    Si l'écart-type des différences est très faible → pattern régulier.
    """
    sorted_c = np.sort(candidates, axis=1)
    diffs = np.diff(sorted_c, axis=1)  # 4 différences pour 5 numéros

    # std faible = les écarts sont tous similaires = pattern arithmétique
    std_diffs = diffs.std(axis=1)
    # Seuil : si std < 2, on considère que c'est "trop régulier"
    return (std_diffs < 2.0).astype(float) * 0.25


def _penalty_cluster(candidates: np.ndarray) -> np.ndarray:
    """
    Pénalité pour les clusters serrés.
    Ex: [20,21,22,23,24] → tous les numéros sont dans une plage étroite.

    On mesure la "range" (max - min). Si elle est trop petite, on pénalise.
    """
    sorted_c = np.sort(candidates, axis=1)
    range_vals = sorted_c[:, -1] - sorted_c[:, 0]  # max - min

    # Plus la range est petite, plus la pénalité est forte
    # clamp((25 - range) / 25, 0, 1) * 0.20
    penalty = np.clip((25 - range_vals) / 25.0, 0, 1) * 0.20
    return penalty


def _penalty_sum(candidates: np.ndarray, sum_range: tuple[int, int]) -> np.ndarray:
    """
    Pénalité pour les sommes hors plage.
    Les tirages EuroMillions réels ont tendance à avoir une somme
    entre 100 et 176 environ. Les extrêmes sont moins courants.
    """
    sums = candidates.sum(axis=1)
    low, high = sum_range

    penalty = np.zeros(len(candidates))
    # En dessous de la plage : pénalité proportionnelle
    below_mask = sums < low
    penalty[below_mask] = np.clip((low - sums[below_mask]) / low, 0, 1) * 0.20
    # Au-dessus de la plage : idem
    above_mask = sums > high
    penalty[above_mask] = np.clip((sums[above_mask] - high) / (250 - high), 0, 1) * 0.20
    return penalty


def _penalty_stars(stars: np.ndarray) -> np.ndarray:
    """
    Pénalité pour les étoiles basses (≤ 7).
    Les étoiles 1..7 sont plus souvent jouées (anniversaires, etc.).
    """
    # proportion d'étoiles ≤ 7 * 0.15
    return (stars <= 7).sum(axis=1) / 2.0 * 0.15


def _bonus_diversity(
    candidates: np.ndarray,
    selected: list[np.ndarray]
) -> np.ndarray:
    """
    Bonus pour les grilles différentes des grilles déjà sélectionnées.
    Utilise la distance de Jaccard : plus les grilles ont de numéros
    en commun, plus le bonus est faible.

    Distance de Jaccard entre A et B = 1 - |A∩B| / |A∪B|
    (0=identiques, 1=aucun numéro commun)
    """
    if not selected:
        return np.zeros(len(candidates))

    selected_sets = [set(s.tolist()) for s in selected]
    bonuses = []

    for cand in candidates:
        cand_set = set(cand.tolist())
        # Calcul de la distance Jaccard moyenne vs les grilles déjà sélectionnées
        jaccard_distances = []
        for sel_set in selected_sets:
            intersection = len(cand_set & sel_set)
            union = len(cand_set | sel_set)
            jaccard_distances.append(1.0 - intersection / union if union > 0 else 1.0)
        bonuses.append(np.mean(jaccard_distances))

    return np.array(bonuses) * 0.15


# ─────────────────────────────────────────────
# Classe principale
# ─────────────────────────────────────────────

class SmartGrid:
    """
    SmartGrid v1 — Optimiseur anti-partage.

    Usage typique :
        sg = SmartGrid()
        tickets = sg.generate(n_tickets=5)
        for t in tickets:
            print(t)
    """

    NUM_RANGE = (1, 50)
    STAR_RANGE = (1, 12)
    NUM_COUNT = 5
    STAR_COUNT = 2

    def __init__(self, config: Optional[SmartGridConfig] = None):
        self.config = config or SmartGridConfig()
        self.rng = np.random.default_rng(self.config.seed)

    # ─────────────────────────────────────────
    # Génération de candidats
    # ─────────────────────────────────────────

    def _generate_candidates(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Génère X candidats aléatoires et filtre selon les contraintes.

        Retourne :
            num_candidates  : matrice (N, 5) de numéros valides
            star_candidates : matrice (N, 2) d'étoiles correspondantes
        """
        n = self.config.n_candidates
        avoid_nums = set(self.config.avoid_numbers)
        avoid_strs = set(self.config.avoid_stars)

        # Pools disponibles (en excluant les numéros à éviter)
        num_pool = np.array([i for i in range(1, 51) if i not in avoid_nums])
        star_pool = np.array([i for i in range(1, 13) if i not in avoid_strs])

        if len(num_pool) < self.NUM_COUNT:
            raise ValueError(
                f"Trop de numéros à éviter : il ne reste que {len(num_pool)} numéros disponibles."
            )
        if len(star_pool) < self.STAR_COUNT:
            raise ValueError(
                f"Trop d'étoiles à éviter : il ne reste que {len(star_pool)} étoiles disponibles."
            )

        # Génération vectorisée : on tire N grilles d'un coup
        # Trick numpy : on utilise argsort de random pour simuler
        # un tirage "sans remise" pour chaque ligne en une seule opération
        num_indices = np.argsort(
            self.rng.random((n, len(num_pool))), axis=1
        )[:, :self.NUM_COUNT]
        num_candidates = num_pool[num_indices]

        star_indices = np.argsort(
            self.rng.random((n, len(star_pool))), axis=1
        )[:, :self.STAR_COUNT]
        star_candidates = star_pool[star_indices]

        return num_candidates, star_candidates

    # ─────────────────────────────────────────
    # Scoring
    # ─────────────────────────────────────────

    def _score_candidates(
        self,
        num_candidates: np.ndarray,
        star_candidates: np.ndarray,
        selected_so_far: list[np.ndarray]
    ) -> tuple[np.ndarray, list[dict]]:
        """
        Calcule le score anti-partage pour chaque candidat.

        Score = 1 - sum(pénalités) + bonus_diversité
        Score est clampé entre 0 et 1.

        Retourne :
            scores      : tableau (N,) de scores
            explain_list: liste de dict avec le détail des pénalités
        """
        w = self.config.penalty_weights

        # Calcul de toutes les pénalités (vectorisé)
        p_dates   = _penalty_dates(num_candidates)    * w["dates"]
        p_seq     = _penalty_sequence(num_candidates) * w["sequence"]
        p_arith   = _penalty_arithmetic(num_candidates) * w["arith"]
        p_cluster = _penalty_cluster(num_candidates)  * w["cluster"]
        p_sum     = _penalty_sum(num_candidates, self.config.sum_range) * w["sum"]
        p_stars   = _penalty_stars(star_candidates)   # déjà pondéré

        # Bonus diversité (non vectorisé car dépend des sélections précédentes)
        b_div = _bonus_diversity(num_candidates, selected_so_far) * w["diversity"]

        total_penalty = np.clip(p_dates + p_seq + p_arith + p_cluster + p_sum + p_stars, 0, 1)
        scores = np.clip(1.0 - total_penalty + b_div, 0, 1)

        # On ne précalcule pas explain pour tous les candidats (trop coûteux)
        # On le fera uniquement pour les tickets sélectionnés
        return scores, {
            "p_dates": p_dates,
            "p_seq": p_seq,
            "p_arith": p_arith,
            "p_cluster": p_cluster,
            "p_sum": p_sum,
            "p_stars": p_stars,
            "b_div": b_div,
        }

    def _build_explain(self, idx: int, penalty_arrays: dict) -> dict:
        """Construit le dictionnaire d'explication pour un ticket donné."""
        return {
            "penalty_dates":    round(float(penalty_arrays["p_dates"][idx]), 3),
            "penalty_sequence": round(float(penalty_arrays["p_seq"][idx]), 3),
            "penalty_arith":    round(float(penalty_arrays["p_arith"][idx]), 3),
            "penalty_cluster":  round(float(penalty_arrays["p_cluster"][idx]), 3),
            "penalty_sum":      round(float(penalty_arrays["p_sum"][idx]), 3),
            "penalty_stars":    round(float(penalty_arrays["p_stars"][idx]), 3),
            "bonus_diversity":  round(float(penalty_arrays["b_div"][idx]), 3),
        }

    # ─────────────────────────────────────────
    # Sélection avec contrainte de diversité
    # ─────────────────────────────────────────

    def _select_diverse_top_k(
        self,
        num_candidates: np.ndarray,
        star_candidates: np.ndarray,
        scores: np.ndarray,
        penalty_arrays: dict,
        k: int,
    ) -> list[SmartTicket]:
        """
        Sélectionne les K meilleurs tickets en garantissant la diversité.

        Algorithme glouton :
        1. Trier les candidats par score décroissant.
        2. Sélectionner le meilleur.
        3. Pour chaque candidat suivant : l'accepter seulement si
           il ne partage pas trop de numéros avec les déjà sélectionnés.
        4. Si impossible, assouplir la contrainte progressivement.
        """
        # Tri par score décroissant
        order = np.argsort(scores)[::-1]

        selected_tickets: list[SmartTicket] = []
        selected_num_arrays: list[np.ndarray] = []
        max_common = self.config.max_common
        diversity_relaxed = False

        for idx in order:
            nums = num_candidates[idx]
            strs = star_candidates[idx]
            num_set = set(nums.tolist())

            # Vérifier la diversité vs les tickets déjà sélectionnés
            too_similar = False
            for sel_nums in selected_num_arrays:
                common = len(num_set & set(sel_nums.tolist()))
                if common > max_common:
                    too_similar = True
                    break

            if not too_similar:
                ticket = SmartTicket(
                    numbers=sorted(nums.tolist()),
                    stars=sorted(strs.tolist()),
                    score=round(float(scores[idx]), 3),
                    explain=self._build_explain(idx, penalty_arrays),
                    diversity_relaxed=diversity_relaxed,
                )
                selected_tickets.append(ticket)
                selected_num_arrays.append(nums)

            if len(selected_tickets) == k:
                break

            # Si on a parcouru 30% des candidats sans trouver K tickets,
            # on assouplit la contrainte de diversité
            current_position = np.where(order == idx)[0][0]
            if current_position > len(order) * 0.3 and len(selected_tickets) < k:
                max_common = min(max_common + 1, 4)
                diversity_relaxed = True

        # Si on n'a pas pu sélectionner K tickets même en assouplissant :
        # fallback — prendre les meilleurs sans contrainte de diversité
        if len(selected_tickets) < k:
            remaining_needed = k - len(selected_tickets)
            already_selected_indices = {
                i for i, idx in enumerate(order)
                if any(
                    np.array_equal(num_candidates[idx], sel)
                    for sel in selected_num_arrays
                )
            }
            for idx in order:
                if remaining_needed == 0:
                    break
                nums = num_candidates[idx]
                if not any(np.array_equal(nums, sel) for sel in selected_num_arrays):
                    ticket = SmartTicket(
                        numbers=sorted(nums.tolist()),
                        stars=sorted(star_candidates[idx].tolist()),
                        score=round(float(scores[idx]), 3),
                        explain=self._build_explain(idx, penalty_arrays),
                        diversity_relaxed=True,
                    )
                    selected_tickets.append(ticket)
                    selected_num_arrays.append(nums)
                    remaining_needed -= 1

        return selected_tickets

    # ─────────────────────────────────────────
    # Point d'entrée public
    # ─────────────────────────────────────────

    def generate(self, n_tickets: int = 1) -> list[SmartTicket]:
        """
        Génère n_tickets grilles optimisées par SmartGrid.

        Args:
            n_tickets : nombre de grilles à générer (1, 5 ou 10).

        Returns:
            Liste de SmartTicket triés par score décroissant.
        """
        if n_tickets not in {1, 5, 10}:
            raise ValueError(f"n_tickets doit être 1, 5 ou 10 (reçu : {n_tickets})")

        # 1. Générer les candidats
        num_candidates, star_candidates = self._generate_candidates()

        # 2. Premier scoring sans diversité (pas de tickets sélectionnés encore)
        scores, penalty_arrays = self._score_candidates(
            num_candidates, star_candidates, selected_so_far=[]
        )

        # 3. Sélection avec contrainte de diversité
        tickets = self._select_diverse_top_k(
            num_candidates, star_candidates, scores, penalty_arrays, k=n_tickets
        )

        return tickets
