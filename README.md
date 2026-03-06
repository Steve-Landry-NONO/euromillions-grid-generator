# EuroMillions Grid Generator

Application web de génération de grilles EuroMillions via deux approches complémentaires.

> ⚠️ **Disclaimer** — EuroMillions est un jeu de hasard. Les résultats sont aléatoires et indépendants. Cette application génère des grilles à titre informatif/pédagogique et n'offre **aucune garantie de gain**.

---

## Modèles disponibles

| Modèle | Type | Description |
|--------|------|-------------|
| **OracleStats v1** | Probabiliste | Analyse l'historique des tirages, construit une distribution de probabilités par lissage de Laplace, génère des grilles par échantillonnage pondéré sans remise |
| **SmartGrid v1** | Optimiseur | Génère 100 000 candidats aléatoires, les score via des heuristiques anti-partage (pénalités dates/suites/clusters), sélectionne les meilleurs avec contrainte de diversité |

---

## Stack technique

```
backend/   Python 3.11 · FastAPI · Pydantic v2 · NumPy · Pandas · SQLite
frontend/  React 18 · TypeScript · Vite
infra/     Docker · docker-compose
tests/     pytest · httpx
```

---

## Structure du projet

```
euromillions-grid-generator/
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py              # Constantes globales (paths, params modèles, CORS)
│   │   ├── data/
│   │   │   ├── euromillions_history.csv   # Dataset historique tirages (versionné)
│   │   │   └── manifest.json          # Métadonnées dataset (version, date MAJ, nb lignes)
│   │   ├── models/
│   │   │   └── schemas.py             # Schémas Pydantic (GenerateRequest/Response, TicketDTO…)
│   │   ├── routers/
│   │   │   ├── health.py              # GET  /api/v1/health
│   │   │   ├── models_router.py       # GET  /api/v1/models
│   │   │   ├── draws.py               # GET  /api/v1/draws/next
│   │   │   └── generate.py            # POST /api/v1/generate
│   │   ├── services/
│   │   │   ├── oracle_stats.py        # Modèle OracleStats v1
│   │   │   ├── smart_grid.py          # Modèle SmartGrid v1
│   │   │   ├── data_loader.py         # Chargement + validation CSV (Data Contract)
│   │   │   ├── draw_calendar.py       # Calcul prochain vendredi (timezone Europe/Paris)
│   │   │   └── generation_service.py  # Orchestration API ↔ modèles ML
│   │   └── main.py                    # App FastAPI (CORS, lifespan, routers, logging)
│   ├── tests/
│   │   ├── conftest.py                # Fixtures partagées (dataset, modèles, seed)
│   │   ├── unit/
│   │   │   ├── test_data_contract.py  # U1 — Validation schéma CSV (BLOQUANT)
│   │   │   ├── test_sampling.py       # U2 — Sampling sans doublons
│   │   │   ├── test_smartgrid_scoring.py  # U3 — Correctness scoring SmartGrid
│   │   │   ├── test_draw_calendar.py  # U4 — Calendrier vendredi + DST
│   │   │   └── test_copy_compliance.py    # U5 — Scan mots interdits (BLOQUANT)
│   │   └── integration/
│   │       ├── test_health_and_models.py  # I1 — /health + /models
│   │       ├── test_generate.py           # I2/I3/I6 — /generate valide, invalide, perf
│   │       └── test_security_and_db.py    # I4/I5 — Rate limit + persistance DB
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pytest.ini
│
├── frontend/
│   ├── src/
│   │   └── App.jsx                    # App React complète (composants + API client)
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
│
├── docker-compose.yml                 # Backend + Frontend en un seul `docker-compose up`
├── .gitignore
└── README.md
```

---

## Démarrage rapide

### Avec Docker (recommandé)

```bash
git clone https://github.com/<ton-compte>/euromillions-grid-generator.git
cd euromillions-grid-generator
docker-compose up --build
```

- Frontend : http://localhost:5173
- API : http://localhost:8000
- Doc interactive : http://localhost:8000/docs

### Sans Docker

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

---

## API — Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/health` | Healthcheck + état du dataset |
| `GET` | `/api/v1/models` | Liste des modèles disponibles |
| `GET` | `/api/v1/draws/next?mode=friday_only` | Prochain tirage (vendredi, Europe/Paris) |
| `POST` | `/api/v1/generate` | Générer 1, 5 ou 10 grilles |

**Exemple — POST /api/v1/generate**
```json
{
  "model_id": "smartgrid_v1",
  "n_tickets": 5,
  "mode": "friday_only",
  "options": {
    "avoid_numbers": [7, 13],
    "seed": 42
  }
}
```

Documentation interactive complète : http://localhost:8000/docs

---

## Tests

```bash
cd backend

# Tous les tests unitaires (pas de dépendance FastAPI)
pytest tests/unit/ -v

# Tous les tests (unitaires + intégration)
pytest tests/ -v

# Tests de performance uniquement
pytest tests/ -v -m slow

# Sans les tests lents
pytest tests/ -v -m "not slow"
```

**Couverture unitaire actuelle : 60 tests, 60 passed**

| Suite | Tests | Statut | Gate prod |
|-------|-------|--------|-----------|
| U1 — Data Contract | 9 | ✅ | BLOQUANT |
| U2 — Sampling | 13 | ✅ | BLOQUANT |
| U3 — SmartGrid Scoring | 17 | ✅ | — |
| U4 — Draw Calendar | 16 | ✅ | BLOQUANT |
| U5 — Copy Compliance | 5 | ✅ | BLOQUANT |

---

## Mise à jour du dataset

```bash
# 1. Remplacer le fichier
cp nouveau_dataset.csv backend/app/data/euromillions_history.csv

# 2. Mettre à jour le manifest
# backend/app/data/manifest.json
{
  "data_version": "2026.03.06",
  "source": "manual_update",
  "last_updated_at": "2026-03-06T08:00:00+01:00",
  "rows": 1907,
  "notes": "Added draw results up to 2026-03-03"
}

# 3. Valider
pytest tests/unit/test_data_contract.py -v

# 4. Smoke test
pytest tests/integration/test_health_and_models.py -v
```

---

## Roadmap

| Version | Contenu |
|---------|---------|
| **MVP v1** ✅ | OracleStats v1, SmartGrid v1, API FastAPI, React UI, tests unitaires |
| **V2** | Mode mardi/vendredi auto, export PDF, comptes utilisateurs, CI/CD GitHub Actions |
| **V3** | Marketplace de stratégies SmartGrid, analytics avancé, modèle ML multi-label |

---

## Conformité & jeu responsable

- Aucune promesse de gain dans l'UI ni dans l'API
- Disclaimers visibles sur chaque modèle et dans chaque réponse `/generate`
- Test automatique de conformité copy (`test_copy_compliance.py`) — gate prod bloquant
- Page "Jeu responsable" et "Méthodologie & limites" prévues en V2

*Jouez avec modération.*
