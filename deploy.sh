#!/bin/sh
# Déploiement ao-veille — à lancer sur le serveur depuis le dossier du projet.
#
#   cd /opt/ao-veille && ./deploy.sh
#
# Récupère le code, reconstruit les images et redémarre la stack.
# Les migrations de base de données sont appliquées automatiquement par le
# collecteur au démarrage (alembic upgrade head).
set -e

echo "==> git pull"
git pull --ff-only

echo "==> build + (re)démarrage des conteneurs"
docker compose up -d --build

echo "==> état des services"
docker compose ps

echo "==> nettoyage des images orphelines"
docker image prune -f

echo "==> Déploiement terminé."
