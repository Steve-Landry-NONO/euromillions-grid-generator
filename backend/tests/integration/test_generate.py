"""
test_generate_valid.py   — I2 : POST /generate (payloads valides)
test_generate_invalid.py — I3 : POST /generate (payloads invalides)
test_perf_smoke.py       — I6 : Performance smoke test
==================================================================

Couvre :
  ✓ OracleStats : 1, 5, 10 tickets
  ✓ SmartGrid   : 1, 5, 10 tickets + diversité
  ✓ Payloads invalides → 422
  ✓ Contraintes impossibles → 400
  ✓ Perf : 10 tickets SmartGrid < 2s
"""

import time
import pytest

try:
    from fastapi.testclient import TestClient
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

pytestmark = pytest.mark.integration

requires_fastapi = pytest.mark.skipif(
    not FASTAPI_AVAILABLE,
    reason="FastAPI/httpx non installés — lance 'pip install fastapi httpx'"
)


# ─────────────────────────────────────────────
# Fixture client
# ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI non disponible")
    from app.main import app
    with TestClient(app) as c:
        yield c


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def assert_valid_ticket(ticket: dict, context: str = ""):
    """Valide qu'un ticket respecte toutes les règles EuroMillions."""
    nums = ticket["numbers"]
    stars = ticket["stars"]

    assert len(nums) == 5, f"{context} : attendu 5 numéros, got {len(nums)}"
    assert len(set(nums)) == 5, f"{context} : numéros non-uniques → {nums}"
    assert all(1 <= n <= 50 for n in nums), f"{context} : numéro hors [1..50] → {nums}"

    assert len(stars) == 2, f"{context} : attendu 2 étoiles, got {len(stars)}"
    assert len(set(stars)) == 2, f"{context} : étoiles non-uniques → {stars}"
    assert all(1 <= s <= 12 for s in stars), f"{context} : étoile hors [1..12] → {stars}"


# ═════════════════════════════════════════════
# I2 — Generate (payloads valides)
# ═════════════════════════════════════════════

@requires_fastapi
class TestGenerateOracleStats:

    def test_generate_oraclestats_1_ticket_ok(self, client):
        """OracleStats : génère 1 ticket valide."""
        response = client.post("/api/v1/generate", json={
            "model_id": "oraclestats_v1",
            "n_tickets": 1,
            "mode": "friday_only",
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["tickets"]) == 1
        assert_valid_ticket(data["tickets"][0], "OracleStats 1 ticket")

    def test_generate_oraclestats_5_tickets_ok(self, client):
        """OracleStats : génère 5 tickets, tous valides."""
        response = client.post("/api/v1/generate", json={
            "model_id": "oraclestats_v1",
            "n_tickets": 5,
            "mode": "friday_only",
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["tickets"]) == 5
        for i, t in enumerate(data["tickets"]):
            assert_valid_ticket(t, f"OracleStats ticket {i+1}")

    def test_generate_oraclestats_10_tickets_ok(self, client):
        """OracleStats : génère 10 tickets, tous valides."""
        response = client.post("/api/v1/generate", json={
            "model_id": "oraclestats_v1",
            "n_tickets": 10,
            "mode": "friday_only",
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["tickets"]) == 10
        for i, t in enumerate(data["tickets"]):
            assert_valid_ticket(t, f"OracleStats ticket {i+1}")

    def test_generate_oraclestats_has_draw_target(self, client):
        """La réponse doit inclure le tirage cible."""
        response = client.post("/api/v1/generate", json={
            "model_id": "oraclestats_v1", "n_tickets": 1,
        })
        data = response.json()
        assert "draw_target" in data
        assert "date" in data["draw_target"]
        assert "label" in data["draw_target"]

    def test_generate_oraclestats_has_disclaimer(self, client):
        """La réponse doit contenir un disclaimer non vide (conformité R1)."""
        response = client.post("/api/v1/generate", json={
            "model_id": "oraclestats_v1", "n_tickets": 1,
        })
        data = response.json()
        assert data.get("disclaimer"), "Disclaimer absent ou vide dans la réponse"

    def test_generate_oraclestats_with_seed_reproducible(self, client):
        """Avec le même seed, OracleStats doit générer les mêmes tickets."""
        payload = {
            "model_id": "oraclestats_v1",
            "n_tickets": 3,
            "options": {"seed": 42},
        }
        r1 = client.post("/api/v1/generate", json=payload).json()
        r2 = client.post("/api/v1/generate", json=payload).json()

        for i, (t1, t2) in enumerate(zip(r1["tickets"], r2["tickets"])):
            assert t1["numbers"] == t2["numbers"], (
                f"Ticket {i+1} non reproductible : {t1['numbers']} != {t2['numbers']}"
            )


@requires_fastapi
class TestGenerateSmartGrid:

    def test_generate_smartgrid_1_ticket_ok(self, client):
        """SmartGrid : génère 1 ticket valide avec score."""
        response = client.post("/api/v1/generate", json={
            "model_id": "smartgrid_v1",
            "n_tickets": 1,
            "mode": "friday_only",
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["tickets"]) == 1

        ticket = data["tickets"][0]
        assert_valid_ticket(ticket, "SmartGrid 1 ticket")
        assert ticket["score"] is not None, "SmartGrid doit retourner un score"
        assert 0.0 <= ticket["score"] <= 1.0

    def test_generate_smartgrid_5_tickets_ok(self, client):
        """SmartGrid : génère 5 tickets, tous valides avec scores."""
        response = client.post("/api/v1/generate", json={
            "model_id": "smartgrid_v1", "n_tickets": 5,
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["tickets"]) == 5
        for i, t in enumerate(data["tickets"]):
            assert_valid_ticket(t, f"SmartGrid ticket {i+1}")
            assert t["score"] is not None
            assert 0.0 <= t["score"] <= 1.0

    def test_generate_smartgrid_10_tickets_ok(self, client):
        """SmartGrid : génère 10 tickets, tous valides."""
        response = client.post("/api/v1/generate", json={
            "model_id": "smartgrid_v1", "n_tickets": 10,
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["tickets"]) == 10
        for i, t in enumerate(data["tickets"]):
            assert_valid_ticket(t, f"SmartGrid ticket {i+1}")

    def test_smartgrid_tickets_are_diversified_default(self, client):
        """
        Par défaut, aucun couple de tickets ne doit partager plus
        de 3 numéros (US-C3 : contrainte de diversité).
        """
        response = client.post("/api/v1/generate", json={
            "model_id": "smartgrid_v1", "n_tickets": 5,
        })
        data = response.json()
        tickets = data["tickets"]

        for i in range(len(tickets)):
            for j in range(i + 1, len(tickets)):
                set_i = set(tickets[i]["numbers"])
                set_j = set(tickets[j]["numbers"])
                common = len(set_i & set_j)
                assert common <= 3, (
                    f"Tickets {i+1} et {j+1} partagent {common} numéros (max: 3) "
                    f"→ contrainte diversité violée"
                )

    def test_smartgrid_explain_present(self, client):
        """
        Chaque ticket SmartGrid doit contenir un champ 'explain' non vide.
        US-C4 : "SmartGrid : score + pénalités principales dans explain."
        """
        response = client.post("/api/v1/generate", json={
            "model_id": "smartgrid_v1", "n_tickets": 1,
        })
        ticket = response.json()["tickets"][0]
        assert ticket.get("explain"), "SmartGrid : explain absent ou vide"


# ═════════════════════════════════════════════
# I3 — Generate (payloads invalides)
# ═════════════════════════════════════════════

@requires_fastapi
class TestGenerateInvalidPayloads:

    def test_generate_invalid_model_id_422(self, client):
        """
        Un model_id inconnu doit retourner 422 (pas 500).
        Validation Pydantic automatique.
        """
        response = client.post("/api/v1/generate", json={
            "model_id": "modele_inexistant",
            "n_tickets": 1,
        })
        assert response.status_code == 422, (
            f"model_id invalide doit → 422, got {response.status_code}"
        )

    def test_generate_invalid_n_tickets_422(self, client):
        """
        n_tickets=7 n'est pas dans {1,5,10} → 422.
        """
        response = client.post("/api/v1/generate", json={
            "model_id": "smartgrid_v1",
            "n_tickets": 7,
        })
        assert response.status_code == 422

    def test_generate_n_tickets_zero_422(self, client):
        """n_tickets=0 → 422."""
        response = client.post("/api/v1/generate", json={
            "model_id": "oraclestats_v1",
            "n_tickets": 0,
        })
        assert response.status_code == 422

    def test_generate_missing_model_id_422(self, client):
        """Payload sans model_id → 422 (champ obligatoire)."""
        response = client.post("/api/v1/generate", json={"n_tickets": 1})
        assert response.status_code == 422

    def test_generate_empty_body_422(self, client):
        """Payload vide → 422."""
        response = client.post("/api/v1/generate", json={})
        assert response.status_code == 422

    def test_generate_impossible_constraints_400(self, client):
        """
        Contraintes impossibles (trop de numéros à éviter → pool vide) → 400.
        Le message d'erreur doit être clair, pas une stacktrace.
        """
        response = client.post("/api/v1/generate", json={
            "model_id": "smartgrid_v1",
            "n_tickets": 1,
            "options": {
                # Éviter 46 numéros → il ne reste que 4 numéros disponibles (< 5)
                "avoid_numbers": list(range(1, 47)),
            },
        })
        assert response.status_code in {400, 422}

        # Le message d'erreur ne doit pas être une stacktrace Python
        body = response.text
        assert "Traceback" not in body, "La réponse d'erreur ne doit pas contenir de stacktrace"
        assert "File " not in body, "La réponse d'erreur ne doit pas exposer les chemins internes"

    def test_generate_invalid_mode_422(self, client):
        """Un mode inconnu doit retourner 422."""
        response = client.post("/api/v1/generate", json={
            "model_id": "smartgrid_v1",
            "n_tickets": 1,
            "mode": "wednesday_only",
        })
        assert response.status_code == 422

    def test_generate_error_response_is_json(self, client):
        """Les réponses d'erreur doivent être du JSON valide."""
        response = client.post("/api/v1/generate", json={"model_id": "invalid"})
        assert response.headers["content-type"].startswith("application/json")
        # Vérifier que c'est du JSON parsable
        try:
            response.json()
        except Exception:
            pytest.fail("La réponse d'erreur n'est pas du JSON valide")


# ═════════════════════════════════════════════
# I6 — Performance smoke test (marqué @slow)
# ═════════════════════════════════════════════

@requires_fastapi
class TestPerformanceSmoke:

    @pytest.mark.slow
    def test_generate_smartgrid_10_tickets_under_2s(self, client):
        """
        GATE PROD : 10 tickets SmartGrid doivent être générés en < 2 secondes.
        Cahier des charges : "génération < 2s pour 10 tickets" (Section 12.1).

        Marqué @slow : exécuté uniquement avec pytest -m slow ou sur CI staging.
        """
        t_start = time.perf_counter()
        response = client.post("/api/v1/generate", json={
            "model_id": "smartgrid_v1",
            "n_tickets": 10,
        })
        elapsed = time.perf_counter() - t_start

        assert response.status_code == 200
        assert elapsed < 2.0, (
            f"SmartGrid 10 tickets : {elapsed:.2f}s ≥ 2.0s (seuil). "
            f"Optimise n_candidates ou vectorise le scoring."
        )

    @pytest.mark.slow
    def test_generate_oraclestats_10_tickets_under_500ms(self, client):
        """
        OracleStats 10 tickets doit être < 500ms (sampling très rapide).
        """
        t_start = time.perf_counter()
        response = client.post("/api/v1/generate", json={
            "model_id": "oraclestats_v1",
            "n_tickets": 10,
        })
        elapsed = time.perf_counter() - t_start

        assert response.status_code == 200
        assert elapsed < 0.5, (
            f"OracleStats 10 tickets : {elapsed:.3f}s ≥ 0.5s."
        )

    def test_response_includes_generation_time(self, client):
        """
        La réponse doit inclure generation_time_ms pour le monitoring.
        """
        response = client.post("/api/v1/generate", json={
            "model_id": "smartgrid_v1", "n_tickets": 1,
        })
        data = response.json()
        assert "generation_time_ms" in data
        assert data["generation_time_ms"] > 0
