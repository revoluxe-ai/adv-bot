# Полная проверка pipeline прогнозирования CTR
# Использование: .\k8s\monitoring\check-predict-ctr-pipeline.ps1 -ShopId "76ffadfc-b81e-4ff8-9611-29b7c1c867dc" -AdvId 30554463

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
}

$namespace = "prod-adv-bot"

Write-Host "=== Full Predict CTR Pipeline Check ===" -ForegroundColor Cyan
Write-Host "Shop ID: $ShopId" -ForegroundColor Yellow
Write-Host "Adv ID: $AdvId" -ForegroundColor Yellow
Write-Host ""

# Шаг 1: Проверка вызова update_predict_ctr
Write-Host "[STEP 1] Checking if update_predict_ctr is being called..." -ForegroundColor Green
$pods = kubectl get pods -n $namespace -l app=run-shop-update-worker -o jsonpath='{.items[*].metadata.name}' 2>&1
if ($LASTEXITCODE -eq 0) {
    $found = $false
    $pods.Split(' ') | ForEach-Object {
        if ($_) {
            $logs = kubectl logs $_ -n $namespace --tail=1000 2>&1 | Select-String -Pattern "Начинаем обновление прогнозов CTR|Нет активных кампаний" -CaseSensitive:$false
            if ($logs) {
                $found = $true
                Write-Host "  Pod $_:" -ForegroundColor Cyan
                $logs | Select-Object -Last 3 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
            }
        }
    }
    if (-not $found) {
        Write-Host "  [WARNING] No logs found about predict CTR updates" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [ERROR] Cannot get worker pods" -ForegroundColor Red
}
Write-Host ""

# Шаг 2: Проверка обработки конкретной кампании
Write-Host "[STEP 2] Checking campaign processing logs..." -ForegroundColor Green
$pod = kubectl get pods -n $namespace -l app=run-shop-update-worker -o jsonpath='{.items[0].metadata.name}' 2>&1
if ($pod -and $LASTEXITCODE -eq 0) {
    $advIdStr = $AdvId.ToString()
    $logs = kubectl logs $pod -n $namespace --tail=3000 2>&1 | Select-String -Pattern "Обрабатываем кампанию $advIdStr|Нет ключевых слов для кампании $advIdStr|Получен None от gRPC сервиса для кампании $advIdStr|пустой словарь прогнозов от gRPC сервиса для кампании $advIdStr|Сохранено.*прогнозов CTR для кампании $advIdStr" -CaseSensitive:$false
    if ($logs) {
        Write-Host "  Found logs for campaign $AdvId:" -ForegroundColor Cyan
        $logs | Select-Object -Last 10 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    } else {
        Write-Host "  [WARNING] No logs found for campaign $AdvId" -ForegroundColor Yellow
        Write-Host "  Checking for any campaign processing..." -ForegroundColor Gray
        $anyLogs = kubectl logs $pod -n $namespace --tail=2000 2>&1 | Select-String -Pattern "Обрабатываем кампанию|Нет ключевых слов для кампании" -CaseSensitive:$false
        if ($anyLogs) {
            Write-Host "  Found logs for other campaigns:" -ForegroundColor Cyan
            $anyLogs | Select-Object -Last 5 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        }
    }
} else {
    Write-Host "  [ERROR] Cannot get worker pod" -ForegroundColor Red
}
Write-Host ""

# Шаг 3: Проверка gRPC ошибок
Write-Host "[STEP 3] Checking for gRPC errors..." -ForegroundColor Green
if ($pod -and $LASTEXITCODE -eq 0) {
    $errors = kubectl logs $pod -n $namespace --tail=2000 2>&1 | Select-String -Pattern "gRPC ошибка|Сервис недоступен|Неверные аргументы|StatusCode|UNAVAILABLE" -CaseSensitive:$false
    if ($errors) {
        Write-Host "  [ERROR] Found gRPC errors:" -ForegroundColor Red
        $errors | Select-Object -Last 10 | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    } else {
        Write-Host "  [OK] No gRPC errors found" -ForegroundColor Green
    }
} else {
    Write-Host "  [ERROR] Cannot get worker pod" -ForegroundColor Red
}
Write-Host ""

# Шаг 4: Проверка логов predict-ctr-service
Write-Host "[STEP 4] Checking predict-ctr-service logs..." -ForegroundColor Green
$predictPod = kubectl get pods -n $namespace -l app=predict-ctr-service -o jsonpath='{.items[0].metadata.name}' 2>&1
if ($predictPod -and $LASTEXITCODE -eq 0) {
    Write-Host "  Recent logs from predict-ctr-service:" -ForegroundColor Cyan
    kubectl logs $predictPod -n $namespace --tail=50 2>&1 | Select-Object -Last 20 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
} else {
    Write-Host "  [ERROR] Cannot get predict-ctr-service pod" -ForegroundColor Red
}
Write-Host ""

# Шаг 5: Проверка активных кампаний для shop_id
Write-Host "[STEP 5] Summary and recommendations..." -ForegroundColor Green
Write-Host "  Pipeline steps:" -ForegroundColor Cyan
Write-Host "    1. update_predict_ctr() called every 60s" -ForegroundColor Gray
Write-Host "    2. get_active_advs() - gets active campaigns for shop" -ForegroundColor Gray
Write-Host "    3. get_calculated_keywords() - gets keywords for each campaign" -ForegroundColor Gray
Write-Host "    4. If no keywords -> return early (DEBUG log)" -ForegroundColor Gray
Write-Host "    5. gRPC request to predict-ctr-service" -ForegroundColor Gray
Write-Host "    6. Save predictions to Redis" -ForegroundColor Gray
Write-Host ""
Write-Host "  Possible issues:" -ForegroundColor Yellow
Write-Host "    - Campaign not in active list (bot_active=false or shop_id mismatch)" -ForegroundColor Gray
Write-Host "    - No keywords for campaign (get_good_bad_phrases returns empty)" -ForegroundColor Gray
Write-Host "    - gRPC service not responding" -ForegroundColor Gray
Write-Host "    - Predictions not saved to Redis" -ForegroundColor Gray
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "    1. Check database: SELECT * FROM adv_setting WHERE adv_id = $AdvId AND bot_active = true" -ForegroundColor Gray
Write-Host "    2. Check shop_id matches: SELECT shop_id FROM wb_cabinet WHERE id = (SELECT wb_cabinet_id FROM adv_setting WHERE adv_id = $AdvId)" -ForegroundColor Gray
Write-Host "    3. Check keywords exist: Check get_good_bad_phrases function" -ForegroundColor Gray
Write-Host "    4. Check Redis keys: predict_ctr:$AdvId:* or predict_ctr_v2:*:*" -ForegroundColor Gray
Write-Host ""

Write-Host "=== Check completed ===" -ForegroundColor Cyan





