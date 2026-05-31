#!/bin/sh
# Point d'entrée du container collector.
# Le code est déjà embarqué dans l'image (COPY . /app).
# 1) applique les migrations de schéma (Alembic)
# 2) lance l'application
set -e

cd /app

echo "==> Application des migrations de base de données (alembic upgrade head)..."
alembic upgrade head

echo "==> Démarrage de l'application..."
ARGS=""
if [ -n "$COLLECT_START_SOURCES" ]; then
  echo "    Sources au démarrage : $COLLECT_START_SOURCES"
  ARGS="--start-sources $COLLECT_START_SOURCES"
fi

exec python /app/main.py $ARGS
