#!/bin/sh
# Point d'entrée du container collector.
# Clone ou met à jour le code depuis GitHub à chaque démarrage,
# puis lance l'application.

set -e

REPO_URL="https://github.com/romain2412/ao-veille.git"
CODE_DIR="/srv/app"        # code cloné depuis GitHub
CONFIG_DIR="/app/config"   # config injectée via volume Docker
BRANCH="${GIT_BRANCH:-main}"

echo "==> Récupération du code depuis GitHub (branche: $BRANCH)..."

if [ -d "$CODE_DIR/.git" ]; then
  echo "    Dépôt existant — git pull"
  git -C "$CODE_DIR" fetch origin "$BRANCH"
  git -C "$CODE_DIR" reset --hard "origin/$BRANCH"
else
  echo "    Premier démarrage — git clone"
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$CODE_DIR"
fi

echo "==> Installation / mise à jour des dépendances..."
pip install --quiet --no-cache-dir -r "$CODE_DIR/requirements.txt"

echo "==> Installation du navigateur Playwright (Chromium)..."
playwright install chromium --with-deps 2>/dev/null || true

# Surcharger la config avec celle du volume si elle existe
if [ -f "$CONFIG_DIR/settings.yml" ]; then
  echo "==> Config externe détectée, utilisation du volume..."
  cp "$CONFIG_DIR/settings.yml" "$CODE_DIR/config/settings.yml"
fi

echo "==> Démarrage de l'application..."
exec python "$CODE_DIR/main.py"
