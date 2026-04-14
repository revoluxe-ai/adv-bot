$ErrorActionPreference = "Stop"

$namespace = "logging"
$release = "loki"
$valuesFile = ".\loki-values.yml"

Write-Host "Installing/upgrading Loki in namespace $namespace..." -ForegroundColor Cyan

if (-not (Test-Path $valuesFile)) {
    Write-Host "Values file not found: $valuesFile" -ForegroundColor Red
    exit 1
}

helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm upgrade --install $release grafana/loki `
  -n $namespace `
  -f $valuesFile

kubectl rollout status statefulset/$release -n $namespace --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "Loki rollout did not complete successfully. Inspect with:" -ForegroundColor Red
    Write-Host "kubectl get pods -n $namespace | Select-String loki" -ForegroundColor White
    Write-Host "kubectl describe pod -n $namespace -l app.kubernetes.io/name=loki" -ForegroundColor White
    exit 1
}

Write-Host "Loki is ready." -ForegroundColor Green
Write-Host "Service: loki.$namespace.svc.cluster.local:3100" -ForegroundColor White
