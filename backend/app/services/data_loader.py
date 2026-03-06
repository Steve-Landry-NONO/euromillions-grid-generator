"""
data_loader.py — Chargement et cache du dataset CSV
=====================================================

Ce service charge le fichier euromillions_history.csv une seule fois
au démarrage de l'application, puis le garde en mémoire (cache).

POURQUOI UN CACHE ?
Sans cache, chaque requête /generate relirait le fichier CSV depuis
le disque → lent et inefficace. Avec le cache, le DataFrame pandas
est déjà prêt en mémoire.

CYCLE DE VIE :
    startup → _loader.load() → cache prêt
    requête → _loader.get_dataframe() → DataFrame instantané
    shutdown → rien à faire (mémoire libérée automatiquement)
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

from app.core.config import DATA_PATH, DATA_MANIFEST_PATH, DATA_VERSION


class DataLoader:
    """
    Charge, valide et met en cache le dataset EuroMillions.

    Usage (dans main.py) :
        loader = DataLoader()
        loader.load()                    # au démarrage
        df = loader.get_dataframe()      # dans les services
        meta = loader.get_metadata()     # pour /health
    """

    def __init__(self):
        self._df: pd.DataFrame | None = None
        self._metadata: dict = {}

    # ─────────────────────────────────────────
    # Chargement initial
    # ─────────────────────────────────────────

    def load(self, path: Path | str = DATA_PATH) -> None:
        """
        Charge le CSV en mémoire et valide le schéma.
        Appelé une seule fois au démarrage (lifespan FastAPI).

        Lève une exception si le dataset est invalide → l'app ne démarre pas.
        """
        path = Path(path)
        print(f"[DataLoader] Chargement du dataset : {path}")

        if not path.exists():
            raise FileNotFoundError(
                f"Dataset introuvable : {path}\n"
                f"Vérifie que le fichier existe à cet emplacement."
            )

        df = pd.read_csv(path, parse_dates=["date"])
        self._validate(df)

        # Tri chronologique
        df = df.sort_values("date").reset_index(drop=True)
        self._df = df

        # Métadonnées pour /health et les logs
        self._metadata = {
            "rows": len(df),
            "first_date": str(df["date"].min().date()),
            "last_date": str(df["date"].max().date()),
            "data_version": self._read_manifest_version(),
        }

        print(
            f"[DataLoader] ✅ Dataset chargé : {len(df)} tirages "
            f"({self._metadata['first_date']} → {self._metadata['last_date']})"
        )

    def _validate(self, df: pd.DataFrame) -> None:
        """
        Validation Data Contract (checklist "bloquante").
        Si une règle échoue, l'application refuse de démarrer.
        """
        required_cols = {"date", "n1", "n2", "n3", "n4", "n5", "s1", "s2"}

        # 1. Colonnes présentes
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"[DataLoader] Colonnes manquantes : {missing}")

        # 2. Aucune valeur manquante
        if df[list(required_cols)].isnull().any().any():
            raise ValueError("[DataLoader] Dataset contient des valeurs manquantes.")

        # 3. Dates uniques et valides
        if df["date"].duplicated().any():
            raise ValueError("[DataLoader] Des dates sont dupliquées dans le dataset.")

        # 4. Numéros dans [1..50]
        num_cols = ["n1", "n2", "n3", "n4", "n5"]
        for col in num_cols:
            if not df[col].between(1, 50).all():
                raise ValueError(f"[DataLoader] Colonne {col} : valeur hors plage [1..50].")

        # 5. 5 numéros distincts par ligne
        nums_matrix = df[num_cols].values
        for i, row in enumerate(nums_matrix):
            if len(set(row)) != 5:
                raise ValueError(
                    f"[DataLoader] Ligne {i} : numéros non distincts → {row}"
                )

        # 6. Étoiles dans [1..12]
        star_cols = ["s1", "s2"]
        for col in star_cols:
            if not df[col].between(1, 12).all():
                raise ValueError(f"[DataLoader] Colonne {col} : valeur hors plage [1..12].")

        # 7. 2 étoiles distinctes par ligne
        if (df["s1"] == df["s2"]).any():
            raise ValueError("[DataLoader] Certaines lignes ont s1 == s2.")

        print("[DataLoader] ✅ Validation Data Contract : OK")

    def _read_manifest_version(self) -> str:
        """Lit la version du manifest si disponible, sinon retourne la version config."""
        try:
            if DATA_MANIFEST_PATH.exists():
                manifest = json.loads(DATA_MANIFEST_PATH.read_text())
                return manifest.get("data_version", DATA_VERSION)
        except Exception:
            pass
        return DATA_VERSION

    # ─────────────────────────────────────────
    # Accesseurs
    # ─────────────────────────────────────────

    def get_dataframe(self) -> pd.DataFrame:
        """
        Retourne le DataFrame en cache.
        Lève une erreur si load() n'a pas été appelé.
        """
        if self._df is None:
            raise RuntimeError(
                "DataLoader non initialisé. Appelle load() au démarrage."
            )
        return self._df

    def get_metadata(self) -> dict:
        """Retourne les métadonnées du dataset (pour /health)."""
        return self._metadata

    @property
    def is_loaded(self) -> bool:
        return self._df is not None


# ─────────────────────────────────────────────
# Instance globale (singleton)
# ─────────────────────────────────────────────
# On crée une instance unique partagée entre tous les routers.
# FastAPI utilise l'injection de dépendances pour y accéder.

_loader = DataLoader()


def get_loader() -> DataLoader:
    """Fonction d'injection de dépendance FastAPI."""
    return _loader
