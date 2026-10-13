# ==========================================================================
# Demarre tous les microservices Voyara en local (sans Docker pour les
# services ; la base Postgres peut etre le conteneur `docker compose up -d postgres`).
#
#   .\scripts\dev.ps1            # demarre tout
#   .\scripts\dev.ps1 -Seed      # + cree l'admin initial
#
# Prerequis :
#   python -m venv .venv
#   .venv\Scripts\pip install -r requirements-dev.txt
#   .venv\Scripts\pip install -e libs/common
# ==========================================================================

param([switch]$Seed)

$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Py)) {
    Write-Host "Venv introuvable ($Py). Creez-le d'abord (voir README)." -ForegroundColor Red
    exit 1
}

Write-Host "1) Verification/creation des bases de donnees..." -ForegroundColor Cyan
& $Py (Join-Path $Root "scripts\create_databases.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host "PostgreSQL injoignable. Demarrez-le puis relancez (ex: docker compose up -d postgres)." -ForegroundColor Red
    exit 1
}

Write-Host "1b) Base du moteur IA (conteneur postgres-ai, port 5435)..." -ForegroundColor Cyan
# Non bloquant : sans Docker, les 7 services et le gateway demarrent quand meme.
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "   Docker introuvable : postgres-ai non demarre (moteur IA indisponible)." -ForegroundColor Yellow
} else {
    Push-Location $Root
    docker compose up -d postgres-ai 2>$null | Out-Null
    $etat = ""
    if ($LASTEXITCODE -eq 0) {
        $conteneur = docker compose ps -q postgres-ai
        for ($i = 0; $i -lt 15; $i++) {
            $etat = docker inspect -f "{{.State.Health.Status}}" $conteneur 2>$null
            if ($etat -eq "healthy") { break }
            Start-Sleep -Seconds 2
        }
    }
    Pop-Location
    if ($etat -eq "healthy") {
        Write-Host "   postgres-ai pret (voyara_ai sur localhost:5435)"
    } else {
        Write-Host "   postgres-ai non pret (Docker Desktop demarre ?) : moteur IA indisponible." -ForegroundColor Yellow
    }
}

if ($Seed) {
    Write-Host "2) Seed du compte admin..." -ForegroundColor Cyan
    Push-Location (Join-Path $Root "services\auth")
    & $Py "scripts\seed_admin.py"
    Pop-Location
}

$services = @(
    @{ Name = "auth";         Dir = "services\auth";         Port = 8001 },
    @{ Name = "catalog";      Dir = "services\catalog";      Port = 8002 },
    @{ Name = "booking";      Dir = "services\booking";      Port = 8003 },
    @{ Name = "payment";      Dir = "services\payment";      Port = 8004 },
    @{ Name = "review";       Dir = "services\review";       Port = 8005 },
    @{ Name = "notification"; Dir = "services\notification"; Port = 8006 },
    @{ Name = "admin";        Dir = "services\admin";        Port = 8007 },
    @{ Name = "gateway";      Dir = "gateway";               Port = 8000 }
)

Write-Host "3) Demarrage des services..." -ForegroundColor Cyan
foreach ($svc in $services) {
    $dir = Join-Path $Root $svc.Dir
    Start-Process -WindowStyle Minimized -WorkingDirectory $dir -FilePath $Py `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--port", $svc.Port, "--reload" `
    | Out-Null
    Write-Host ("   {0,-14} http://localhost:{1}" -f $svc.Name, $svc.Port)
}

Write-Host ""
Write-Host "Gateway  : http://localhost:8000         (point d'entree unique)" -ForegroundColor Green
Write-Host "Sante    : http://localhost:8000/health  (etat de tous les services)" -ForegroundColor Green
Write-Host "Frontends: cd frontend; npm run dev      (client :5173 + admin :5174/admin)" -ForegroundColor Green
Write-Host ""
Write-Host "Arret : .\scripts\stop-dev.ps1" -ForegroundColor Yellow
