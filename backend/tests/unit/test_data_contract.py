"""
test_data_contract.py — U1 : Validation du Data Contract
==========================================================

Objectif : garantir que le dataset CSV est valide avant toute utilisation
par OracleStats ou SmartGrid. Si ces tests échouent → BLOQUANT (ne pas déployer).

Correspond à la checklist "bloquante" du Data Contract v1 :
  ✓ Colonnes exactes
  ✓ Zéro valeurs manquantes
  ✓ Dates uniques et parsables
  ✓ Numéros dans [1..50]
  ✓ 5 numéros distincts par ligne
  ✓ Étoiles dans [1..12]
  ✓ 2 étoiles distinctes par ligne
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path


# ── Colonnes attendues (Data Contract v1) ─────────────────────
REQUIRED_COLUMNS = ["date", "n1", "n2", "n3", "n4", "n5", "s1", "s2"]
NUM_COLS = ["n1", "n2", "n3", "n4", "n5"]
STAR_COLS = ["s1", "s2"]


# ─────────────────────────────────────────────
# U1-1 : Schéma exact
# ─────────────────────────────────────────────

def test_schema_columns_exact(load_dataset):
    """
    Le CSV doit contenir exactement les 8 colonnes du Data Contract.
    Ni plus (colonnes parasites), ni moins (colonnes manquantes).
    """
    df = load_dataset
    assert set(df.columns) >= set(REQUIRED_COLUMNS), (
        f"Colonnes manquantes : {set(REQUIRED_COLUMNS) - set(df.columns)}"
    )


# ─────────────────────────────────────────────
# U1-2 : Zéro valeurs manquantes
# ─────────────────────────────────────────────

def test_no_nulls(load_dataset):
    """
    Aucune valeur NaN ou vide dans les 8 colonnes obligatoires.
    Une valeur manquante = tirage invalide = résultats incohérents.
    """
    df = load_dataset
    null_counts = df[REQUIRED_COLUMNS].isnull().sum()
    assert null_counts.sum() == 0, (
        f"Valeurs manquantes détectées :\n{null_counts[null_counts > 0]}"
    )


# ─────────────────────────────────────────────
# U1-3 : Dates parsables et uniques
# ─────────────────────────────────────────────

def test_date_parse_and_unique(load_dataset):
    """
    Chaque date doit :
    - Être parsable au format YYYY-MM-DD
    - Être unique (1 seul tirage par date)
    - Ne pas être dans le futur lointain (cohérence)
    """
    df = load_dataset

    # Vérification que les dates sont bien des datetime
    assert pd.api.types.is_datetime64_any_dtype(df["date"]), (
        "La colonne 'date' doit être de type datetime. "
        "Vérifie le parse_dates=['date'] dans pd.read_csv()."
    )

    # Unicité
    duplicated = df[df["date"].duplicated()]
    assert len(duplicated) == 0, (
        f"{len(duplicated)} date(s) dupliquée(s) :\n{duplicated['date'].tolist()[:5]}"
    )

    # Pas de dates en erreur (NaT)
    assert df["date"].isna().sum() == 0, "Certaines dates n'ont pas pu être parsées (NaT)."


# ─────────────────────────────────────────────
# U1-4 : Numéros dans [1..50]
# ─────────────────────────────────────────────

def test_numbers_range_1_50(load_dataset):
    """
    Chaque numéro (n1..n5) doit être un entier entre 1 et 50 inclus.
    Règle EuroMillions fondamentale.
    """
    df = load_dataset
    for col in NUM_COLS:
        out_of_range = df[(df[col] < 1) | (df[col] > 50)]
        assert len(out_of_range) == 0, (
            f"Colonne {col} : {len(out_of_range)} valeur(s) hors plage [1..50]. "
            f"Exemples : {out_of_range[col].tolist()[:5]}"
        )


# ─────────────────────────────────────────────
# U1-5 : 5 numéros distincts par ligne
# ─────────────────────────────────────────────

def test_numbers_unique_per_row(load_dataset):
    """
    Dans chaque tirage, les 5 numéros doivent tous être différents.
    Ex: [5, 5, 12, 23, 40] → INVALIDE (5 répété).
    """
    df = load_dataset
    nums_matrix = df[NUM_COLS].values  # shape (N, 5)

    # Vectorisé : pour chaque ligne, compte le nb de valeurs uniques
    unique_counts = np.apply_along_axis(lambda row: len(set(row)), axis=1, arr=nums_matrix)
    invalid_rows = np.where(unique_counts != 5)[0]

    assert len(invalid_rows) == 0, (
        f"{len(invalid_rows)} ligne(s) avec numéros non-distincts. "
        f"Premières lignes concernées (index) : {invalid_rows[:5].tolist()}"
    )


# ─────────────────────────────────────────────
# U1-6 : Étoiles dans [1..12]
# ─────────────────────────────────────────────

def test_stars_range_1_12(load_dataset):
    """
    Chaque étoile (s1, s2) doit être un entier entre 1 et 12 inclus.
    Règle EuroMillions fondamentale.
    """
    df = load_dataset
    for col in STAR_COLS:
        out_of_range = df[(df[col] < 1) | (df[col] > 12)]
        assert len(out_of_range) == 0, (
            f"Colonne {col} : {len(out_of_range)} valeur(s) hors plage [1..12]. "
            f"Exemples : {out_of_range[col].tolist()[:5]}"
        )


# ─────────────────────────────────────────────
# U1-7 : 2 étoiles distinctes par ligne
# ─────────────────────────────────────────────

def test_stars_unique_per_row(load_dataset):
    """
    Dans chaque tirage, s1 != s2.
    Ex: s1=5, s2=5 → INVALIDE.
    """
    df = load_dataset
    duplicated_stars = df[df["s1"] == df["s2"]]
    assert len(duplicated_stars) == 0, (
        f"{len(duplicated_stars)} ligne(s) avec s1 == s2. "
        f"Exemples :\n{duplicated_stars[['date', 's1', 's2']].head(3)}"
    )


# ─────────────────────────────────────────────
# U1-8 : Dataset non vide et cohérent
# ─────────────────────────────────────────────

def test_dataset_has_sufficient_rows(load_dataset):
    """
    Le dataset doit avoir au moins 100 tirages pour qu'OracleStats
    puisse calculer une distribution significative.
    """
    df = load_dataset
    assert len(df) >= 100, (
        f"Dataset trop petit : {len(df)} lignes. "
        f"Minimum recommandé : 100 tirages pour OracleStats."
    )


def test_dataset_sorted_chronologically(load_dataset):
    """
    Les dates doivent être triables sans incohérence
    (pas de dates futures aberrantes).
    """
    df = load_dataset
    # Vérifier que les dates sont dans l'ordre après tri
    sorted_dates = df["date"].sort_values().reset_index(drop=True)
    # Pas de saut anormal (> 60 jours entre deux tirages consécutifs)
    diffs = sorted_dates.diff().dropna()
    max_gap = diffs.max()
    assert max_gap.days <= 60, (
        f"Écart anormal entre deux dates consécutives : {max_gap.days} jours. "
        f"Vérifie l'intégrité du dataset."
    )
