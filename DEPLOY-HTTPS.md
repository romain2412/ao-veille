# Mise en place du HTTPS (Caddy) — procédure

Procédure à exécuter **une seule fois** sur le serveur de prod pour activer le
HTTPS sur `https://ao.veille.fbvrd-tools.fr`.

- **Serveur** : `212.227.75.168` — dossier `/opt/ao-veille`
- **Domaine** : `ao.veille.fbvrd-tools.fr`
- Mécanisme : un service **Caddy** (reverse-proxy) obtient et renouvelle
  automatiquement un certificat Let's Encrypt.

---

## Prérequis (déjà validés)

- [x] DNS : `ao.veille.fbvrd-tools.fr` → `212.227.75.168` (enregistrement A)
- [x] Port 80 ouvert (le site répond déjà en http)
- [x] Pare-feu `ufw` inactif → le port 443 est donc joignable
- [x] Code poussé sur `main` (service `caddy` + `Caddyfile`)

---

## Procédure

### 1. Récupérer le code à jour

```bash
cd /opt/ao-veille
git pull --ff-only
```

Vérifier que le `Caddyfile` est bien présent :

```bash
cat Caddyfile        # doit afficher le bloc "ao.veille.fbvrd-tools.fr { reverse_proxy frontend:80 }"
```

### 2. Mettre à jour `CORS_ORIGINS` dans le `.env`

L'origine devient `https://...` (et non plus `http://212.227.75.168`).
Éditer `/opt/ao-veille/.env` et remplacer la ligne `CORS_ORIGINS` par :

```ini
CORS_ORIGINS=https://ao.veille.fbvrd-tools.fr
```

(Optionnel — pour pouvoir continuer à accéder en direct par l'IP, on peut
mettre plusieurs origines séparées par une virgule :
`CORS_ORIGINS=https://ao.veille.fbvrd-tools.fr,http://212.227.75.168`)

### 3. Déployer

```bash
./deploy.sh
# ou si "Permission denied" :  sh deploy.sh
```

Cela démarre le service **caddy** (ports 80 + 443) et retire le port 80 du
frontend (désormais derrière Caddy).

> ⚠️ Bref instant de coupure (quelques secondes) pendant la bascule du port 80
> du frontend vers Caddy. Sans gravité.

### 4. Vérifier l'obtention du certificat

```bash
# Logs de Caddy : on doit voir "certificate obtained successfully"
docker compose logs caddy | grep -iE "certificate|obtain|error" | tail -20

# Tous les services up (caddy expose 80 + 443)
docker compose ps
```

### 5. Tester le HTTPS

Depuis le serveur ou ton PC :

```bash
curl -I https://ao.veille.fbvrd-tools.fr        # doit répondre HTTP/2 200
curl -I http://ao.veille.fbvrd-tools.fr         # doit rediriger (308) vers https
```

Puis dans le navigateur : **https://ao.veille.fbvrd-tools.fr** → cadenas 🔒,
et `http://...` doit basculer automatiquement en `https://...`.

---

## En cas de souci

**Le certificat n'est pas obtenu** (`docker compose logs caddy` montre une erreur) :
- Vérifier que le DNS pointe bien : `nslookup ao.veille.fbvrd-tools.fr`
- Vérifier que le port 443 est ouvert (aucun pare-feu ne le bloque)
- Caddy réessaie automatiquement ; relancer au besoin : `docker compose restart caddy`

**Le site s'affiche mais les données ne chargent pas** (erreur CORS dans la
console du navigateur, F12) :
- Vérifier que `CORS_ORIGINS=https://ao.veille.fbvrd-tools.fr` dans le `.env`
- `docker compose up -d` pour reprendre en compte le `.env`

**Erreur de quota Let's Encrypt** (si plusieurs essais répétés) :
- Attendre quelques heures (limite de certificats par semaine), ou tester
  d'abord avec le serveur de staging Let's Encrypt. Ne PAS supprimer le volume
  `caddy_data` (il conserve les certificats déjà obtenus).

---

## Après la mise en place

- Les déploiements suivants restent identiques : `./deploy.sh`.
- Caddy **renouvelle le certificat tout seul** (avant les 90 jours). Rien à faire.
- Le volume `caddy_data` contient les certificats : **ne pas le supprimer**.
- Penser à mettre à jour les liens / favoris vers la nouvelle URL `https://`.
