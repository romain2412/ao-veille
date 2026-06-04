# État du projet — ao-veille (point de situation)

> Document de passation entre sessions de développement.
> Dernière mise à jour : 2026-06-03.

## 1. Qu'est-ce que c'est

Application de **veille d'appels d'offres** (AO) pour FB VRD (bureau d'études
VRD & Paysage). Collecte automatique d'AO depuis plusieurs sources, scoring de
pertinence, portail web de consultation + page d'administration.

## 2. Environnements

| | Local (dev/test) | Production |
|---|---|---|
| Emplacement | `C:\Users\romai\OneDrive\Documents\GitHub\FBVRD\ao-veille` | serveur `212.227.75.168`, dossier `/opt/ao-veille` |
| Lancement | `deploy-local.ps1` (Docker Desktop) → http://localhost:8080 | `./deploy.sh` → https://ao.veille.fbvrd-tools.fr |
| Conteneurs | `ao-veille-{db,api,collector,frontend}` (+ caddy en prod) | idem + `ao-veille-caddy-1` (HTTPS) |
| Python | **uniquement dans les conteneurs** (pas installé sur Windows) | idem |

**Important (local)** : pas de Python/openpyxl sur la machine Windows → tout
script Python se lance via `docker exec ao-veille-<service>-1 python ...`.
Le local utilise `docker-compose.yml` + `docker-compose.local.yml` (frontend
exposé sur 8080, Caddy neutralisé).

## 3. Architecture technique

- **Backend** : FastAPI (`api/`), SQLAlchemy async + PostgreSQL (`storage/`),
  scoring (`processor/scorer.py`), collecteurs (`collector/`), scheduler
  APScheduler (`scheduler/jobs.py`), mailer SMTP (`notifier/mailer.py`).
- **Frontend** : React + Vite + Tailwind + react-query (`frontend/src/`).
- **Reverse-proxy / HTTPS** : Caddy (certificat Let's Encrypt auto) en prod.
- **Migrations** : Alembic (`alembic/versions/`), appliquées au démarrage du
  collecteur (`alembic upgrade head` dans `docker-entrypoint.sh`).
- **Déploiement** : code embarqué dans les images (plus de clone GitHub runtime).
  `deploy.sh` = `git pull` + `docker compose up -d --build` + `image prune`.

### Sources de collecte (6)
`boamp` (API), `demat_ampa` (Playwright), `e_marches_publics` (Playwright),
`noalis` (httpx/bs4), `vilogia` (httpx/bs4), `aquitanis` (httpx/bs4).
Détail des critères de sélection + scoring : voir `../veille_sources.xlsx`.

### Scoring (config `config/settings.yml`)
Mots-clés pondérés par groupe (commun + spécifique par source) + bonus
Nouvelle-Aquitaine (+20) − malus hors TRAVAUX/SERVICES (−10). **Seuil de
conservation : score ≥ 20.** Collecte toutes les 4 h, lookback 10 j.

## 4. Fonctionnalités en place

- Portail : liste des AO (non expirés), bandeau de sources cliquable
  (stats vus/non-vus + filtre + couleurs), recherche, filtres, pagination.
  Tri : Nouvelle-Aquitaine d'abord, puis score, puis date de publication.
- Auth JWT, rate-limiting sur `/auth/login`, comptes admin/non-admin.
- **Page Admin** (`/admin`, réservée admin) :
  - Monitoring par source : statut dernier run, collecté / score validated /
    inserted / updated, durée, date, **prochain run**.
  - Boutons **Relancer** (par source) et **Tout relancer** (file de demandes
    `collection_requests` traitée par le collecteur, polling du statut).
  - **Comptes utilisateurs** : activer/désactiver (garde-fous : pas
    d'auto-désactivation, pas le dernier admin actif).
  - **Invitations** : créer une invitation (email + rôle admin ou non) → lien
    `/invite/<token>` + **envoi par email** (Resend). L'utilisateur choisit son
    mot de passe. Invitations en attente listées (utilisées/expirées masquées).
- **Email** : via Resend (SMTP), domaine `fbvrd-tools.fr` vérifié, expéditeur
  `no-reply@fbvrd-tools.fr`. Dégradation gracieuse si SMTP non configuré.

## 5. Migrations Alembic
`0001` schéma initial · `0002` colonnes array→text[] · `0003` collection_runs ·
`0004` app_state · `0005` collection_requests · `0006` run_metrics
(score_validated/updated) · `0007` invitations. **Tête actuelle : `0007`.**

## 6. Configuration `.env` (NON versionné — git-ignoré)
Variables clés : `DATABASE_URL`, `SECRET_KEY` (obligatoire), `CORS_ORIGINS`,
`COLLECT_START_SOURCES`, `APP_BASE_URL`, `SMTP_*` (Resend). Voir `.env.example`.
⚠️ Le `.env` vit uniquement sur chaque machine ; il n'est pas récupéré par
`git pull`. Toute nouvelle variable doit être ajoutée manuellement en prod.

## 7. À FAIRE / points en suspens

### À vérifier en priorité au prochain démarrage
- [ ] Confirmer que la PROD a bien déployé le dernier lot (migrations 0002→0007
      + toutes les features admin). Vérifier :
      `docker exec ao-veille-db-1 psql -U ao_user -d ao_veille -t -A -c "select version_num from alembic_version;"` → doit afficher `0007_invitations`.
- [ ] Confirmer `.env` prod : `APP_BASE_URL=https://ao.veille.fbvrd-tools.fr` + variables SMTP Resend.

### Pistes évoquées, non implémentées
- [ ] **Tri configurable** des AO côté portail (menu « Trier par » : pertinence,
      date limite (urgent), score, date de publication). Gérer `deadline NULL`
      en `NULLS LAST`.
- [ ] **AO BOAMP sans date limite** : ~21 % des AO ont `deadline = NULL`
      (champ `datelimitereponse` parfois absent côté API BOAMP). À investiguer
      (parsing récupérable ?).
- [ ] **Centraliser la config d'environnement** dans un module `config.py`
      (aujourd'hui `os.getenv()` dispersés : SECRET_KEY, DATABASE_URL, CORS,
      SMTP_*, APP_BASE_URL). Point noté dans AUDIT.md.

### Sécurité / dette (AUDIT.md) — restant
- [ ] Désactiver `/docs` et `/openapi.json` en prod.
- [ ] Envisager cookie HttpOnly au lieu de localStorage pour le JWT.
- [ ] Ajouter des tests (aucun actuellement).
- [ ] Optimiser `repository.upsert` (commits par lot).

## 8. Scripts utiles
- `deploy.sh` (prod) / `deploy-local.ps1` (local) : déploiement.
- `scripts/reset-data.sh` : vide les données (garde users/migration/invitations),
  avec dump de sauvegarde + confirmation `VIDER`.
- `scripts/create_admin.py` : crée un admin en CLI.
- `connect-prod-ao-veille.ps1` (hors repo, dans `C:\Users\romai\`) : SSH prod.

## 9. Docs de référence dans le repo
`AUDIT.md` (audit sécurité/qualité), `DEPLOY.md` (déploiement détaillé),
`DEPLOY-HTTPS.md` (mise en place HTTPS), ce fichier.
