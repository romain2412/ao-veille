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
  # Dépôt déjà initialisé → simple mise à jour
  echo "    Dépôt existant — git pull"
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  # Premier démarrage : /app existe mais est vide (créé par WORKDIR)
  # On clone dans un dossier temporaire puis on déplace le contenu
  echo "    Premier démarrage — git clone"
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" /tmp/ao-veille-src
  # Déplacer tout le contenu (y compris .git) dans /app
  cp -a /tmp/ao-veille-src/. "$APP_DIR/"
  rm -rf /tmp/ao-veille-src
fi

echo "==> Installation / mise à jour des dépendances..."
pip install --quiet --no-cache-dir -r "$APP_DIR/requirements.txt"

echo "==> Démarrage de l'application..."
exec python "$APP_DIR/main.py"
