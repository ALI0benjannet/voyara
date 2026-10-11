# Arrete tous les microservices Voyara demarres par dev.ps1
# (tue les processus qui ecoutent sur les ports 8000-8007)

$ports = 8000..8007
$stopped = 0

foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        try {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction Stop
            Write-Host "Port $port : processus $($conn.OwningProcess) arrete"
            $stopped++
        } catch {}
    }
}

Write-Host "$stopped processus arretes." -ForegroundColor Green
