"""
test_health_and_models.py — I1 : Health & meta endpoints
test_draws_next.py        — I2 : Draws/next endpoint
==========================================================

Ces tests d'intégration vérifient les endpoints "légers" de l'API.
Ils nécessitent FastAPI + httpx pour tourner.

Si FastAPI n'est pas installé (env sans réseau), les tests sont
automatiquement skippés avec un message clair.

POUR LANCER :
    pip install fastapi uvicorn httpx pytest-asyncio
    pytest tests/integration/ -v
"""

import pytest
import sys

# ── Skip automatique si FastAPI non disponible ──────────────
try:
    from fastapi.testclient import TestClient
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

pytestmark = pytest.mark.integration

requires_fastapi = pytest.mark.skipif(
    not FASTAPI_AVAILABLE,
    reason="FastAPI/httpx non installés — lance 'pip install fastapi httpx' pour ces tests"
)


# ─────────────────────────────────────────────
# Fixture : client de test FastAPI
# ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """
    Crée un TestClient FastAPI synchrone.
    Le TestClient gère le lifespan (startup/shutdown) automatiquement.
    scope="module" → client créé une fois pour tous les tests du fichier.
    """
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI non disponible")

    from app.main import app
    with TestClient(app) as c:
        yield c


# ═════════════════════════════════════════════
# I1 — Health & models
# ═════════════════════════════════════════════

@requires_fastapi
class TestHealthEndpoint:

    def test_health_ok(self, client):
        """
        GET /api/v1/health doit retourner 200 avec status='ok'.
        Utilisé par le monitoring et le Runbook (Incident A).
        """
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "dataset_rows" in data
        assert data["dataset_rows"] > 0, "Le dataset doit être chargé et non vide"

    def test_health_returns_data_version(self, client):
        """La réponse /health doit inclure la version du dataset."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "data_version" in data
        assert data["data_version"] != "unknown"

    def test_health_returns_last_date(self, client):
        """La réponse /health doit inclure la date du dernier tirage."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "dataset_last_date" in data
        # Format YYYY-MM-DD
        last_date = data["dataset_last_date"]
        assert len(last_date) == 10 and last_date[4] == "-"


@requires_fastapi
class TestModelsEndpoint:

    def test_models_contains_oraclestats_and_smartgrid(self, client):
        """
        GET /api/v1/models doit retourner les 2 modèles MVP.
        US-A1 : "Une page affiche 2 cartes modèle minimum."
        """
        response = client.get("/api/v1/models")
        assert response.status_code == 200

        data = response.json()
        assert "models" in data
        model_ids = [m["model_id"] for m in data["models"]]
        assert "oraclestats_v1" in model_ids, "OracleStats manquant dans /models"
        assert "smartgrid_v1" in model_ids, "SmartGrid manquant dans /models"

    def test_models_have_required_fields(self, client):
        """
        Chaque modèle doit contenir les champs nécessaires à l'UI.
        """
        response = client.get("/api/v1/models")
        data = response.json()
        required_fields = ["model_id", "name", "short_description", "disclaimer", "version"]

        for model in data["models"]:
            for field in required_fields:
                assert field in model, f"Modèle {model.get('model_id')} manque le champ '{field}'"

    def test_models_disclaimers_not_empty(self, client):
        """
        Chaque modèle doit avoir un disclaimer non vide (conformité R1).
        """
        response = client.get("/api/v1/models")
        data = response.json()
        for model in data["models"]:
            assert model["disclaimer"], (
                f"Modèle {model['model_id']} a un disclaimer vide — non conforme R1"
            )


# ═════════════════════════════════════════════
# I2 — Draws/next
# ═════════════════════════════════════════════

@requires_fastapi
class TestDrawsNextEndpoint:

    def test_draws_next_friday_only_returns_iso_date(self, client):
        """
        GET /api/v1/draws/next?mode=friday_only doit retourner une date ISO valide.
        """
        response = client.get("/api/v1/draws/next?mode=friday_only")
        assert response.status_code == 200

        data = response.json()
        assert "draw_target" in data
        draw = data["draw_target"]

        assert "date" in draw
        assert "mode" in draw
        assert "label" in draw

        # Format ISO
        date_str = draw["date"]
        assert len(date_str) == 10, f"Date non ISO : {date_str}"
        assert date_str[4] == "-" and date_str[7] == "-"

    def test_draws_next_returns_a_friday(self, client):
        """
        La date retournée doit toujours être un vendredi.
        """
        from datetime import date
        response = client.get("/api/v1/draws/next?mode=friday_only")
        data = response.json()
        result_date = date.fromisoformat(data["draw_target"]["date"])
        assert result_date.weekday() == 4, (
            f"La date retournée ({result_date}) n'est pas un vendredi "
            f"(weekday={result_date.weekday()})"
        )

    def test_draws_next_mode_unknown_returns_400(self, client):
        """
        Un mode inconnu doit retourner 400, pas 500.
        """
        response = client.get("/api/v1/draws/next?mode=tuesday_only")
        assert response.status_code == 400

    def test_draws_next_label_in_french(self, client):
        """Le label doit être en français et contenir 'Vendredi'."""
        response = client.get("/api/v1/draws/next?mode=friday_only")
        data = response.json()
        label = data["draw_target"]["label"]
        assert "Vendredi" in label, f"Label pas en français : {label}"
