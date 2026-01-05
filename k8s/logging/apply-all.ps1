# Скрипт для применения всех манифестов error-collector
# Использование: .\apply-all.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Применение манифестов error-collector ===" -ForegroundColor Cyan

$namespace = "logging"
$basePath = ".\error-collector"

# Проверяем, что мы в правильной директории
if (-not (Test-Path "$basePath\deployment.yaml")) {
    Write-Host "Ошибка: файлы манифестов не найдены. Запустите скрипт из k8s\logging\" -ForegroundColor Red
    exit 1
}

# 1. ConfigMap
Write-Host "`n1. Применяю ConfigMap..." -ForegroundColor Yellow
kubectl apply -f "$basePath\configmap.yaml"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка при применении ConfigMap" -ForegroundColor Red
    exit 1
}

# 2. Secret (проверяем, существует ли)
Write-Host "`n2. Проверяю Secret..." -ForegroundColor Yellow
$secretExists = kubectl get secret error-collector-secrets -n $namespace 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Secret не найден. Создайте его командой:" -ForegroundColor Yellow
    Write-Host "kubectl create secret generic error-collector-secrets \`" -ForegroundColor Cyan
    Write-Host "  --from-literal=telegram_bot_token='YOUR_BOT_TOKEN' \`" -ForegroundColor Cyan
    Write-Host "  --from-literal=telegram_chat_id='YOUR_CHAT_ID' \`" -ForegroundColor Cyan
    Write-Host "  --from-literal=redis_password='' \`" -ForegroundColor Cyan
    Write-Host "  -n $namespace" -ForegroundColor Cyan
    Write-Host "`nПродолжить без Secret? (y/n): " -NoNewline -ForegroundColor Yellow
    $answer = Read-Host
    if ($answer -ne "y") {
        exit 1
    }
} else {
    Write-Host "Secret уже существует, пропускаю" -ForegroundColor Green
}

# 3. Deployment
Write-Host "`n3. Применяю Deployment..." -ForegroundColor Yellow
kubectl apply -f "$basePath\deployment.yaml"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка при применении Deployment" -ForegroundColor Red
    exit 1
}

# 4. Service
Write-Host "`n4. Применяю Service..." -ForegroundColor Yellow
kubectl apply -f "$basePath\service.yaml"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка при применении Service" -ForegroundColor Red
    exit 1
}

# 5. CronJob
Write-Host "`n5. Применяю CronJob..." -ForegroundColor Yellow
kubectl apply -f "$basePath\cronjob.yaml"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка при применении CronJob" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Все манифесты применены успешно! ===" -ForegroundColor Green
Write-Host "`nПроверьте статус:" -ForegroundColor Cyan
Write-Host "kubectl get pods -n $namespace -l app=error-collector" -ForegroundColor White
Write-Host "kubectl get svc -n $namespace error-collector" -ForegroundColor White
Write-Host "kubectl get cronjob -n $namespace error-collector-digest" -ForegroundColor White

Write-Host "`nПроверьте логи:" -ForegroundColor Cyan
Write-Host "kubectl logs -n $namespace -l app=error-collector --tail=50" -ForegroundColor White







