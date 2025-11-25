# Скрипт для настройки kubectl конфига
# Использование: . .\k8s\monitoring\setup-kubectl-config.ps1

$kubeconfigPath = "C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml"

if (Test-Path $kubeconfigPath) {
    $env:KUBECONFIG = $kubeconfigPath
    Write-Host "✅ KUBECONFIG установлен: $kubeconfigPath" -ForegroundColor Green
    
    # Проверка подключения
    Write-Host "Проверка подключения к кластеру..." -ForegroundColor Cyan
    $context = kubectl config current-context 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Текущий контекст: $context" -ForegroundColor Green
    } else {
        Write-Host "❌ Ошибка получения контекста" -ForegroundColor Red
    }
} else {
    Write-Host "❌ Файл конфига не найден: $kubeconfigPath" -ForegroundColor Red
    Write-Host "Проверьте путь к конфигу" -ForegroundColor Yellow
}





