# Скрипт для применения конфигурации Fluent Bit для отправки ошибок в error-collector
# Использование: .\apply-fluent-bit-config.ps1

$namespace = "logging"
$configmapName = "fluent-bit"

Write-Host "Получаю текущий ConfigMap fluent-bit..." -ForegroundColor Yellow

# Получаем текущий конфиг
$currentConfig = kubectl get configmap $configmapName -n $namespace -o json | ConvertFrom-Json

# Читаем новый конфиг для ошибок
$errorsConfigPath = ".\fluent-bit-errors-to-webhook.yaml"
if (-not (Test-Path $errorsConfigPath)) {
    Write-Host "Ошибка: файл $errorsConfigPath не найден" -ForegroundColor Red
    exit 1
}

$errorsConfigContent = Get-Content $errorsConfigPath -Raw

# Извлекаем конфиг из YAML (между data: и следующими ключами)
# Ищем блок errors-webhook.conf
$errorsConfigMatch = [regex]::Match($errorsConfigContent, '(?s)errors-webhook\.conf:\s*\|\s*\n(.*?)(?=\n\s*\w+:|$)')
if (-not $errorsConfigMatch.Success) {
    Write-Host "Ошибка: не удалось извлечь конфиг из $errorsConfigPath" -ForegroundColor Red
    Write-Host "Попробуйте добавить конфиг вручную через: kubectl edit configmap fluent-bit -n $namespace" -ForegroundColor Yellow
    exit 1
}

$newConfigBlock = $errorsConfigMatch.Groups[1].Value.Trim()

# Получаем текущий fluent-bit.conf
$currentFluentBitConf = $currentConfig.data.'fluent-bit.conf'

# Проверяем, не добавлен ли уже этот конфиг
if ($currentFluentBitConf -match "error-collector\.logging\.svc") {
    Write-Host "Конфиг для error-collector уже добавлен в fluent-bit.conf" -ForegroundColor Yellow
    Write-Host "Хотите обновить? (y/n): " -NoNewline
    $answer = Read-Host
    if ($answer -ne "y") {
        Write-Host "Отменено" -ForegroundColor Yellow
        exit 0
    }
    # Удаляем старый блок
    $currentFluentBitConf = $currentFluentBitConf -replace '(?s)\[FILTER\].*?Name grep.*?Match kube\.\*.*?Regex log.*?\[OUTPUT\].*?Name http.*?Match kube\.\*.*?Host error-collector.*?Retry_Limit \d+.*?\n', ''
}

# Добавляем новый конфиг в конец
$updatedConf = $currentFluentBitConf + "`n`n" + $newConfigBlock

# Обновляем ConfigMap
$currentConfig.data.'fluent-bit.conf' = $updatedConf

# Сохраняем во временный файл
$tempFile = [System.IO.Path]::GetTempFileName() + ".json"
$currentConfig | ConvertTo-Json -Depth 10 | Set-Content $tempFile

Write-Host "Применяю обновленный ConfigMap..." -ForegroundColor Yellow
kubectl apply -f $tempFile

if ($LASTEXITCODE -eq 0) {
    Write-Host "ConfigMap обновлен успешно!" -ForegroundColor Green
    Write-Host "Fluent Bit DaemonSet автоматически перезагрузит конфиг" -ForegroundColor Green
    Write-Host "Проверьте логи: kubectl logs -n $namespace -l app=fluent-bit --tail=50" -ForegroundColor Cyan
} else {
    Write-Host "Ошибка при применении ConfigMap" -ForegroundColor Red
    exit 1
}

# Удаляем временный файл
Remove-Item $tempFile -ErrorAction SilentlyContinue

