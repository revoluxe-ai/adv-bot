# Применение оптимизации CPU для Neo4j
# Использование: .\k8s\monitoring\apply-neo4j-cpu-optimization.ps1

$kubeconfigPath = "C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml"
if (Test-Path $kubeconfigPath) {
    $env:KUBECONFIG = $kubeconfigPath
}

$namespace = "prod-analytics"
$valuesFile = "k8s\databases\neo4j\my-neo4j-values.yaml"

Write-Host "=== Applying Neo4j CPU Optimization ===" -ForegroundColor Cyan
Write-Host ""

# Проверка файла конфигурации
if (-not (Test-Path $valuesFile)) {
    Write-Host "[ERROR] Configuration file not found: $valuesFile" -ForegroundColor Red
    exit 1
}

Write-Host "[STEP 1] Checking current Neo4j CPU usage..." -ForegroundColor Green
$currentUsage = kubectl top pod my-neo4j-0 -n $namespace 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host $currentUsage
} else {
    Write-Host "[WARNING] Cannot get current CPU usage" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "[STEP 2] Checking if Helm is available..." -ForegroundColor Green
$helmCheck = helm version --short 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Helm version: $helmCheck" -ForegroundColor Green
    
    Write-Host "[STEP 3] Applying updated configuration..." -ForegroundColor Green
    Write-Host "Command: helm upgrade my-neo4j neo4j/neo4j -n $namespace -f $valuesFile" -ForegroundColor Gray
    Write-Host ""
    Write-Host "⚠️  This will update Neo4j configuration. Continue? (Y/N)" -ForegroundColor Yellow
    $confirm = Read-Host
    if ($confirm -eq "Y" -or $confirm -eq "y") {
        helm upgrade my-neo4j neo4j/neo4j -n $namespace -f $valuesFile
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Configuration applied successfully" -ForegroundColor Green
            
            Write-Host "[STEP 4] Checking if restart is needed..." -ForegroundColor Green
            Write-Host "Neo4j may need restart to apply new settings." -ForegroundColor Yellow
            Write-Host "Restart command: kubectl rollout restart statefulset/my-neo4j -n $namespace" -ForegroundColor Gray
            Write-Host ""
            Write-Host "Restart now? (Y/N)" -ForegroundColor Yellow
            $restart = Read-Host
            if ($restart -eq "Y" -or $restart -eq "y") {
                kubectl rollout restart statefulset/my-neo4j -n $namespace
                Write-Host "[OK] Neo4j restart initiated" -ForegroundColor Green
                Write-Host "Waiting for rollout to complete..." -ForegroundColor Gray
                kubectl rollout status statefulset/my-neo4j -n $namespace --timeout=5m
            }
        } else {
            Write-Host "[ERROR] Failed to apply configuration" -ForegroundColor Red
        }
    } else {
        Write-Host "[CANCELLED] Operation cancelled by user" -ForegroundColor Yellow
    }
} else {
    Write-Host "[ERROR] Helm not found. Cannot apply configuration." -ForegroundColor Red
    Write-Host "Alternative: Apply configuration manually using kubectl" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "[STEP 5] Monitoring CPU usage after changes..." -ForegroundColor Green
Write-Host "Check CPU usage with: kubectl top pod my-neo4j-0 -n $namespace" -ForegroundColor Gray
Write-Host ""

Write-Host "=== Optimization Complete ===" -ForegroundColor Cyan





