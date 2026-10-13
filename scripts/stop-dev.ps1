# Arrete tous les microservices Voyara demarres par dev.ps1
# (tue les processus qui ecoutent sur les ports 8000-8007)
#
# Avec --reload, uvicorn lance un reloader + un worker enfant
# (multiprocessing spawn_main(parent_pid=...)) qui herite du socket. Tuer le seul
# PID en ecoute laisse ce worker orphelin servir l'ancien code : on tue donc
# l'arbre complet, plus les workers dont le parent est deja mort.

$ports = 8000..8007
$stopped = 0

function Stop-Tree([int]$procId) {
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$procId" -ErrorAction SilentlyContinue
    foreach ($child in $children) { Stop-Tree $child.ProcessId }
    # Workers spawn orphelins : leur ligne de commande garde le PID du parent
    $orphans = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "spawn_main\(parent_pid=$procId\b" }
    foreach ($orphan in $orphans) { Stop-Tree $orphan.ProcessId }
    try {
        Stop-Process -Id $procId -Force -ErrorAction Stop
        $script:stopped++
    } catch {}
}

# Plusieurs generations peuvent partager un port et Windows n'en montre qu'une
# a la fois : on repasse tant qu'un port reste en ecoute (5 passes max).
for ($pass = 1; $pass -le 5; $pass++) {
  $busy = $false
  foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in ($connections | Select-Object -ExpandProperty OwningProcess -Unique)) {
        $busy = $true
        # Remonte au reloader uvicorn pour couper l'arbre entier
        $root = $conn
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$conn" -ErrorAction SilentlyContinue
        if ($proc -and $proc.CommandLine -match 'uvicorn') {
            $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)" -ErrorAction SilentlyContinue
            if ($parent -and $parent.CommandLine -match 'uvicorn') { $root = $parent.ProcessId }
        }
        Stop-Tree $root
        Write-Host "Port $port : processus $root arrete"
    }
  }
  if (-not $busy) { break }
  Start-Sleep -Milliseconds 500
}

Write-Host "$stopped processus arretes." -ForegroundColor Green

# Base du moteur IA demarree par dev.ps1 : arretee, les donnees restent dans le
# volume voyara_pgdata_ai. Le Postgres principal (5434) n'est pas touche.
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Push-Location (Split-Path -Parent $PSScriptRoot)
    $conteneur = docker compose ps -q postgres-ai 2>$null
    if ($conteneur) {
        docker compose stop postgres-ai 2>$null | Out-Null
        Write-Host "postgres-ai arrete (donnees conservees)." -ForegroundColor Green
    }
    Pop-Location
}
