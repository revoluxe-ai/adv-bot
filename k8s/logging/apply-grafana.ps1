# Устанавливает Grafana (chart grafana/grafana) в namespace logging с Loki и дашбордом ошибок.
# Пример (HTTPS за Ingress): .\apply-grafana.ps1 -HostName "grafana.example.com"
# Только port-forward (без Ingress): .\apply-grafana.ps1 -SkipIngress
# TLS для Ingress: добавьте cert-manager (см. аннотации ниже) или заполните ingress.tls в grafana-values.yml.

param(
    [string]$HostName = "",
    [ValidateSet("https", "http")]
    [string]$UrlScheme = "https",
    [string]$IngressClass = "nginx",
    [string]$StorageClass = "",
    [switch]$SkipIngress,
    [switch]$RecreateAdminSecret
)

$ErrorActionPreference = "Stop"
$ns = "logging"
$release = "grafana"
$valuesTemplate = Join-Path $PSScriptRoot "grafana\grafana-values.yml"
$dashboardJson = Join-Path $PSScriptRoot "grafana\loki-errors-dashboard.json"

if (-not (Test-Path $valuesTemplate)) {
    Write-Host "Не найден $valuesTemplate" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $dashboardJson)) {
    Write-Host "Не найден $dashboardJson" -ForegroundColor Red
    exit 1
}

if ($SkipIngress) {
    if (-not $HostName) { $HostName = "localhost" }
    $rootUrl = "http://localhost:3000/"
    $ingressEnabled = "false"
    Write-Host "Режим без Ingress: root_url=$rootUrl (используйте kubectl port-forward svc/$release 3000:80 -n $ns)" -ForegroundColor Yellow
}
else {
    if (-not $HostName) {
        Write-Host "Укажите -HostName (FQDN для Ingress), например: .\apply-grafana.ps1 -HostName grafana.example.com" -ForegroundColor Red
        exit 1
    }
    $rootUrl = "$UrlScheme`://$HostName/"
    $ingressEnabled = "true"
}

Write-Host "Helm: repo grafana..." -ForegroundColor Cyan
helm repo add grafana https://grafana.github.io/helm-charts 2>$null
helm repo update | Out-Null

Write-Host "Namespace $ns..." -ForegroundColor Cyan
kubectl get namespace $ns 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { kubectl create namespace $ns }

if ($RecreateAdminSecret) {
    kubectl delete secret grafana-admin -n $ns 2>$null
}

kubectl get secret grafana-admin -n $ns 2>$null | Out-Null
$secretMissing = $LASTEXITCODE -ne 0

if ($secretMissing) {
    $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'.ToCharArray()
    $pass = -join ((1..24) | ForEach-Object { $chars | Get-Random })
    kubectl create secret generic grafana-admin -n $ns `
        --from-literal=admin-user=admin `
        --from-literal=admin-password=$pass
    Write-Host ""
    Write-Host "Создан secret grafana-admin. Логин: admin" -ForegroundColor Green
    Write-Host "Пароль (сохраните): $pass" -ForegroundColor Yellow
    Write-Host ""
}
else {
    Write-Host "Secret grafana-admin уже есть (пароль не меняли). Сброс: .\apply-grafana.ps1 -RecreateAdminSecret" -ForegroundColor DarkGray
}

$values = Get-Content -Raw $valuesTemplate
$values = $values.Replace("__GRAFANA_FQDN__", $HostName)
$values = $values.Replace("__GRAFANA_ROOT_URL__", $rootUrl)
$values = $values.Replace("__INGRESS_ENABLED__", $ingressEnabled)
if ($IngressClass) {
    $values = $values -replace "(?m)^  ingressClassName:.*$", "  ingressClassName: $IngressClass"
}
if ($StorageClass) {
    $values = $values -replace "(?m)^  storageClassName:.*$", "  storageClassName: `"$StorageClass`""
}

$tmpValues = [System.IO.Path]::GetTempFileName() + ".yml"
Set-Content -Path $tmpValues -Value $values -Encoding UTF8

Write-Host "Helm upgrade --install $release..." -ForegroundColor Cyan
helm upgrade --install $release grafana/grafana -n $ns -f $tmpValues
if ($LASTEXITCODE -ne 0) {
    Write-Host "Helm failed" -ForegroundColor Red
    exit 1
}
Remove-Item $tmpValues -ErrorAction SilentlyContinue

Write-Host "ConfigMap дашборда..." -ForegroundColor Cyan
kubectl create configmap grafana-dashboard-loki-errors -n $ns `
    --from-file=loki-errors.json=$dashboardJson `
    --dry-run=client -o yaml | kubectl apply -f -
kubectl label configmap grafana-dashboard-loki-errors -n $ns grafana_dashboard=1 --overwrite

Write-Host "Ожидание rollout..." -ForegroundColor Cyan
kubectl rollout status deployment -n $ns -l "app.kubernetes.io/name=grafana" --timeout=300s

Write-Host ""
Write-Host "Готово." -ForegroundColor Green
if ($SkipIngress) {
    Write-Host "Port-forward: kubectl port-forward -n $ns svc/$release 3000:80" -ForegroundColor White
    Write-Host "UI: http://localhost:3000/  Дашборд: Home -> Dashboards -> Loki — ошибки по namespace / pod" -ForegroundColor White
}
else {
    Write-Host "UI: $rootUrl" -ForegroundColor White
    Write-Host "Если Ingress не поднимается: kubectl describe ingress -n $ns $release" -ForegroundColor DarkGray
    Write-Host "TLS (пример cert-manager): добавьте в grafana-values.yml ingress.annotations:" -ForegroundColor DarkGray
    Write-Host '  cert-manager.io/cluster-issuer: "letsencrypt-prod"' -ForegroundColor DarkGray
    Write-Host "и блок ingress.tls с secretName." -ForegroundColor DarkGray
}
