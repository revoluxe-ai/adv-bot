<#
.SYNOPSIS
  Диагностика проблем Pending из-за CPU на однонодовом кластере (Insufficient cpu).

.DESCRIPTION
  Скрипт помогает быстро ответить на вопросы:
  - Сколько CPU "зарезервировано" requests на ноде (Allocated resources)?
  - Какие поды/контейнеры забивают CPU requests?
  - Что реально потребляет CPU прямо сейчас (kubectl top)?
  - Какие поды Pending и что пишет scheduler в Events?

.EXAMPLE
  .\k8s\monitoring\diagnose-cpu-scheduling.ps1

.EXAMPLE
  .\k8s\monitoring\diagnose-cpu-scheduling.ps1 -Top 40
#>

[CmdletBinding()]
param(
    [int]$Top = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Convert-CpuToMilli {
    param([AllowNull()][string]$Cpu)

    if ([string]::IsNullOrWhiteSpace($Cpu)) { return 0 }
    $Cpu = $Cpu.Trim()

    if ($Cpu.EndsWith("m")) {
        return [int]($Cpu.TrimEnd("m"))
    }

    # "1", "2", "0.5"
    return [int]([math]::Round(([double]$Cpu) * 1000))
}

function Convert-MemToMi {
    param([AllowNull()][string]$Mem)

    if ([string]::IsNullOrWhiteSpace($Mem)) { return 0 }
    $Mem = $Mem.Trim()

    if ($Mem -match "Ki$") { return [int]([math]::Round(([double]($Mem -replace "Ki$","")) / 1024)) }
    if ($Mem -match "Mi$") { return [int]([double]($Mem -replace "Mi$","")) }
    if ($Mem -match "Gi$") { return [int]([math]::Round(([double]($Mem -replace "Gi$","")) * 1024)) }
    if ($Mem -match "Ti$") { return [int]([math]::Round(([double]($Mem -replace "Ti$","")) * 1024 * 1024)) }

    # bytes (редко)
    if ($Mem -match "^[0-9]+$") { return [int]([math]::Round(([double]$Mem) / 1024 / 1024)) }
    return 0
}

function Try-Run {
    param([scriptblock]$Block)
    try { & $Block } catch { Write-Host "[WARN] $($_.Exception.Message)" -ForegroundColor Yellow }
}

Write-Host "=== CPU Scheduling диагностика ===" -ForegroundColor Cyan
Write-Host "Top entries: $Top" -ForegroundColor Gray
Write-Host ""

Try-Run {
    Write-Host "1) Pending pods + причины (Events):" -ForegroundColor Green
    $pending = kubectl get pods -A --field-selector=status.phase=Pending -o wide 2>&1
    if ($LASTEXITCODE -ne 0) { throw $pending }
    if ([string]::IsNullOrWhiteSpace($pending)) {
        Write-Host "  Нет Pending pods" -ForegroundColor Green
    } else {
        Write-Host $pending
        Write-Host ""
        $pendingPods = kubectl get pods -A --field-selector=status.phase=Pending -o json 2>&1 | ConvertFrom-Json
        foreach ($p in $pendingPods.items) {
            $ns = $p.metadata.namespace
            $name = $p.metadata.name
            Write-Host "  --- describe $ns/$name (Events) ---" -ForegroundColor Cyan
            kubectl describe pod $name -n $ns 2>&1 | Select-String -Pattern "^Events:" -Context 0,50
        }
    }
    Write-Host ""
}

Try-Run {
    Write-Host "2) Allocated resources на ноде (requests vs allocatable):" -ForegroundColor Green
    $node = kubectl get nodes -o jsonpath='{.items[0].metadata.name}' 2>&1
    if ($LASTEXITCODE -ne 0) { throw $node }
    Write-Host "  Node: $node" -ForegroundColor Gray
    kubectl describe node $node 2>&1 | Select-String -Pattern "^Allocated resources:" -Context 0,16
    Write-Host ""
}

Try-Run {
    Write-Host "3) TOP pods по CPU requests (из spec.resources.requests):" -ForegroundColor Green

    $pods = kubectl get pods -A -o json 2>&1 | ConvertFrom-Json
    $rows = New-Object System.Collections.Generic.List[object]

    foreach ($p in $pods.items) {
        $ns = $p.metadata.namespace
        $podName = $p.metadata.name
        $phase = $p.status.phase

        $cpuReqTotal = 0
        $memReqTotalMi = 0

        foreach ($c in $p.spec.containers) {
            $cpuReq = Convert-CpuToMilli $c.resources.requests.cpu
            $memReqMi = Convert-MemToMi $c.resources.requests.memory
            $cpuReqTotal += $cpuReq
            $memReqTotalMi += $memReqMi
        }

        $rows.Add([pscustomobject]@{
            Namespace = $ns
            Pod       = $podName
            Phase     = $phase
            CpuReq_m  = $cpuReqTotal
            MemReq_Mi = $memReqTotalMi
        })
    }

    $rows |
        Sort-Object CpuReq_m -Descending |
        Select-Object -First $Top |
        Format-Table -AutoSize

    Write-Host ""
    Write-Host "Подсказка: если node Allocated cpu requests > 90%, новый rollout с maxSurge>0 часто упрётся в Insufficient cpu." -ForegroundColor Yellow
    Write-Host ""
}

Try-Run {
    Write-Host "4) Фактическое потребление (kubectl top pods -A --sort-by=cpu):" -ForegroundColor Green
    $topOut = kubectl top pods -A --sort-by=cpu 2>&1
    if ($LASTEXITCODE -ne 0) { throw $topOut }
    $topOut | Select-Object -First ($Top + 1)
    Write-Host ""
}

Write-Host "=== Рекомендации (коротко) ===" -ForegroundColor Cyan
Write-Host "1) Снижать именно requests.cpu у 'толстых' подов (это влияет на scheduling)." -ForegroundColor Gray
Write-Host "2) Для однонодового кластера на время rollout: выставить maxSurge=0, maxUnavailable=1 (см. patch-rollout-strategy.yaml)." -ForegroundColor Gray
Write-Host "3) Ориентируйтесь на kubectl top + запас; requests обычно 1.2x-2x от p95 usage." -ForegroundColor Gray
Write-Host ""








