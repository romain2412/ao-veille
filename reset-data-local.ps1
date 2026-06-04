<#
.SYNOPSIS
    Vide les tables de donnees de la base LOCALE (Docker Desktop).
.DESCRIPTION
    Conserve : users, alembic_version, invitations.
    Vide     : tenders, collection_runs, collection_requests, app_state.
    Demande une confirmation avant d'agir.
.EXAMPLE
    .\reset-data-local.ps1
#>

[CmdletBinding()]
param(
    [string] $DbContainer = "ao-veille-db-1",
    [string] $DbUser = "ao_user",
    [string] $DbName = "ao_veille",
    [switch] $Force   # saute la confirmation interactive
)

$ErrorActionPreference = "Continue"

# Tables a vider (donnees metier), separees par des virgules pour TRUNCATE
$tables = "tenders, collection_runs, collection_requests, app_state"

$countSql = "select 'tenders' as t, count(*) from tenders union all select 'collection_runs', count(*) from collection_runs union all select 'collection_requests', count(*) from collection_requests union all select 'app_state', count(*) from app_state union all select 'users_conserve', count(*) from users union all select 'invitations_conserve', count(*) from invitations;"

Write-Host "=== Reset des donnees LOCALES - base $DbName ===" -ForegroundColor Cyan
Write-Host "  Tables videes    : $tables"
Write-Host "  Tables conservees: users, alembic_version, invitations"
Write-Host "Comptage actuel :"
docker exec $DbContainer psql -U $DbUser -d $DbName -P pager=off -c $countSql

Write-Host ""
if (-not $Force) {
    $confirm = Read-Host "Taper VIDER pour confirmer le vidage local"
    if ($confirm -ne "VIDER") {
        Write-Host "Annule." -ForegroundColor Yellow
        return
    }
}

Write-Host "==> Vidage des tables..." -ForegroundColor Cyan
$truncate = "TRUNCATE TABLE $tables RESTART IDENTITY;"
docker exec $DbContainer psql -U $DbUser -d $DbName -c $truncate

Write-Host "==> Termine. Comptage apres :" -ForegroundColor Green
docker exec $DbContainer psql -U $DbUser -d $DbName -P pager=off -c $countSql
