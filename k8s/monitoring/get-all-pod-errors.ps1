# Get All Pod Errors Script
param(
    [string]$Namespace = "all",
    [string]$Pattern = "error|failed|exception|crash",
    [int]$TailLines = 100,
    [switch]$OnlyProblematicPods
)

Write-Host "======================================================"
Write-Host "GET ALL POD ERRORS - Poisk oshibok vo vsekh podakh"
Write-Host "======================================================"

if ($Namespace -eq "all") {
    Write-Host "Namespace: VSE" -ForegroundColor Cyan
    $namespaces = kubectl get ns -o jsonpath='{.items[*].metadata.name}'
}
else {
    Write-Host "Namespace: $Namespace" -ForegroundColor Cyan
    $namespaces = @($Namespace)
}

$errorCount = 0
$podCount = 0
$podsWithErrors = @()

foreach ($ns in $namespaces.Split(" ")) {
    $ns = $ns.Trim()
    if ([string]::IsNullOrEmpty($ns)) { continue }
    
    Write-Host ""
    Write-Host "───────────────────────────────────────────────────" -ForegroundColor Gray
    Write-Host "Namespace: $ns" -ForegroundColor Cyan
    Write-Host "───────────────────────────────────────────────────" -ForegroundColor Gray
    
    # Get all pods in namespace
    $pods = kubectl get pods -n $ns -o jsonpath='{.items[*].metadata.name}' 2>$null
    
    if ([string]::IsNullOrEmpty($pods)) {
        Write-Host "  (net podov ili oshibka dostupa)" -ForegroundColor Gray
        continue
    }
    
    foreach ($pod in $pods.Split(" ")) {
        $pod = $pod.Trim()
        if ([string]::IsNullOrEmpty($pod)) { continue }
        
        $podCount++
        
        # Get pod status
        $status = kubectl get pod -n $ns $pod -o jsonpath='{.status.phase}' 2>$null
        
        # Get logs
        $logs = kubectl logs -n $ns $pod --tail=$TailLines 2>$null
        
        if ([string]::IsNullOrEmpty($logs)) {
            $logs = kubectl logs -n $ns $pod --previous --tail=$TailLines 2>$null
        }
        
        # Search for errors
        $errors = $logs | Select-String -Pattern $Pattern -AllMatches -IgnoreCase
        
        if ($errors) {
            $podsWithErrors += @{
                Namespace = $ns
                Pod       = $pod
                Status    = $status
                Errors    = $errors
                ErrorCount = $errors.Count
            }
            $errorCount += $errors.Count
            
            Write-Host "  [ERROR] $pod [$status]" -ForegroundColor Red
            foreach ($error in $errors) {
                Write-Host "    > $($error.Line)" -ForegroundColor Red
            }
        }
        elseif (-not $OnlyProblematicPods) {
            Write-Host "  [OK] $pod [$status]" -ForegroundColor Green
        }
    }
}

# Summary
Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "ITOGI:" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "Vsego proverenno podov: $podCount"
Write-Host "Podov s oshibkami: $($podsWithErrors.Count)" -ForegroundColor Red
Write-Host "Vsego strok s oshibkami: $errorCount" -ForegroundColor Red
Write-Host "======================================================" -ForegroundColor Cyan

Write-Host "Done!" -ForegroundColor Green
