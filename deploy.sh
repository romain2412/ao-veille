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

# Vérifications post-déploiement (purement informatives, n'échouent jamais)
echo "==> version de migration appliquée :"
docker exec ao-veille-db-1 psql -U ao_user -d ao_veille -t -A -c "select version_num from alembic_version;" || true
echo "==> health check API :"
curl -s -o /dev/null -w "%{http_code}\n" https://ao.veille.fbvrd-tools.fr/api/health || true

echo "==> Déploiement terminé."
