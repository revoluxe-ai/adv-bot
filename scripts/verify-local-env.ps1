# ============================================================================
# verify-local-env.ps1
# ============================================================================
# Проверка типичных ошибок .env для локального запуска (PG/CH/Redis).
# Запуск: .\scripts\verify-local-env.ps1
# ============================================================================

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot ".env"

if (-not (Test-Path $envFile)) {
    Write-Error ".env not found at $envFile"
}

function Get-EnvValue {
    param([string]$Key)
    $line = Get-Content $envFile | Where-Object { $_ -match "^\s*$Key\s*=" } | Select-Object -First 1
    if (-not $line) { return $null }
    return ($line -split "=", 2)[1].Trim().Trim('"').Trim("'")
}

$pgHost = Get-EnvValue "POSTGRES_MASTER_HOST"
$pgPort = Get-EnvValue "POSTGRES_PORT"
$chHost = Get-EnvValue "CLICK_HOUSE_HOST"
$chPort = Get-EnvValue "CLICKHOUSE_PORT"
$redisHost = Get-EnvValue "REDIS_HOST"

$errors = @()
$warnings = @()

# LB Proxy Timeweb + NodePort: classic SSL timeout ~60s
if ($pgHost -eq "217.25.92.218" -and $pgPort -eq "31024") {
    $errors += "POSTGRES: 217.25.92.218:31024 is LB IP + NodePort mix. Use 92.255.79.78:31024 or 127.0.0.1:15432."
}

if ($pgHost -eq "217.25.92.218" -and $pgPort -eq "5432") {
    $warnings += "POSTGRES: 217.25.92.218:5432 Timeweb Proxy LB often breaks pooler auth. Prefer 92.255.79.78:31024."
}

if ($pgPort -match "^\d+$" -and [int]$pgPort -ge 30000 -and $pgPort -le 32767 -and $pgHost -eq "217.25.92.218") {
    $errors += "POSTGRES: NodePort $pgPort must not use LB host 217.25.92.218; use 92.255.79.78."
}

if ($chHost -eq "194.87.215.163" -and $chPort -match "^\d+$" -and [int]$chPort -ge 30000) {
    $warnings += "CLICKHOUSE: LB IP 194.87.215.163 with NodePort $chPort may fail; use 92.255.79.78:$chPort."
}

if ($redisHost -and $redisHost -notmatch "127\.0\.0\.1|localhost") {
    $errors += "REDIS_HOST=${redisHost}: local dev needs 127.0.0.1 (k8s redis not reachable from PC)."
}

if ($redisHost -eq "127.0.0.1" -or $redisHost -eq "localhost") {
    $tcp = Test-NetConnection 127.0.0.1 -Port 6379 -WarningAction SilentlyContinue
    if (-not $tcp.TcpTestSucceeded) {
        $errors += "Redis not listening on 127.0.0.1:6379. Run: docker run -d --name adv-bot-redis -p 6379:6379 redis:7-alpine"
    }
}

Write-Host "Checking $envFile"
Write-Host "  POSTGRES_MASTER_HOST=$pgHost"
Write-Host "  POSTGRES_PORT=$pgPort"
Write-Host "  CLICK_HOUSE_HOST=$chHost"
Write-Host "  CLICKHOUSE_PORT=$chPort"
Write-Host "  REDIS_HOST=$redisHost"
Write-Host ""

foreach ($w in $warnings) {
    Write-Host "WARN: $w" -ForegroundColor Yellow
}

if ($errors.Count -gt 0) {
    foreach ($e in $errors) {
        Write-Host "ERROR: $e" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Fix: .\scripts\sync-local-env-from-k8s.ps1 then merge .env.k8s-sync into .env"
    exit 1
}

Write-Host "OK: no blocking issues found" -ForegroundColor Green
if ($warnings.Count -gt 0) {
    exit 2
}
