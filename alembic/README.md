# Migrations Alembic — ao-veille

Le schéma de la base est géré par Alembic (plus de `create_all`).

## Commandes utiles

Les migrations s'appliquent **automatiquement au démarrage du collecteur**
(`docker-entrypoint.sh` → `alembic upgrade head`). Manuellement :

```bash
# Appliquer toutes les migrations
docker compose exec collector alembic upgrade head

# Voir la révision courante
docker compose exec collector alembic current

# Générer une nouvelle migration après modif des modèles
docker compose exec collector alembic revision --autogenerate -m "description"
```

## Adopter Alembic sur une base existante (déjà peuplée)

Si la base contient déjà les tables (cas du serveur de prod), il ne faut PAS
re-jouer la migration initiale. On pose la baseline une seule fois :

```bash
docker compose exec collector alembic stamp head
```

Ensuite, les migrations suivantes s'appliqueront normalement via `upgrade head`.
