# Диагностика проблемы с прогнозом CTR
# Использование: .\k8s\monitoring\diagnose-predict-ctr.ps1 -ShopId "76ffadfc-b81e-4ff8-9611-29b7c1c867dc" -AdvId 30554463

param(
    [Parameter(Mandatory=$true)]
    [string]$ShopId,
    
    [Parameter(Mandatory=$true)]
    [int]$AdvId
)

# Установка KUBECONFIG
$kubeconfigPath = "C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml"
if (Test-Path $kubeconfigPath) {
    $env:KUBECONFIG = $kubeconfigPath
} else {
    Write-Host "[WARNING] Конфиг kubectl не найден: $kubeconfigPath" -ForegroundColor Yellow
    Write-Host "Продолжаю с текущим конфигом..." -ForegroundColor Yellow
}

Write-Host "=== Диагностика прогноза CTR ===" -ForegroundColor Cyan
Write-Host "Shop ID: $ShopId" -ForegroundColor Yellow
Write-Host "Adv ID: $AdvId" -ForegroundColor Yellow
Write-Host "KUBECONFIG: $env:KUBECONFIG" -ForegroundColor Gray
Write-Host ""

# Определение namespace (prod-adv-bot или default)
$namespace = "prod-adv-bot"
$testNs = kubectl get namespace prod-adv-bot 2>&1
if ($LASTEXITCODE -ne 0) {
    $namespace = "default"
    Write-Host "[WARNING] Namespace prod-adv-bot не найден, используем default" -ForegroundColor Yellow
} else {
    Write-Host "[OK] Используем namespace: $namespace" -ForegroundColor Green
}
Write-Host ""

# 1. Проверка статуса predict-ctr-service
Write-Host "1. Проверка статуса predict-ctr-service..." -ForegroundColor Green
$predictCtrPods = kubectl get pods -n $namespace -l app=predict-ctr-service -o wide 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host $predictCtrPods
    $podStatus = kubectl get pods -n $namespace -l app=predict-ctr-service -o jsonpath='{.items[0].status.phase}' 2>&1
    if ($podStatus -eq "Running") {
        Write-Host "[OK] Pod predict-ctr-service работает" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Pod predict-ctr-service не работает. Статус: $podStatus" -ForegroundColor Red
    }
} else {
    Write-Host "[ERROR] Не удалось получить статус подов predict-ctr-service" -ForegroundColor Red
    Write-Host $predictCtrPods
}
Write-Host ""

# 2. Проверка Service
Write-Host "2. Проверка Service predict-ctr-service..." -ForegroundColor Green
$service = kubectl get svc -n $namespace predict-ctr-service -o wide 2>&1
if ($LASTEXITCODE -ne 0) {
    # Пробуем в default namespace
    $service = kubectl get svc -n default predict-ctr-service -o wide 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[WARNING] Service найден в namespace default, но поды в $namespace" -ForegroundColor Yellow
        Write-Host "   Это может быть проблемой! Service должен быть в том же namespace." -ForegroundColor Red
    }
}
if ($LASTEXITCODE -eq 0) {
    Write-Host $service
    Write-Host "[OK] Service существует" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Service predict-ctr-service не найден!" -ForegroundColor Red
    Write-Host "   Применить: kubectl apply -f k8s\predict-ctr-service.yaml" -ForegroundColor Yellow
}
Write-Host ""

# 3. Проверка переменных окружения в воркерах
Write-Host "3. Проверка переменных окружения в run-shop-update-worker..." -ForegroundColor Green
$deploymentYaml = kubectl get deployment run-shop-update-worker -n $namespace -o yaml 2>&1
if ($LASTEXITCODE -eq 0) {
    $hostMatch = $deploymentYaml | Select-String -Pattern 'name: PREDICT_CTR_HOST' -Context 0,1
    $portMatch = $deploymentYaml | Select-String -Pattern 'name: PREDICT_CTR_PORT' -Context 0,1
    
    if ($hostMatch -and $portMatch) {
        $hostValue = ($hostMatch | Select-Object -First 1).Context.PostContext[0] -replace '.*value:\s*(.*)', '$1'
        $portValue = ($portMatch | Select-Object -First 1).Context.PostContext[0] -replace '.*value:\s*(.*)', '$1'
        
        Write-Host "Переменные окружения:" -ForegroundColor Cyan
        Write-Host "  PREDICT_CTR_HOST: $hostValue" -ForegroundColor Gray
        Write-Host "  PREDICT_CTR_PORT: $portValue" -ForegroundColor Gray
        
        if ($hostValue -and $portValue) {
            Write-Host "[OK] Переменные окружения установлены" -ForegroundColor Green
            $expectedHost = "predict-ctr-service.$namespace.svc.cluster.local"
            if ($hostValue -ne $expectedHost -and $hostValue -ne "predict-ctr-service") {
                Write-Host "[WARNING] Host указан как '$hostValue', рекомендуется использовать '$expectedHost'" -ForegroundColor Yellow
            }
        } else {
            Write-Host "[ERROR] Переменные PREDICT_CTR_HOST или PREDICT_CTR_PORT не установлены!" -ForegroundColor Red
            Write-Host "   Установить: kubectl set env deployment/run-shop-update-worker -n $namespace PREDICT_CTR_HOST=predict-ctr-service.$namespace.svc.cluster.local PREDICT_CTR_PORT=50053" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[ERROR] Переменные PREDICT_CTR_HOST или PREDICT_CTR_PORT не найдены!" -ForegroundColor Red
        Write-Host "   Установить: kubectl set env deployment/run-shop-update-worker -n $namespace PREDICT_CTR_HOST=predict-ctr-service.$namespace.svc.cluster.local PREDICT_CTR_PORT=50053" -ForegroundColor Yellow
    }
} else {
    Write-Host "[ERROR] Не удалось получить deployment" -ForegroundColor Red
}
Write-Host ""

# 4. Проверка логов воркеров на ошибки
Write-Host "4. Поиск ошибок в логах воркеров (последние 100 строк)..." -ForegroundColor Green
$workerPods = kubectl get pods -n $namespace -l app=run-shop-update-worker -o jsonpath='{.items[0].metadata.name}' 2>&1
if ($workerPods -and $LASTEXITCODE -eq 0) {
    Write-Host "Проверка логов пода: $workerPods" -ForegroundColor Cyan
    $advIdStr = $AdvId.ToString()
    $pattern = "predict.*ctr|grpc|UNAVAILABLE|ERROR|predict_ctr|$advIdStr"
    $logs = kubectl logs $workerPods -n $namespace --tail=100 2>&1 | Select-String -Pattern $pattern -CaseSensitive:$false
    if ($logs) {
        Write-Host "Найдены записи в логах:" -ForegroundColor Yellow
        $logs | ForEach-Object { Write-Host $_ }
    } else {
        Write-Host "[WARNING] Записей о predict_ctr в последних 100 строках не найдено" -ForegroundColor Yellow
        Write-Host "Проверяю больше логов..." -ForegroundColor Gray
        $moreLogs = kubectl logs $workerPods -n $namespace --tail=500 2>&1 | Select-String -Pattern "update_predict_ctr|$advIdStr" -CaseSensitive:$false
        if ($moreLogs) {
            Write-Host "Найдены записи в расширенном поиске:" -ForegroundColor Yellow
            $moreLogs | Select-Object -Last 10 | ForEach-Object { Write-Host $_ }
        }
    }
} else {
    Write-Host "[ERROR] Не удалось найти поды run-shop-update-worker" -ForegroundColor Red
}
Write-Host ""

# 5. Проверка логов predict-ctr-service
Write-Host "5. Проверка логов predict-ctr-service (последние 50 строк)..." -ForegroundColor Green
$predictCtrPod = kubectl get pods -n $namespace -l app=predict-ctr-service -o jsonpath='{.items[0].metadata.name}' 2>&1
if ($predictCtrPod -and $LASTEXITCODE -eq 0) {
    Write-Host "Логи пода: $predictCtrPod" -ForegroundColor Cyan
    kubectl logs $predictCtrPod -n $namespace --tail=50 2>&1 | Select-Object -Last 20
} else {
    Write-Host "[ERROR] Не удалось найти под predict-ctr-service" -ForegroundColor Red
}
Write-Host ""

# 6. Проверка подключения к сервису
Write-Host "6. Проверка подключения к predict-ctr-service из пода..." -ForegroundColor Green
if ($workerPods -and $LASTEXITCODE -eq 0) {
    Write-Host "Проверка DNS резолюции..." -ForegroundColor Cyan
    $dnsCheck = kubectl exec $workerPods -n $namespace -- nslookup predict-ctr-service.$namespace.svc.cluster.local 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host $dnsCheck
        Write-Host "[OK] DNS резолюция работает" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Проблема с DNS резолюцией" -ForegroundColor Red
        Write-Host $dnsCheck
    }
} else {
    Write-Host "[WARNING] Не удалось проверить подключение (под не найден)" -ForegroundColor Yellow
}
Write-Host ""

# 7. Рекомендации
Write-Host "=== Рекомендации ===" -ForegroundColor Cyan
Write-Host "1. Если Service отсутствует в namespace $namespace, применить:" -ForegroundColor Yellow
Write-Host "   kubectl apply -f k8s\predict-ctr-service.yaml -n $namespace" -ForegroundColor Yellow
Write-Host "   Или создать Service в правильном namespace" -ForegroundColor Yellow
Write-Host "2. Если переменные окружения отсутствуют:" -ForegroundColor Yellow
Write-Host "   kubectl set env deployment/run-shop-update-worker -n $namespace PREDICT_CTR_HOST=predict-ctr-service.$namespace.svc.cluster.local PREDICT_CTR_PORT=50053" -ForegroundColor Yellow
Write-Host "3. Перезапустить deployment:" -ForegroundColor Yellow
Write-Host "   kubectl rollout restart deployment/run-shop-update-worker -n $namespace" -ForegroundColor Yellow
Write-Host "4. Проверить логи после перезапуска:" -ForegroundColor Yellow
Write-Host "   kubectl logs -f deployment/run-shop-update-worker -n $namespace | Select-String 'predict_ctr'" -ForegroundColor Yellow
Write-Host ""

# 8. Проверка Redis (если доступен)
Write-Host "8. Проверка Redis на наличие прогнозов..." -ForegroundColor Green
Write-Host "   Для проверки Redis нужен доступ к базе данных" -ForegroundColor Yellow
Write-Host "   Ключи для поиска:" -ForegroundColor Cyan
Write-Host "   - predict_ctr:$AdvId:* (V1 режим)" -ForegroundColor Gray
Write-Host "   - predict_ctr_v2:*:* (V2 режим, нужно знать nmids)" -ForegroundColor Gray
Write-Host ""

Write-Host "=== Диагностика завершена ===" -ForegroundColor Cyan
