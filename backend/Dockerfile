# ─────────────────────────────────────────────
# Dockerfile — Backend FastAPI
# ─────────────────────────────────────────────

FROM python:3.11-slim

# Répertoire de travail dans le container
WORKDIR /app

# Copier les dépendances en premier (cache Docker optimisé)
# Si requirements.txt ne change pas, cette couche est réutilisée
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Port exposé
EXPOSE 8000

# Commande de démarrage
# --host 0.0.0.0 : écoute sur toutes les interfaces (requis dans Docker)
# --workers 1    : 1 worker en MVP (augmenter en prod)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
