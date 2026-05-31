# 🔍 Audit — `ao-veille` (Veille appels d'offres FB VRD)

> Audit réalisé le 2026-05-31. Périmètre : **sécurité** et **qualité du code**.
> Stack : FastAPI + SQLAlchemy async + PostgreSQL · collecteurs httpx/Playwright · React + Vite + Tailwind · Docker Compose.

**Verdict global** : architecture propre et bien organisée, mais **plusieurs failles de sécurité critiques à corriger avant mise en production**.

---

## Synthèse — Top 5 à corriger en priorité

1. Régénérer `SECRET_KEY` (aléatoire fort) **et** faire échouer le démarrage si absente.
2. Supprimer le fallback de clé secrète par défaut dans `api/auth.py`.
3. Embarquer le code dans l'image Docker plutôt que `git pull` au runtime (`docker-entrypoint.sh`).
4. Fermer le port PostgreSQL exposé + définir un mot de passe fort.
5. Ajouter un rate-limiting sur `/auth/login` + activer TLS/HTTPS.

---

## 🔴 Sécurité — Critique

### 1. Clé JWT faible et devinable
**Fichier** : `.env:5` → `SECRET_KEY=fbvrd-ao-veille-secret-key-2026-changeme`

C'est la clé qui signe **tous les tokens d'authentification**. Elle est prévisible (nom du projet + année + « changeme »). Quiconque la devine peut **forger un token admin** et contourner entièrement l'authentification.

**Correctif** : générer une clé aléatoire forte :
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 2. Fallback dangereux sur la clé secrète dans le code
**Fichier** : `api/auth.py:12` → `os.getenv("SECRET_KEY", "changeme-secret-key-very-long-and-random")`

Si la variable d'environnement n'est pas définie, l'app démarre quand même avec une **clé publique connue** (présente dans le code et `.env.example`).

**Correctif** : lever une erreur au démarrage si `SECRET_KEY` est absente, plutôt que d'utiliser un défaut.

### 3. Le collecteur exécute du code tiré de GitHub à chaque démarrage
**Fichier** : `docker-entrypoint.sh:17-22` → `git reset --hard origin/main` puis `python main.py`

Le conteneur ne contient pas son propre code — il **clone `main` à chaque boot** sans pin de commit. Risque chaîne d'approvisionnement : un push malveillant (ou un compromis du dépôt) = exécution de code arbitraire en prod.

**Correctif** : embarquer le code dans l'image (`COPY . .`, comme `Dockerfile.api`) et figer un tag/commit.

---

## 🟠 Sécurité — Élevé

### 4. PostgreSQL exposé sur l'hôte avec mot de passe faible
**Fichier** : `docker-compose.yml:10-11` expose `5432:5432`, avec `POSTGRES_PASSWORD=ao_password_fbvrd`.

La base est joignable depuis l'extérieur de Docker avec un mot de passe trivial.

**Correctif** : supprimer le mapping de port (les autres services accèdent via le réseau interne `db:5432`) et durcir le mot de passe.

### 5. Aucune limitation de débit sur `/auth/login`
**Fichier** : `api/routes/auth.py:21` — pas de rate-limiting → **brute-force possible**.

**Correctif** : ajouter un limiteur (ex. `slowapi`) et éventuellement un verrouillage temporaire après N échecs.

### 6. Pas de HTTPS / TLS
**Fichier** : `frontend/nginx.conf:2` n'écoute qu'en `:80`. Mots de passe et JWT transitent **en clair**.

**Correctif** : reverse-proxy TLS (Caddy/Traefik) ou certificat sur nginx.

### 7. CORS permissif par défaut
**Fichier** : `api/main.py:22-27` → `allow_origins=os.getenv("CORS_ORIGINS","*")` + `allow_credentials=True` + méthodes/headers `*`.

Si la variable est oubliée, on retombe sur `*`. Ne jamais combiner `*` avec `allow_credentials`.

**Correctif** : restreindre explicitement les origines autorisées.

---

## 🟡 Sécurité — Moyen

- **Token en `localStorage`** (`frontend/src/api/client.js:9`) : vulnérable au vol par XSS. Pas de XSS aujourd'hui (React échappe tout, aucun `dangerouslySetInnerHTML`), mais un cookie `HttpOnly` serait plus sûr.
- **`/docs` et `/openapi.json` exposés** par défaut (FastAPI) : à désactiver en prod (`docs_url=None`).
- **`get_admin_user`** (`api/deps.py:49`) est défini mais **jamais utilisé** : la distinction admin/utilisateur n'est appliquée nulle part. À brancher ou retirer.
- ✅ **Pas d'injection SQL** : tout passe par des requêtes paramétrées SQLAlchemy (le `ilike(f"%{search}%")` ne construit que la *valeur* du paramètre, qui reste bindée — c'est sûr).

---

## 🛠️ Qualité du code

### Bugs / API obsolètes
- **`@app.on_event("startup")`** (`api/main.py:34`) est déprécié et supprimé dans les FastAPI récents → migrer vers `lifespan`.
- **`datetime.utcnow()`** déprécié en Python 3.12 (utilisé partout : `processor/scorer.py`, `scheduler/jobs.py:35`, collecteurs, `models/tender.py:62`) → `datetime.now(timezone.utc)`.
- **`keepPreviousData`** (`frontend/src/pages/Tenders.jsx:45`) n'existe plus en react-query v5 → `placeholderData: keepPreviousData`.
- **Filtre sources cassé** : si l'utilisateur **désélectionne toutes** les sources, le front envoie `undefined` (`Tenders.jsx:43`) → l'API renvoie **toutes** les sources au lieu d'aucune.
- **`DATABASE_URL` avec `${...}` dans le `.env`** : les variables type `${POSTGRES_USER}`/`${POSTGRES_PASSWORD}` **ne sont pas interpolées** quand le fichier est injecté via `env_file:` (Docker Compose ne fait l'expansion que dans le `docker-compose.yml`, pas dans `env_file`). Résultat : connexion BDD avec des identifiants littéraux `${...}` → `password authentication failed`. **Contournement actuel** : `DATABASE_URL` écrite en dur dans le `.env`, ce qui duplique le mot de passe. **Correctif propre** : définir `DATABASE_URL` dans `docker-compose.yml` (`environment:`) avec `${POSTGRES_USER}`/`${POSTGRES_PASSWORD}` — là l'interpolation Compose fonctionne et il n'y a plus qu'une seule source de vérité pour le mot de passe.

### Duplication
- Les libellés/couleurs des sources sont **réécrits 3 fois** (`TenderCard.jsx:4`, `TenderDetail.jsx:128`, `Tenders.jsx:16`) + côté backend `schemas.py:39`. À centraliser dans un seul module.
- Deux dépendances de session BDD identiques : `get_db` (`api/deps.py:20`) et `get_session` (`storage/database.py:99`).

### Dépendances / outillage
- `requirements.txt:2` : `pydantic` listé en double, et **`passlib==1.7.4`** n'est plus maintenu (incompatibilités connues avec `bcrypt>=4.1`). Migrer vers `bcrypt` directement ou `argon2`.
- **Alembic est installé mais inutilisé** : le schéma est créé via `create_all` (`storage/database.py:93`). Toute évolution de colonne ne sera **pas migrée** sur une base existante.
- **Aucun test** alors que `pytest`/`pytest-asyncio` sont en dépendances.

### Performance
- `storage/repository.py` (méthode `upsert`) fait **un commit + 2 SELECT par AO** → lent sur de gros volumes. Regrouper en transaction par lot.

### Robustesse des collecteurs
- Les scrapers Playwright (`collector/demat_ampa.py`, `collector/e_marches_publics.py`, `collector/vilogia.py`) reposent sur des sélecteurs DOM / un parsing positionnel fragiles — ils casseront au moindre changement de site.
- `collector/e_marches_publics.py` met la **même URL générique** pour tous les AO → lien inexploitable.
- `collector/boamp.py:217` : le hack `fmt[:len(value[:19])]` pour parser les dates est obscur et fragile.

---

## ✅ Points positifs

- Architecture en couches claire (collector / processor / storage / api / scheduler), facile à étendre via le `registry`.
- Mots de passe hachés (bcrypt), JWT correctement vérifié, déduplication inter-sources par *fingerprint* bien pensée.
- Frontend sans faille XSS (rendu échappé), bonne séparation des responsabilités.
- `.env` correctement exclu de Git (seul `.env.example` est suivi).

---

## Checklist de remédiation

### Sécurité
- [ ] Régénérer `SECRET_KEY` (aléatoire fort)
- [ ] Faire échouer le démarrage si `SECRET_KEY` absente (supprimer le défaut)
- [ ] Embarquer le code dans l'image Docker (supprimer le `git pull` runtime)
- [ ] Fermer le port `5432` + mot de passe Postgres fort
- [ ] Rate-limiting sur `/auth/login`
- [ ] Activer TLS/HTTPS
- [ ] Restreindre CORS (origines explicites)
- [ ] Désactiver `/docs` en prod
- [ ] Brancher ou retirer `get_admin_user`
- [ ] Envisager un cookie `HttpOnly` à la place de `localStorage`

### Qualité
- [ ] Migrer `on_event` → `lifespan`
- [ ] Remplacer `datetime.utcnow()` → `datetime.now(timezone.utc)`
- [ ] Corriger `keepPreviousData` (react-query v5)
- [ ] Corriger le filtre « toutes sources désélectionnées »
- [ ] Déplacer `DATABASE_URL` du `.env` vers `docker-compose.yml` (interpolation `${...}` + une seule source de vérité pour le mot de passe)
- [ ] Centraliser les libellés/couleurs des sources
- [ ] Dédupliquer `get_db` / `get_session`
- [ ] Nettoyer `requirements.txt` (pydantic en double) + remplacer passlib
- [ ] Mettre en place des migrations Alembic réelles
- [ ] Ajouter des tests
- [ ] Optimiser `upsert` (transaction par lot)
- [ ] Fiabiliser le parsing des dates BOAMP
