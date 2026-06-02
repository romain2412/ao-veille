# Déploiement — ao-veille

Guide de déploiement de l'application sur le serveur de production.

- **Serveur** : `212.227.75.168`
- **Dossier projet** : `/opt/ao-veille`
- **Orchestration** : Docker Compose

---

## 1. Architecture des conteneurs

La stack est composée de 4 services (cf. `docker-compose.yml`) :

| Service | Rôle | Image / build | Données |
|---------|------|---------------|---------|
| `caddy` | Reverse-proxy + HTTPS auto (Let's Encrypt) | `caddy:2-alpine` | volumes `caddy_data` (certificats) / `caddy_config` |
| `db` | PostgreSQL 16 | `postgres:16-alpine` | volume `pgdata` (persistant) |
| `collector` | Collecte + scoring des AO, applique les migrations | `Dockerfile.collector` | — |
| `api` | API FastAPI (consultation) | `Dockerfile.api` | — |
| `frontend` | Portail web (React + nginx) | `frontend/Dockerfile` | — |

Chaîne des requêtes en production :

```
Navigateur ─https(443)─► caddy ─► frontend (nginx) ─► api
                         (TLS)     (sert React + route /api)
```

- **Caddy** est la seule porte d'entrée (ports 80 et 443). Il termine le TLS et
  gère les certificats automatiquement. Le `frontend` n'expose plus de port sur
  l'hôte (il n'est joignable que par Caddy via le réseau interne).
- Le domaine `ao.veille.fbvrd-tools.fr` doit pointer (DNS A) vers le serveur, et
  les ports **80 et 443** doivent être ouverts (Let's Encrypt vérifie via le 80).
- ⚠️ Le volume `caddy_data` contient les certificats : ne pas le supprimer
  (sinon Caddy redemande un certificat à chaque fois → risque de quota
  Let's Encrypt si répété).

Points clés :

- **Le code est embarqué dans les images** (`COPY . /app`). Plus de clone GitHub
  au runtime : pour livrer du code, on reconstruit les images.
- **La base PostgreSQL n'est PAS exposée sur l'hôte** : elle n'est joignable que
  par les autres conteneurs via le réseau interne Docker (`db:5432`).
- **Les données vivent dans le volume `pgdata`**, indépendant des conteneurs.
  Détruire/recréer un conteneur ne perd aucune donnée.
- **Le `.env` n'est pas versionné** (il est dans `.gitignore`) : un `git pull`
  ne l'écrase jamais. Seul `.env.example` (modèle sans secrets) est suivi.

---

## 2. Le schéma de base (Alembic)

Le schéma est géré par des **migrations Alembic versionnées** (plus de
`create_all`). Les migrations sont appliquées **automatiquement au démarrage du
collecteur** (`docker-entrypoint.sh` → `alembic upgrade head`).

- **Base vierge** (nouvelle installation) : `alembic upgrade head` crée tout.
- **Base existante déjà peuplée** : il faut adopter la baseline UNE SEULE FOIS
  avec `alembic stamp head` (voir étape 3), sinon Alembic tenterait de recréer
  des tables qui existent déjà.

---

## 3. Le script `deploy.sh`

Le déploiement courant tient en une commande : `./deploy.sh`. Il enchaîne :

```sh
git pull --ff-only            # 1. récupère le code à jour depuis GitHub
docker compose up -d --build  # 2. reconstruit les images et recrée les conteneurs
docker compose ps             # 3. affiche l'état des services
docker image prune -f         # 4. supprime les images orphelines (nettoyage disque)
```

### Que fait `docker compose up -d --build` exactement ?

Pour **chaque** service, Compose compare l'état voulu à l'état courant :

- Si l'image a changé (rebuild) ou la config diffère → il **arrête, supprime et
  recrée** le conteneur (même nom, ex. `ao-veille-collector-1`). Il n'y a jamais
  deux versions d'un même service en parallèle.
- Si rien n'a changé pour un service → il **laisse le conteneur tourner** tel
  quel (pas d'interruption inutile).

Le volume `pgdata` n'est jamais touché → **les données sont conservées** à
chaque déploiement.

> ⚠️ Ne JAMAIS utiliser `docker compose down -v` : le `-v` supprimerait le
> volume `pgdata` et donc toutes les données collectées.

---

## 4. Procédure de déploiement

### Cas A — Déploiement courant (mise à jour de code)

Une fois la première mise en service faite (cas B ci-dessous), tout déploiement
se résume à :

```bash
cd /opt/ao-veille
./deploy.sh
```

### Cas B — Première mise en service (ou migration vers cette nouvelle version)

À ne faire qu'une fois. Étapes 1 → 5 :

#### Étape 1 — Générer les secrets

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # → SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(24))"   # → mot de passe Postgres (optionnel)
```

#### Étape 2 — Configurer le `.env`

Éditer `/opt/ao-veille/.env` :

```ini
SECRET_KEY=<la clé de 64 caractères générée à l'étape 1>
COLLECT_START_SOURCES=aquitanis
CORS_ORIGINS=https://ao.veille.fbvrd-tools.fr
```

> Depuis le passage en HTTPS, l'origine est `https://ao.veille.fbvrd-tools.fr`
> (et non plus `http://212.227.75.168`). `CORS_ORIGINS` doit refléter cette URL.

> ⚠️ `SECRET_KEY` est **obligatoire** : l'application refuse de démarrer si elle
> est absente ou commence par `changeme`. Changer la `SECRET_KEY` déconnecte les
> utilisateurs (les anciens jetons JWT deviennent invalides) — c'est normal.

Pour changer le mot de passe Postgres (optionnel) : la base existe déjà, donc
modifier `POSTGRES_PASSWORD` dans le `.env` ne suffit pas. Il faut le changer
**dans Postgres ET dans le `.env` en même temps** :

```bash
docker compose exec db psql -U ao_user -d ao_veille \
  -c "ALTER USER ao_user WITH PASSWORD 'NOUVEAU_MOT_DE_PASSE';"
```

Puis mettre à jour `POSTGRES_PASSWORD` **et** `DATABASE_URL` dans le `.env`.

#### Étape 3 — Adopter Alembic sur la base existante (UNE seule fois)

> À faire uniquement si la base contient déjà les tables (cas du serveur actuel).
> Sur une base totalement vierge, sauter cette étape : `deploy.sh` créera tout.

```bash
cd /opt/ao-veille
git pull --ff-only
docker compose run --rm collector alembic stamp head
```

#### Étape 4 — Déployer

```bash
./deploy.sh
```

#### Étape 5 — Vérifier

```bash
docker compose ps                                   # tous les services "Up" / db "healthy"
curl -s localhost/api/health                        # doit répondre {"status":"ok"}
docker compose logs collector | grep -i aquitanis   # voir la collecte Aquitanis
```

Vérifier aussi en base le nombre d'AO par source :

```bash
docker compose exec db psql -U ao_user -d ao_veille \
  -c "select source, count(*) from tenders group by source order by source;"
```

---

## 5. Commandes utiles (exploitation)

```bash
# Logs en direct d'un service
docker compose logs -f collector

# Lancer une collecte ponctuelle d'une source précise (sans attendre le scheduler)
docker compose exec collector python /app/main.py --once --start-sources aquitanis

# État des migrations
docker compose exec collector alembic current

# Redémarrer un seul service
docker compose restart api
```

---

## 6. Rate-limiting (anti brute-force sur le login)

L'endpoint `POST /auth/login` est limité à **5 tentatives par minute et par IP**
(via [slowapi](https://github.com/laurentS/slowapi)). Au-delà, l'API répond
`429 Too Many Requests`. Cela protège contre les attaques par force brute sur les
mots de passe.

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `api/rate_limit.py` | crée le `limiter` partagé + fonction `client_ip` (lit l'IP réelle) |
| `api/main.py` | branche le `limiter` sur l'app + handler de réponse `429` |
| `api/routes/auth.py` | décorateur `@limiter.limit("5/minute")` sur `/auth/login` |
| `frontend/nginx.conf` | transmet l'en-tête `X-Forwarded-For` à l'API |

### Identification par IP réelle (derrière les proxies)

L'app tourne derrière deux reverse-proxies (`caddy → nginx`). L'IP de connexion
vue par l'API est donc celle du proxy, pas celle du visiteur. Pour compter par
**IP réelle**, on lit l'en-tête `X-Forwarded-For` :

- **Caddy** ajoute `X-Forwarded-For` automatiquement (en tête de chaîne).
- **nginx** le transmet (`proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for`).
- **slowapi** (`api/rate_limit.py` → `client_ip`) prend la 1ʳᵉ IP de l'en-tête.

> ⚠️ **Sécurité — pourquoi on peut faire confiance à `X-Forwarded-For` ici.**
> Cet en-tête est du texte, donc falsifiable par un client. S'y fier serait
> dangereux si l'API était joignable directement : un attaquant changerait d'IP
> à chaque requête pour contourner la limite.
> C'est sûr dans **notre** cas **uniquement** parce que l'API n'est **jamais**
> exposée sur Internet (réseau Docker interne, aucun port public ; seul Caddy a
> un port ouvert). Toute requête passe donc forcément par Caddy, qui voit la
> vraie IP de la connexion TCP (non falsifiable) et écrase tout en-tête
> `X-Forwarded-For` envoyé par le client.
> **Corollaire : ne jamais exposer directement le port de l'API (`api`) ni de
> nginx (`frontend`) sur l'hôte** — cela casserait cette garantie.

### Ajuster la limite

Modifier la valeur dans `api/routes/auth.py` (ex. `"3/minute"`, `"10/minute"`),
puis redéployer (`./deploy.sh`). Aucune migration ni changement de `.env`.

---

## 7. Déploiement local (test avant prod)

Pour tester la stack sur sa machine (Docker Desktop) avant de pousser en prod,
on utilise une **surcharge** qui désactive Caddy/HTTPS et expose le frontend
directement sur `localhost`.

| Fichier | Rôle |
|---------|------|
| `docker-compose.local.yml` | surcharge locale : frontend sur `localhost:8080`, Caddy neutralisé |
| `deploy-local.ps1` | script PowerShell de déploiement local |

### Utilisation (PowerShell)

```powershell
.\deploy-local.ps1              # build + démarrage → http://localhost:8080
.\deploy-local.ps1 -Port 3000  # exposer sur un autre port
.\deploy-local.ps1 -Down       # arrêter la stack (données conservées)
```

L'app est alors sur **http://localhost:8080** (API en same-origin sous `/api`).

### Équivalent en ligne de commande

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

### Différences avec la prod

- **Pas de HTTPS/Caddy** : Caddy exigerait un certificat Let's Encrypt pour le
  vrai domaine, impossible en local → le service `caddy` est neutralisé.
- **frontend exposé** sur `localhost:8080` (en prod il n'a aucun port public).
- Tout le reste est **identique à la prod** : mêmes images, mêmes migrations
  Alembic au démarrage, même rate-limiting. C'est donc un test fidèle.

> En local, le rate-limiting comptera par IP directe (pas de chaîne de proxies),
> ce qui est sans importance pour un test fonctionnel.

---

## 8. Notes

- **`COLLECT_START_SOURCES`** ne pilote que la collecte **au démarrage** du
  collecteur. Le scheduler collecte de toute façon **toutes** les sources toutes
  les 12 h. En fonctionnement normal, on peut laisser cette variable vide.
- Sources disponibles : `boamp`, `demat_ampa`, `e_marches_publics`, `noalis`,
  `vilogia`, `aquitanis`.
