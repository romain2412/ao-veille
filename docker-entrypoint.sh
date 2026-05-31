#!/bin/sh
# Point d'entrée du container collector.
# Clone ou met à jour le code depuis GitHub à chaque démarrage,
# puis lance l'application.

set -e

REPO_URL="https://github.com/romain2412/ao-veille.git"
CODE_DIR="/srv/app"
CONFIG_DIR="/app/config"
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

# Surcharger la config avec celle du volume si elle existe
if [ -f "$CONFIG_DIR/settings.yml" ]; then
  echo "==> Config externe détectée, utilisation du volume..."
  cp "$CONFIG_DIR/settings.yml" "$CODE_DIR/config/settings.yml"
fi

echo "==> Démarrage de l'application..."

# Construction des arguments CLI
ARGS=""
if [ -n "$COLLECT_START_SOURCES" ]; then
  echo "    Sources au démarrage : $COLLECT_START_SOURCES"
  ARGS="--start-sources $COLLECT_START_SOURCES"
fi

exec python "$CODE_DIR/main.py" $ARGS
