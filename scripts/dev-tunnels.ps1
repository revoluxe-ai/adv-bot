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
if ($env:DEV_TUNNELS_KUBECONFIG) {
    $kubeconfig = $env:DEV_TUNNELS_KUBECONFIG
} else {
    $kubeconfig = $defaultKubeconfig
}

if (-not (Test-Path $kubeconfig)) {
    Write-Error "Kubeconfig not found: $kubeconfig"
}

$env:KUBECONFIG = $kubeconfig

Write-Host "KUBECONFIG=$kubeconfig"
kubectl config current-context

Write-Host ""
Write-Host "Starting Postgres tunnel: localhost:15432 -> postgres-db:5432"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$env:KUBECONFIG='$kubeconfig'; kubectl port-forward -n prod-adv-bot svc/postgres-db 15432:5432"
)

Write-Host "Starting ClickHouse tunnel: localhost:18123/19000 -> ClickHouse"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$env:KUBECONFIG='$kubeconfig'; kubectl port-forward -n prod-analytics svc/chi-clickhouse-main-0-0 18123:8123 19000:9000"
)

Write-Host ""
Write-Host "Tunnels started in separate PowerShell windows."
Write-Host "PG:        127.0.0.1:15432"
Write-Host "CH HTTP:   127.0.0.1:18123"
Write-Host "CH Native: 127.0.0.1:19000"
Write-Host ""
Write-Host "Set in .env (RUN_LOCAL=false if using this script only):"
Write-Host "  POSTGRES_MASTER_HOST=127.0.0.1"
Write-Host "  POSTGRES_REPLICA_HOST=127.0.0.1"
Write-Host "  POSTGRES_PORT=15432"
Write-Host "  POSTGRES_SSL_MODE=disable"
Write-Host "  CLICK_HOUSE_HOST=127.0.0.1"
Write-Host "  CLICKHOUSE_PORT=18123"
