# ============================================================================
# dev-tunnels.ps1
# ============================================================================
# Назначение: ручной kubectl port-forward к Postgres и ClickHouse в k8s
#             для локальной разработки (без LoadBalancer наружу).
# Запуск:     .\scripts\dev-tunnels.ps1
# Env:        DEV_TUNNELS_KUBECONFIG — путь к kubeconfig (опционально)
# ============================================================================

$ErrorActionPreference = "Stop"

# Скрипт лежит в scripts/ — корень репозитория на уровень выше
$repoRoot = Split-Path -Parent $PSScriptRoot

$defaultKubeconfig = Join-Path $repoRoot "k8s\new-cluster\new-cluster-config.yaml"
$kubeconfig = if (-not [string]::IsNullOrWhiteSpace($env:DEV_TUNNELS_KUBECONFIG)) {
    $env:DEV_TUNNELS_KUBECONFIG
} else {
    $defaultKubeconfig
}

if (-not (Test-Path $kubeconfig)) {
    throw "Kubeconfig not found: $kubeconfig. Set DEV_TUNNELS_KUBECONFIG to override."
}

$env:KUBECONFIG = $kubeconfig

Write-Host "KUBECONFIG=$kubeconfig"
kubectl config current-context

Write-Host ""
# По умолчанию локальный PG идёт через PgBouncer (session mode)
$pgResource = if ($env:DEV_TUNNEL_PG_RESOURCE) { $env:DEV_TUNNEL_PG_RESOURCE } else { "svc/postgres-db-pooler" }

function Test-TcpPortOpen {
    param([int]$Port)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $asyncResult = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $asyncResult.AsyncWaitHandle.WaitOne(250)) {
            $client.Close()
            return $false
        }
        $client.EndConnect($asyncResult)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Invoke-PostgresSmokeCheck {
    param(
        [int]$Port = 15432,
        [int]$TimeoutSec = 20
    )

    if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
        Write-Host "PG smoke check skipped: psql not found in PATH."
        return
    }

    $pgUser = $env:POSTGRES_USER
    $pgDb = if ($env:POSTGRES_DBNAME) { $env:POSTGRES_DBNAME } else { "postgres" }
    if (-not $pgUser) {
        Write-Host "PG smoke check skipped: set POSTGRES_USER (and optionally POSTGRES_DBNAME/POSTGRES_PASSWORD)."
        return
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-TcpPortOpen -Port $Port) { break }
        Start-Sleep -Milliseconds 500
    }
    if (-not (Test-TcpPortOpen -Port $Port)) {
        Write-Host "PG smoke check skipped: 127.0.0.1:$Port is not listening yet."
        return
    }

    if ($env:POSTGRES_PASSWORD) {
        $env:PGPASSWORD = $env:POSTGRES_PASSWORD
    }

    $smokeOutput = & psql -h 127.0.0.1 -p $Port -U $pgUser -d $pgDb -t -A -c "SELECT 1;" 2>&1
    if ($LASTEXITCODE -eq 0 -and (($smokeOutput -join "`n") -match "1")) {
        Write-Host "PG smoke check OK: SELECT 1 via 127.0.0.1:$Port ($pgResource)."
        return
    }

    Write-Host "PG smoke check FAILED: SELECT 1 via 127.0.0.1:$Port ($pgResource)."
    if ($smokeOutput) {
        Write-Host ($smokeOutput | Select-Object -First 3)
    }
}

if (Test-TcpPortOpen -Port 15432) {
    Write-Host "Postgres tunnel already active on 127.0.0.1:15432, reusing existing forward."
} else {
    Write-Host "Starting Postgres tunnel (PgBouncer session mode): localhost:15432 -> ${pgResource}:5432"
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "`$env:KUBECONFIG='$kubeconfig'; kubectl port-forward -n prod-adv-bot $pgResource 15432:5432"
    )
}

Write-Host "Starting ClickHouse tunnel: localhost:18123 -> ClickHouse HTTP"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$env:KUBECONFIG='$kubeconfig'; kubectl port-forward -n prod-analytics svc/chi-clickhouse-main-0-0 18123:8123"
)

Write-Host ""
Write-Host "Tunnels started in separate PowerShell windows."
Write-Host "PG:        127.0.0.1:15432"
Write-Host "PG mode:   PgBouncer session mode (prod-adv-bot/${pgResource})"
Write-Host "CH HTTP:   127.0.0.1:18123"
Write-Host "CH Native: 127.0.0.1:19000"
Write-Host "PG resource: ${pgResource}"
Write-Host "Fallback for emergency direct PG: DEV_TUNNEL_PG_RESOURCE=pod/postgres-db-0 (not default)"
Write-Host ""
Write-Host "Set in .env (RUN_LOCAL=false if using this script only):"
Write-Host "  POSTGRES_MASTER_HOST=127.0.0.1"
Write-Host "  POSTGRES_REPLICA_HOST=127.0.0.1"
Write-Host "  POSTGRES_PORT=15432"
Write-Host "  POSTGRES_SSL_MODE=require"
Write-Host "  PG_POOL_SIZE=1"
Write-Host "  PG_MAX_OVERFLOW=0"
Write-Host "  CLICK_HOUSE_HOST=127.0.0.1"
Write-Host "  CLICKHOUSE_PORT=18123"
Invoke-PostgresSmokeCheck -Port 15432
