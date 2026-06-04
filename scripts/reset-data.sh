#!/bin/sh
# Vide les tables de DONNÉES de la base (PROD ou local).
#
# Conserve : users, alembic_version, invitations.
# Vide     : tenders, collection_runs, collection_requests, app_state.
#
# Fait un dump de sauvegarde horodaté AVANT, et demande une confirmation.
#
# Usage (depuis le dossier du projet) :
#   sh scripts/reset-data.sh
#
set -e

DB_SERVICE="db"
DB_USER="${POSTGRES_USER:-ao_user}"
DB_NAME="${POSTGRES_DB:-ao_veille}"

# Tables à vider (données métier uniquement)
# Liste séparée par virgules pour la commande TRUNCATE (syntaxe SQL)
TABLES="tenders, collection_runs, collection_requests, app_state"

echo "============================================================"
echo "  Réinitialisation des données — base '$DB_NAME'"
echo "============================================================"
echo "  Tables VIDÉES   : $TABLES"
echo "  Tables CONSERVÉES: users, alembic_version, invitations"
echo "------------------------------------------------------------"

# --- État avant ---
echo "Comptage actuel :"
docker compose exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$DB_NAME" -P pager=off -c \
  "select 'tenders' t, count(*) from tenders
   union all select 'collection_runs', count(*) from collection_runs
   union all select 'collection_requests', count(*) from collection_requests
   union all select 'app_state', count(*) from app_state
   union all select 'users (conserve)', count(*) from users
   union all select 'invitations (conserve)', count(*) from invitations;"

# --- Confirmation ---
printf "\n⚠️  Cette opération est IRRÉVERSIBLE (un dump est fait avant).\n"
printf "Tapez exactement 'VIDER' pour confirmer : "
read CONFIRM
if [ "$CONFIRM" != "VIDER" ]; then
  echo "Annulé."
  exit 1
fi

# --- Sauvegarde (dump) ---
STAMP=$(date +%Y%m%d_%H%M%S)
DUMP="backup_${DB_NAME}_${STAMP}.sql"
echo "==> Sauvegarde dans ./$DUMP ..."
docker compose exec -T "$DB_SERVICE" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$DUMP"
echo "    Dump OK ($(wc -c < "$DUMP") octets)."

# --- Vidage ---
echo "==> Vidage des tables..."
docker compose exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$DB_NAME" -c \
  "TRUNCATE TABLE $TABLES RESTART IDENTITY;"

# --- État après ---
echo "==> Terminé. Comptage après :"
docker compose exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$DB_NAME" -P pager=off -c \
  "select 'tenders' t, count(*) from tenders
   union all select 'collection_runs', count(*) from collection_runs
   union all select 'collection_requests', count(*) from collection_requests
   union all select 'app_state', count(*) from app_state
   union all select 'users (conserve)', count(*) from users
   union all select 'invitations (conserve)', count(*) from invitations;"

echo "============================================================"
echo "  Sauvegarde disponible : ./$DUMP"
echo "  Restauration possible : "
echo "    docker compose exec -T $DB_SERVICE psql -U $DB_USER -d $DB_NAME < $DUMP"
echo "============================================================"
