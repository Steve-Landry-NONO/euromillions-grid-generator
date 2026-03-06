"""
main.py — Point d'entrée de l'application FastAPI
===================================================

C'est ici que tout est assemblé :
1. Création de l'app FastAPI
2. Configuration du CORS (sécurité cross-origin)
3. Chargement du dataset au démarrage (lifespan)
4. Enregistrement des routers (endpoints)
5. Middleware de logging des requêtes

LANCER L'APP :
    uvicorn app.main:app --reload --port 8000

DOC AUTO (OpenAPI) :
    http://localhost:8000/docs       ← interface interactive Swagger
    http://localhost:8000/redoc      ← documentation lisible
    http://localhost:8000/openapi.json ← schéma brut JSON
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import APP_VERSION, CORS_ORIGINS
from app.services.data_loader import get_loader
from app.routers import health, models_router, draws, generate

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Lifespan (démarrage / arrêt)
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gère le cycle de vie de l'application.

    Tout ce qui est AVANT le `yield` s'exécute au démarrage.
    Tout ce qui est APRÈS le `yield` s'exécute à l'arrêt.

    C'est ici qu'on charge le dataset une seule fois en mémoire.
    """
    # ── Démarrage ──────────────────────────────
    logger.info(f"🚀 EuroMillions Grid Generator v{APP_VERSION} — démarrage...")

    loader = get_loader()
    try:
        loader.load()
        logger.info("✅ Dataset chargé avec succès.")
    except FileNotFoundError as e:
        logger.error(f"❌ Dataset introuvable : {e}")
        logger.error("   → Place le fichier euromillions_history.csv dans backend/app/data/")
        raise  # L'app refuse de démarrer sans dataset

    logger.info("✅ Application prête.")
    logger.info("📖 Documentation : http://localhost:8000/docs")

    yield  # L'application tourne ici

    # ── Arrêt ──────────────────────────────────
    logger.info("🛑 Arrêt de l'application.")


# ─────────────────────────────────────────────
# Création de l'application
# ─────────────────────────────────────────────

app = FastAPI(
    title="EuroMillions Grid Generator API",
    description=(
        "API de génération de grilles EuroMillions via deux approches : "
        "OracleStats (probabiliste) et SmartGrid (optimiseur anti-partage). "
        "\n\n"
        "⚠️ **Disclaimer** : EuroMillions est un jeu de hasard. "
        "Les résultats sont aléatoires et indépendants. "
        "Cette API génère des grilles à titre informatif/pédagogique "
        "et n'offre aucune garantie de gain."
    ),
    version=APP_VERSION,
    lifespan=lifespan,
    # Désactive la doc en production si besoin :
    # docs_url=None, redoc_url=None,
)


# ─────────────────────────────────────────────
# Middleware CORS
# ─────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# Permet au frontend React (localhost:5173) d'appeler l'API (localhost:8000)
# En production, remplacer par le vrai domaine.

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Middleware de logging des requêtes
# ─────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Logue chaque requête avec sa latence.
    Format : [METHOD] /path → 200 (45ms)
    """
    t_start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - t_start) * 1000

    logger.info(
        f"[{request.method}] {request.url.path} "
        f"→ {response.status_code} ({elapsed_ms:.0f}ms)"
    )
    return response


# ─────────────────────────────────────────────
# Gestionnaire d'erreurs global
# ─────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Capture toutes les exceptions non gérées.
    Retourne un JSON propre sans stacktrace (sécurité prod).
    """
    logger.error(f"Exception non gérée sur {request.url.path} : {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erreur interne du serveur.",
            "detail": "Une erreur inattendue s'est produite. Réessaie dans quelques instants.",
        },
    )


# ─────────────────────────────────────────────
# Enregistrement des routers
# ─────────────────────────────────────────────
# Tous les endpoints sont préfixés par /api/v1

API_PREFIX = "/api/v1"

app.include_router(health.router,          prefix=API_PREFIX)
app.include_router(models_router.router,   prefix=API_PREFIX)
app.include_router(draws.router,           prefix=API_PREFIX)
app.include_router(generate.router,        prefix=API_PREFIX)


# ─────────────────────────────────────────────
# Route racine (redirect vers docs)
# ─────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "EuroMillions Grid Generator API",
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
    }
