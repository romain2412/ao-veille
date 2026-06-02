<#
.SYNOPSIS
    Déploiement LOCAL de ao-veille (sans HTTPS/Caddy), pour tester avant la prod.

.DESCRIPTION
    Reconstruit les images et (re)démarre la stack en local via Docker Desktop,
    en utilisant la surcharge docker-compose.local.yml :
      - frontend exposé sur http://localhost:8080
      - Caddy désactivé (pas de certificat en local)
    Les migrations Alembic sont appliquées au démarrage du collector.

.EXAMPLE
    .\deploy-local.ps1
    Build + démarrage. App sur http://localhost:8080

.EXAMPLE
    .\deploy-local.ps1 -Down
    Arrête la stack locale (sans supprimer les données).
#>

[CmdletBinding()]
param(
    # Arrête la stack au lieu de la démarrer
    [switch] $Down,
    # Port local d'exposition du frontend (défaut 8080)
    [int] $Port = 8080
)

# NB : docker compose écrit sa progression sur stderr ; on n'active donc PAS
# "Stop" globalement (sinon PowerShell prendrait ces lignes pour des erreurs).
$ErrorActionPreference = "Continue"

# Se placer dans le dossier du script (racine du projet)
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

$composeArgs = @("-f", "docker-compose.yml", "-f", "docker-compose.local.yml")

if ($Down) {
    Write-Host "==> Arrêt de la stack locale..." -ForegroundColor Cyan
    docker compose @composeArgs down
    Write-Host "==> Stack arrêtée (données conservées)." -ForegroundColor Green
    return
}

# Vérifs de base
if (-not (Test-Path "$ProjectDir\.env")) {
    Write-Host "Fichier .env absent. Copie .env.example en .env et renseigne SECRET_KEY." -ForegroundColor Red
    exit 1
}

$env:FRONTEND_PORT = "$Port"

# docker compose écrit sa progression sur stderr ; on fusionne stderr->stdout
# (2>&1) pour que PowerShell ne les remonte pas comme des erreurs.
Write-Host "==> Build des images..." -ForegroundColor Cyan
docker compose @composeArgs build 2>&1 | ForEach-Object { "$_" }

Write-Host "==> (Re)démarrage des conteneurs..." -ForegroundColor Cyan
docker compose @composeArgs up -d 2>&1 | ForEach-Object { "$_" }

Write-Host "==> État des services :" -ForegroundColor Cyan
docker compose @composeArgs ps 2>&1 | ForEach-Object { "$_" }

Write-Host ""
Write-Host "==> Déploiement local terminé." -ForegroundColor Green
Write-Host "    Frontend : http://localhost:$Port" -ForegroundColor Yellow
Write-Host "    API health : http://localhost:$Port/api/health" -ForegroundColor Yellow
