"""
OracleStats v1 — Modèle probabiliste EuroMillions
==================================================

COMMENT ÇA MARCHE (version simple) :
--------------------------------------
1. On lit l'historique des tirages (CSV).
2. On compte combien de fois chaque numéro est apparu
   dans les N derniers tirages → c'est la "fréquence".
3. On "lisse" ces fréquences pour éviter de trop faire
   confiance aux numéros très fréquents (lissage de Laplace).
4. On mélange un peu avec une distribution uniforme
   (tous les numéros ont la même chance) pour rester
   "honnête" statistiquement.
5. On tire aléatoirement 5 numéros + 2 étoiles selon
   ces probabilités, SANS remise (sans doublons).

DISCLAIMER : Cela ne prédit pas les numéros gagnants.
EuroMillions est un jeu de hasard indépendant.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
# Structures de données
# ─────────────────────────────────────────────

@dataclass
class Ticket:
    """Représente une grille EuroMillions générée."""
    numbers: list[int]   # 5 numéros entre 1 et 50
    stars: list[int]     # 2 étoiles entre 1 et 12
    explanation: str = ""
    top_numbers: list[tuple] = field(default_factory=list)  # (numéro, poids)
    top_stars: list[tuple] = field(default_factory=list)    # (étoile, poids)

    def __str__(self):
        nums = " ".join(f"{n:02d}" for n in self.numbers)
        strs = " ".join(f"{s:02d}" for s in self.stars)
        return f"Numéros : {nums}  |  Étoiles : {strs}"


@dataclass
class OracleStatsConfig:
    """
    Paramètres du modèle OracleStats.

    window_size      : nombre de tirages récents à analyser (défaut 200).
                       Ex: 200 = on regarde les 200 derniers tirages.
    alpha            : force du lissage de Laplace (défaut 1.0).
                       Plus alpha est grand, plus on se rapproche de l'uniforme.
    lambda_uniform   : proportion d'uniforme mélangée (défaut 0.25).
                       0.0 = 100% historique, 1.0 = 100% hasard pur.
    seed             : graine aléatoire pour reproductibilité (optionnel).
    top_k_display    : combien de numéros "chauds" afficher (défaut 10).
    """
    window_size: int = 200
    alpha: float = 1.0
    lambda_uniform: float = 0.25
    seed: Optional[int] = None
    top_k_display: int = 10


# ─────────────────────────────────────────────
# Classe principale
# ─────────────────────────────────────────────

class OracleStats:
    """
    Modèle OracleStats v1.

    Usage typique :
        model = OracleStats("euromillions_history.csv")
        tickets = model.generate(n_tickets=5)
        for t in tickets:
            print(t)
    """

    # Règles EuroMillions
    NUM_RANGE = (1, 50)   # numéros de 1 à 50
    STAR_RANGE = (1, 12)  # étoiles de 1 à 12
    NUM_COUNT = 5         # 5 numéros par grille
    STAR_COUNT = 2        # 2 étoiles par grille

    def __init__(self, csv_path: str | Path, config: Optional[OracleStatsConfig] = None):
        """
        Initialise le modèle.

        Args:
            csv_path : chemin vers le fichier CSV historique.
            config   : paramètres du modèle (optionnel, valeurs par défaut sinon).
        """
        self.config = config or OracleStatsConfig()
        self.rng = np.random.default_rng(self.config.seed)

        # Chargement et validation du dataset
        self._df = self._load_dataset(csv_path)

        # Calcul des distributions de probabilités
        self._prob_numbers, self._prob_stars = self._compute_distributions()

    # ─────────────────────────────────────────
    # Chargement des données
    # ─────────────────────────────────────────

    def _load_dataset(self, csv_path: str | Path) -> pd.DataFrame:
        """
        Charge et valide le CSV historique.

        Format attendu : date,n1,n2,n3,n4,n5,s1,s2
        Exemple ligne  : 2025-12-30,4,17,25,36,44,3,11
        """
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset introuvable : {path}")

        df = pd.read_csv(path, parse_dates=["date"])

        # Vérification des colonnes obligatoires
        required = {"date", "n1", "n2", "n3", "n4", "n5", "s1", "s2"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Colonnes manquantes dans le CSV : {missing}")

        # Vérification des valeurs nulles
        if df[list(required)].isnull().any().any():
            raise ValueError("Le dataset contient des valeurs manquantes.")

        # Tri chronologique (le plus récent en dernier)
        df = df.sort_values("date").reset_index(drop=True)

        print(f"[OracleStats] Dataset chargé : {len(df)} tirages "
              f"(du {df['date'].min().date()} au {df['date'].max().date()})")
        return df

    # ─────────────────────────────────────────
    # Calcul des distributions
    # ─────────────────────────────────────────

    def _compute_distributions(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Calcule les probabilités pour chaque numéro (1..50) et étoile (1..12).

        Étapes :
        1. Prendre les N derniers tirages (fenêtre glissante).
        2. Compter les fréquences de chaque numéro/étoile.
        3. Appliquer le lissage de Laplace.
        4. Mélanger avec une distribution uniforme.

        Retourne :
            prob_numbers : tableau de 50 probabilités (index 0 = numéro 1)
            prob_stars   : tableau de 12 probabilités (index 0 = étoile 1)
        """
        # Étape 1 : fenêtre glissante
        window = self.config.window_size
        df_window = self._df.tail(window)
        n_draws = len(df_window)

        # Étape 2 : compter les occurrences
        #   Pour les numéros : on "empile" les 5 colonnes n1..n5
        num_cols = ["n1", "n2", "n3", "n4", "n5"]
        star_cols = ["s1", "s2"]

        num_values = df_window[num_cols].values.flatten()   # tous les numéros tirés
        star_values = df_window[star_cols].values.flatten() # toutes les étoiles tirées

        # Fréquences brutes (tableau indexé 0..49 pour les numéros 1..50)
        freq_num = np.zeros(50)
        for v in num_values:
            freq_num[int(v) - 1] += 1  # -1 car index Python commence à 0

        freq_star = np.zeros(12)
        for v in star_values:
            freq_star[int(v) - 1] += 1

        # Étape 3 : lissage de Laplace
        #   Formule : p_i = (freq_i + alpha) / (total + alpha * nb_valeurs)
        #   alpha=1 → on ajoute 1 "tirage fictif" pour chaque numéro.
        #   Effet : les numéros jamais apparus ont quand même une petite probabilité.
        alpha = self.config.alpha

        total_num = freq_num.sum() + alpha * 50
        prob_num_raw = (freq_num + alpha) / total_num

        total_star = freq_star.sum() + alpha * 12
        prob_star_raw = (freq_star + alpha) / total_star

        # Étape 4 : mélange avec l'uniforme
        #   lambda=0.25 → 75% historique + 25% hasard pur
        lam = self.config.lambda_uniform
        uniform_num = np.ones(50) / 50
        uniform_star = np.ones(12) / 12

        prob_num = (1 - lam) * prob_num_raw + lam * uniform_num
        prob_star = (1 - lam) * prob_star_raw + lam * uniform_star

        # Normalisation finale (pour être sûr que ça somme à 1.0)
        prob_num /= prob_num.sum()
        prob_star /= prob_star.sum()

        return prob_num, prob_star

    # ─────────────────────────────────────────
    # Génération de tickets
    # ─────────────────────────────────────────

    def _sample_ticket(self) -> Ticket:
        """
        Génère un ticket EuroMillions par échantillonnage pondéré sans remise.

        "Sans remise" = une fois qu'un numéro est tiré, il ne peut pas
        être tiré une deuxième fois dans la même grille.
        """
        # np.random.choice avec replace=False = sans remise
        numbers_0indexed = self.rng.choice(
            50,
            size=self.NUM_COUNT,
            replace=False,
            p=self._prob_numbers
        )
        stars_0indexed = self.rng.choice(
            12,
            size=self.STAR_COUNT,
            replace=False,
            p=self._prob_stars
        )

        # Conversion index → valeur réelle (0-indexed → 1-indexed)
        numbers = sorted((numbers_0indexed + 1).tolist())
        stars = sorted((stars_0indexed + 1).tolist())

        return Ticket(numbers=numbers, stars=stars)

    def generate(self, n_tickets: int = 1) -> list[Ticket]:
        """
        Génère n_tickets grilles EuroMillions.

        Args:
            n_tickets : nombre de grilles à générer (1, 5 ou 10 recommandés).

        Returns:
            Liste de Ticket avec numéros, étoiles et explication.
        """
        if n_tickets not in {1, 5, 10}:
            raise ValueError(f"n_tickets doit être 1, 5 ou 10 (reçu : {n_tickets})")

        tickets = [self._sample_ticket() for _ in range(n_tickets)]

        # Ajout des explications et du top des numéros pondérés
        top_nums = self._get_top_weighted(self._prob_numbers, k=self.config.top_k_display)
        top_strs = self._get_top_weighted(self._prob_stars, k=5)

        explanation = (
            f"Grille générée par OracleStats v1 — "
            f"Basé sur les {self.config.window_size} derniers tirages, "
            f"lissage α={self.config.alpha}, mélange uniforme λ={self.config.lambda_uniform}. "
            f"Approche expérimentale : aucune garantie de gain. "
            f"EuroMillions reste un jeu de hasard indépendant."
        )

        for ticket in tickets:
            ticket.explanation = explanation
            ticket.top_numbers = top_nums
            ticket.top_stars = top_strs

        return tickets

    # ─────────────────────────────────────────
    # Utilitaires
    # ─────────────────────────────────────────

    def _get_top_weighted(self, probs: np.ndarray, k: int) -> list[tuple[int, float]]:
        """
        Retourne les k valeurs avec les plus hautes probabilités.

        Retourne : [(valeur_1indexed, probabilité_arrondie), ...]
        """
        indices_sorted = np.argsort(probs)[::-1][:k]
        return [(int(i) + 1, round(float(probs[i]), 4)) for i in indices_sorted]

    def get_distribution_summary(self) -> dict:
        """
        Retourne un résumé des distributions calculées.
        Utile pour l'affichage "top 10" dans l'UI.
        """
        return {
            "top_numbers": self._get_top_weighted(self._prob_numbers, 10),
            "top_stars": self._get_top_weighted(self._prob_stars, 5),
            "window_used": min(self.config.window_size, len(self._df)),
            "total_draws_in_dataset": len(self._df),
        }
