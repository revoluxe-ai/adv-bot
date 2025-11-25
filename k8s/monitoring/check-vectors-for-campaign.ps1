# Проверка векторов для кампании
# Использование: .\k8s\monitoring\check-vectors-for-campaign.ps1 -AdvId 30554463

param(
    [Parameter(Mandatory=$true)]
    [int]$AdvId
)

$kubeconfigPath = "C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml"
if (Test-Path $kubeconfigPath) {
    $env:KUBECONFIG = $kubeconfigPath
}

$namespace = "prod-adv-bot"

Write-Host "=== Checking Vectors for Campaign $AdvId ===" -ForegroundColor Cyan
Write-Host ""

# Шаг 1: Получить nmids кампании из БД (нужно будет выполнить SQL запрос)
Write-Host "[STEP 1] Need to get nmids for campaign $AdvId" -ForegroundColor Yellow
Write-Host "  SQL Query: SELECT nmids FROM adv_setting WHERE adv_id = $AdvId" -ForegroundColor Gray
Write-Host ""

# Шаг 2: Проверить векторы товаров в Redis
Write-Host "[STEP 2] Checking item vectors in Redis..." -ForegroundColor Green
Write-Host "  Redis keys pattern: item_vector:{nmid}" -ForegroundColor Gray
Write-Host "  Need to check Redis for item_vector keys" -ForegroundColor Yellow
Write-Host ""

# Шаг 3: Проверить векторы товаров в Neo4j
Write-Host "[STEP 3] Checking item vectors in Neo4j..." -ForegroundColor Green
Write-Host "  Neo4j query: MATCH (item:Item) WHERE item.nmid IN [nmids] AND item.fastrp IS NOT NULL RETURN count(item)" -ForegroundColor Gray
Write-Host ""

# Шаг 4: Получить ключевые слова кампании
Write-Host "[STEP 4] Need to get keywords for campaign $AdvId" -ForegroundColor Yellow
Write-Host "  SQL Query: SELECT text FROM keyword_setting WHERE adv_setting_id = (SELECT id FROM adv_setting WHERE adv_id = $AdvId)" -ForegroundColor Gray
Write-Host ""

# Шаг 5: Проверить векторы ключевых слов в Redis
Write-Host "[STEP 5] Checking keyword vectors in Redis..." -ForegroundColor Green
Write-Host "  Redis keys pattern: keyword_vector:{keyword}" -ForegroundColor Gray
Write-Host ""

# Шаг 6: Проверить векторы ключевых слов в Neo4j
Write-Host "[STEP 6] Checking keyword vectors in Neo4j..." -ForegroundColor Green
Write-Host "  Neo4j query: MATCH (k:KeywordPhrase) WHERE k.text IN [keywords] AND k.fastrp IS NOT NULL RETURN count(k)" -ForegroundColor Gray
Write-Host ""

Write-Host "=== Manual Checks Needed ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Check Redis item vectors:" -ForegroundColor Yellow
Write-Host "   kubectl exec -n $namespace redis-pod -- redis-cli KEYS 'item_vector:*' | Measure-Object" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Check Redis keyword vectors:" -ForegroundColor Yellow
Write-Host "   kubectl exec -n $namespace redis-pod -- redis-cli KEYS 'keyword_vector:*' | Measure-Object" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Check Neo4j item vectors:" -ForegroundColor Yellow
Write-Host "   MATCH (item:Item) WHERE item.fastrp IS NOT NULL RETURN count(item)" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Check Neo4j keyword vectors:" -ForegroundColor Yellow
Write-Host "   MATCH (k:KeywordPhrase) WHERE k.fastrp IS NOT NULL RETURN count(k)" -ForegroundColor Gray
Write-Host ""
Write-Host "5. Check if update-keywords-vectors pod is running:" -ForegroundColor Yellow
Write-Host "   kubectl get pods -n $namespace | Select-String 'update-keywords-vectors'" -ForegroundColor Gray
Write-Host ""

Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host "If vectors are missing:" -ForegroundColor Yellow
Write-Host "1. Run update-keywords-vectors-in-redis-from-neo4j job" -ForegroundColor Gray
Write-Host "2. Check update_vectors_in_redis process logs" -ForegroundColor Gray
Write-Host "3. Verify Neo4j has vectors (fastrp property)" -ForegroundColor Gray
Write-Host ""





