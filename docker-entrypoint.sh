#!/bin/sh
# Point d'entrée du container collector.
# Clone ou met à jour le code depuis GitHub à chaque démarrage,
# puis lance l'application.

set -e

REPO_URL="https://github.com/romain2412/ao-veille.git"
APP_DIR="/app"
BRANCH="${GIT_BRANCH:-main}"

echo "==> Récupération du code depuis GitHub (branche: $BRANCH)..."

if [ -d "$APP_DIR/.git" ]; then
  echo "    Dépôt existant — git pull"
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  echo "    Premier démarrage — git clone"
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$APP_DIR"
fi

echo "==> Installation / mise à jour des dépendances..."
pip install --quiet --no-cache-dir -r "$APP_DIR/requirements.txt"

echo "==> Démarrage de l'application..."
exec python "$APP_DIR/main.py"
