"""
config.py — Configuration globale de l'application
====================================================

Toutes les valeurs configurables sont ici.
En production, les variables d'environnement surchargent ces valeurs.

Exemple :
    DATA_PATH=/app/data/euromillions_history.csv uvicorn app.main:app
"""

from pathlib import Path

# ─────────────────────────────────────────────
# Chemins
# ─────────────────────────────────────────────

# Dossier racine de l'application (backend/app/)
APP_DIR = Path(__file__).parent.parent

# Chemin vers le CSV historique
DATA_PATH = APP_DIR / "data" / "euromillions_history.csv"

# Chemin vers le manifest de version du dataset
DATA_MANIFEST_PATH = APP_DIR / "data" / "manifest.json"

# ─────────────────────────────────────────────
# Versioning
# ─────────────────────────────────────────────

APP_VERSION = "1.0.0"
DATA_VERSION = "2026.03.06"   # mis à jour à chaque update du CSV

# ─────────────────────────────────────────────
# Paramètres des modèles (valeurs par défaut)
# ─────────────────────────────────────────────

ORACLE_STATS_DEFAULTS = {
    "window_size": 200,
    "alpha": 1.0,
    "lambda_uniform": 0.25,
}

SMART_GRID_DEFAULTS = {
    "n_candidates": 100_000,
    "sum_range": (100, 176),
    "max_common": 3,
}

# ─────────────────────────────────────────────
# Sécurité & rate limiting
# ─────────────────────────────────────────────

RATE_LIMIT_PER_MINUTE = 30   # requêtes max par IP par minute
CORS_ORIGINS = [
    "http://localhost:5173",   # Vite dev server (frontend React)
    "http://localhost:3000",   # alternative
]

# ─────────────────────────────────────────────
# Timezone
# ─────────────────────────────────────────────

TIMEZONE = "Europe/Paris"
