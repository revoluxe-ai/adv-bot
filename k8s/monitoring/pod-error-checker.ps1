# 🚨 Pod Error Monitoring Tool for PowerShell
# Быстрый мониторинг ошибок в подах

param(
    [string]$Namespace = "default",
    [int]$PodLimit = 50
)

# Цвета
$Colors = @{
    Green = 'DarkGreen'
    Red = 'Red'
    Yellow = 'Yellow'
    Cyan = 'Cyan'
    White = 'White'
}

function Write-Header {
    param([string]$Text)
    Write-Host "════════════════════════════════════════" -ForegroundColor $Colors.Cyan
    Write-Host "🚨 $Text" -ForegroundColor $Colors.White -BackgroundColor Black
    Write-Host "════════════════════════════════════════" -ForegroundColor $Colors.Cyan
}

function Write-Section {
    param([string]$Text)
    Write-Host "`n➜ $Text" -ForegroundColor $Colors.Cyan
}

function Write-Ok {
    param([string]$Text)
    Write-Host "✓ $Text" -ForegroundColor $Colors.Green
}

function Write-Error {
    param([string]$Text)
    Write-Host "✗ $Text" -ForegroundColor $Colors.Red
}

function Write-Warn {
    param([string]$Text)
    Write-Host "⚠ $Text" -ForegroundColor $Colors.Yellow
}

Write-Header "POD ERROR MONITORING - $Namespace"

# 1. Поды не в Running статусе
Write-Section "Поды не в Running статусе (КРИТИЧНО)"
try {
    $problematicPods = kubectl get pods -n $Namespace --field-selector=status.phase!=Running --no-headers 2>$null
    if ($problematicPods) {
        $problematicPods | ForEach-Object {
            $parts = $_ -split '\s+'
            $podName = $parts[0]
            $status = $parts[2]
            Write-Error "$podName - Status: $status"
        }
    } else {
        Write-Ok "Нет подов в проблемных статусах"
    }
} catch {
    Write-Error "Ошибка при получении подов: $_"
}

# 2. Поды с ImagePullBackOff
Write-Section "Проблемы с загрузкой образов"
try {
    $imagePullIssues = kubectl get pods -n $Namespace -o json | ConvertFrom-Json | 
        Select-Object -ExpandProperty items | 
        Where-Object { 
            $_.status.containerStatuses.state.waiting.reason -eq 'ImagePullBackOff' -or 
            $_.status.containerStatuses.state.waiting.reason -eq 'ErrImagePull'
        }
    
    if ($imagePullIssues) {
        $imagePullIssues | ForEach-Object {
            $podName = $_.metadata.name
            $reason = $_.status.containerStatuses[0].state.waiting.reason
            Write-Error "$podName - Reason: $reason"
        }
    } else {
        Write-Ok "Нет проблем с загрузкой образов"
    }
} catch {
    Write-Error "Ошибка при проверке образов: $_"
}

# 3. Все поды в статусе Pending
Write-Section "Поды в статусе Pending (зависают)"
try {
    $pendingPods = kubectl get pods -n $Namespace --field-selector=status.phase=Pending --no-headers 2>$null
    if ($pendingPods) {
        $pendingPods | ForEach-Object {
            $parts = $_ -split '\s+'
            $podName = $parts[0]
            Write-Warn "$podName - Pending"
        }
    } else {
        Write-Ok "Нет зависших подов"
    }
} catch {
    Write-Error "Ошибка при получении Pending подов: $_"
}

# 4. Поды с рестартами
Write-Section "Поды с рестартами"
try {
    $allPods = kubectl get pods -n $Namespace -o json | ConvertFrom-Json | Select-Object -ExpandProperty items
    $restartsFound = 0
    
    $allPods | ForEach-Object {
        $podName = $_.metadata.name
        $restarts = $_.status.containerStatuses[0].restartCount
        if ($restarts -gt 0) {
            Write-Warn "$podName - Restarts: $restarts"
            $restartsFound++
        }
    }
    
    if ($restartsFound -eq 0) {
        Write-Ok "Нет подов с рестартами"
    }
} catch {
    Write-Error "Ошибка при проверке рестартов: $_"
}

# 5. События с ошибками
Write-Section "Последние ошибочные события"
try {
    $events = kubectl get events -n $Namespace --sort-by='.lastTimestamp' 2>$null | 
        Select-String -Pattern 'Failed|Error|ImagePull' | Select-Object -Last 10
    
    if ($events) {
        $events | ForEach-Object {
            Write-Error $_
        }
    } else {
        Write-Ok "Нет ошибочных событий"
    }
} catch {
    Write-Error "Ошибка при получении событий: $_"
}

# 6. Статистика по подам
Write-Section "Статистика по подам"
try {
    $allPods = kubectl get pods -n $Namespace -o json | ConvertFrom-Json | Select-Object -ExpandProperty items
    $running = 0
    $pending = 0
    $failed = 0
    
    $allPods | ForEach-Object {
        $phase = $_.status.phase
        switch ($phase) {
            'Running' { $running++ }
            'Pending' { $pending++ }
            'Failed' { $failed++ }
        }
    }
    
    Write-Ok "Running: $running"
    if ($pending -gt 0) { Write-Warn "Pending: $pending" }
    if ($failed -gt 0) { Write-Error "Failed: $failed" }
} catch {
    Write-Error "Ошибка при подсчете статистики: $_"
}

# 7. Топ подов по рестартам
Write-Section "Топ 10 подов по количеству рестартов"
try {
    $topRestarts = kubectl get pods -n $Namespace -o json | ConvertFrom-Json | 
        Select-Object -ExpandProperty items | 
        Select-Object @{N='Pod';E={$_.metadata.name}}, @{N='Restarts';E={$_.status.containerStatuses[0].restartCount}} |
        Where-Object { $_.Restarts -gt 0 } |
        Sort-Object -Property Restarts -Descending | 
        Select-Object -First 10
    
    if ($topRestarts) {
        $topRestarts | ForEach-Object {
            if ($_.Restarts -gt 5) {
                Write-Error "$($_.Pod) - $($_.Restarts) restarts"
            } else {
                Write-Warn "$($_.Pod) - $($_.Restarts) restarts"
            }
        }
    } else {
        Write-Ok "Нет подов с рестартами"
    }
} catch {
    Write-Error "Ошибка при получении топа рестартов: $_"
}

Write-Host "`n════════════════════════════════════════" -ForegroundColor $Colors.Cyan
Write-Host "✓ Мониторинг завершен" -ForegroundColor $Colors.Green
Write-Host "════════════════════════════════════════" -ForegroundColor $Colors.Cyan

# Рекомендации
Write-Host "`n💡 Рекомендации для расследования:" -ForegroundColor $Colors.Cyan
Write-Host "1. Посмотреть логи:       kubectl logs -n $Namespace POD_NAME" -ForegroundColor $Colors.White
Write-Host "2. Описание пода:        kubectl describe pod -n $Namespace POD_NAME" -ForegroundColor $Colors.White
Write-Host "3. События в namespace:  kubectl get events -n $Namespace --sort-by='.lastTimestamp'" -ForegroundColor $Colors.White
Write-Host ""

