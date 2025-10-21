# ═══════════════════════════════════════════════════════════════════════════════
# GRAFANA - БЫСТРОЕ РЕШЕНИЕ ПРОБЛЕМЫ С ЛОГИНОМ
# ═══════════════════════════════════════════════════════════════════════════════

param(
    [switch]$FixPassword,
    [switch]$CheckPod,
    [switch]$ShowPassword,
    [switch]$PortForward
)

# Цвета для вывода
$colors = @{
    Success = "Green"
    Error   = "Red"
    Info    = "Cyan"
    Warning = "Yellow"
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# ═══════════════════════════════════════════════════════════════════════════════
# ПРОВЕРКА POD
# ═══════════════════════════════════════════════════════════════════════════════

function Check-GrafanaPod {
    Write-ColorOutput "`n🔍 Проверяю статус Grafana pod..." $colors.Info
    
    $pod = kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].metadata.name}'
    $status = kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].status.phase}'
    $ready = kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}'
    
    if ($pod -and $status -eq "Running" -and $ready -eq "True") {
        Write-ColorOutput "✅ Pod работает: $pod" $colors.Success
        return $true
    }
    else {
        Write-ColorOutput "❌ Pod проблема: $pod (статус: $status, ready: $ready)" $colors.Error
        return $false
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# ПОЛУЧИТЬ ПАРОЛЬ
# ═══════════════════════════════════════════════════════════════════════════════

function Get-GrafanaPassword {
    Write-ColorOutput "`n🔑 Получаю пароль из Secret..." $colors.Info
    
    $encodedPassword = kubectl get secret -n kube-prometheus-stack kube-prometheus-stack-grafana `
        -o jsonpath="{.data.admin-password}"
    
    if ($encodedPassword) {
        $password = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($encodedPassword))
        Write-ColorOutput "✅ Пароль: $password" $colors.Success
        return $password
    }
    else {
        Write-ColorOutput "❌ Не смог получить пароль" $colors.Error
        return $null
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# ПЕРЕСОЗДАТЬ POD
# ═══════════════════════════════════════════════════════════════════════════════

function Recreate-GrafanaPod {
    Write-ColorOutput "`n🔄 Пересоздаю Grafana pod..." $colors.Warning
    
    kubectl delete pod -n kube-prometheus-stack -l app.kubernetes.io/name=grafana
    
    Write-ColorOutput "⏳ Жду пока pod перезагрузится (это займет 30-40 секунд)..." $colors.Info
    
    $counter = 0
    $maxWait = 60
    
    while ($counter -lt $maxWait) {
        $pod = kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].metadata.name}' 2>$null
        $status = kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].status.phase}' 2>$null
        $ready = kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>$null
        
        if ($pod -and $status -eq "Running" -and $ready -eq "True") {
            Write-ColorOutput "✅ Pod успешно пересоздан: $pod" $colors.Success
            return $true
        }
        
        Write-ColorOutput "⏳ Ждем... ($counter/$maxWait сек)" $colors.Info
        Start-Sleep -Seconds 2
        $counter += 2
    }
    
    Write-ColorOutput "❌ Timeout: pod не запустился за 60 секунд" $colors.Error
    return $false
}

# ═══════════════════════════════════════════════════════════════════════════════
# ЗАПУСТИТЬ PORT-FORWARD
# ═══════════════════════════════════════════════════════════════════════════════

function Start-PortForward {
    Write-ColorOutput "`n📡 Запускаю port-forward..." $colors.Info
    
    # Проверяем занят ли порт
    $existingProcess = Get-Process | Where-Object { $_.ProcessName -eq "kubectl" } | 
        Where-Object { $_.CommandLine -like "*port-forward*3000*" }
    
    if ($existingProcess) {
        Write-ColorOutput "⚠️  Port-forward уже запущен на процессе $($existingProcess.Id)" $colors.Warning
        Write-ColorOutput "✅ Графана доступна на: http://localhost:3000" $colors.Success
        return
    }
    
    Write-ColorOutput "▶️  Запускаю: kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80" $colors.Info
    Write-ColorOutput "⚠️  Это окно должно остаться открытым!" $colors.Warning
    
    # Запускаем port-forward (это будет блокирующая операция)
    kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
}

# ═══════════════════════════════════════════════════════════════════════════════
# ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════════════════════════════════

function Show-Menu {
    Write-ColorOutput "`n═══════════════════════════════════════════════════════════════════════════════" $colors.Info
    Write-ColorOutput "              GRAFANA - БЫСТРОЕ РЕШЕНИЕ ПРОБЛЕМЫ С ЛОГИНОМ" $colors.Info
    Write-ColorOutput "═══════════════════════════════════════════════════════════════════════════════" $colors.Info
    
    Write-ColorOutput "`nВыберите действие:" $colors.Info
    Write-Host "1. ✅ Полный Fix (пересоздать pod + проверить + показать пароль)"
    Write-Host "2. 🔍 Проверить статус pod"
    Write-Host "3. 🔄 Пересоздать pod"
    Write-Host "4. 🔑 Показать пароль из Secret"
    Write-Host "5. 📡 Запустить port-forward"
    Write-Host "6. 🚀 Быстрый старт (check + password + port-forward)"
    Write-Host "0. ❌ Выход"
    
    Write-ColorOutput "`nИли используйте флаги из командной строки:" $colors.Info
    Write-Host "powershell ./k8s/grafana-fix.ps1 -FixPassword"
    Write-Host "powershell ./k8s/grafana-fix.ps1 -CheckPod"
    Write-Host "powershell ./k8s/grafana-fix.ps1 -ShowPassword"
    Write-Host "powershell ./k8s/grafana-fix.ps1 -PortForward"
}

# ═══════════════════════════════════════════════════════════════════════════════
# ОСНОВНОЙ КОД
# ═══════════════════════════════════════════════════════════════════════════════

# Если указаны флаги, выполнить их
if ($CheckPod) {
    Check-GrafanaPod
    exit
}

if ($ShowPassword) {
    Get-GrafanaPassword
    exit
}

if ($FixPassword) {
    Write-ColorOutput "🚀 Полный Fix в процессе..." $colors.Warning
    
    Recreate-GrafanaPod
    
    if ($?) {
        $password = Get-GrafanaPassword
        
        Write-ColorOutput "`n✅ POD ГОТОВ!" $colors.Success
        Write-ColorOutput "Ваши учетные данные:" $colors.Success
        Write-ColorOutput "  Username: admin" $colors.Success
        Write-ColorOutput "  Password: $password" $colors.Success
        Write-ColorOutput "`nОткройте в браузере: http://localhost:3000" $colors.Success
    }
    exit
}

if ($PortForward) {
    Start-PortForward
    exit
}

# Если флагов нет - показать меню
Show-Menu

$choice = Read-Host "`nВаш выбор"

switch ($choice) {
    "1" {
        Write-ColorOutput "`n🚀 Полный Fix..." $colors.Warning
        
        Recreate-GrafanaPod
        
        if ($?) {
            Start-Sleep -Seconds 5
            $password = Get-GrafanaPassword
            
            Write-ColorOutput "`n═══════════════════════════════════════════════════════════════════════════════" $colors.Success
            Write-ColorOutput "✅ УСПЕШНО!" $colors.Success
            Write-ColorOutput "═══════════════════════════════════════════════════════════════════════════════" $colors.Success
            Write-ColorOutput "`nУчетные данные для входа:" $colors.Success
            Write-ColorOutput "  👤 Username: admin" $colors.Success
            Write-ColorOutput "  🔐 Password: $password" $colors.Success
            Write-ColorOutput "`nОткройте в браузере: http://localhost:3000" $colors.Success
            Write-ColorOutput "═══════════════════════════════════════════════════════════════════════════════" $colors.Success
        }
    }
    
    "2" {
        Check-GrafanaPod
    }
    
    "3" {
        Recreate-GrafanaPod
    }
    
    "4" {
        Get-GrafanaPassword
    }
    
    "5" {
        Start-PortForward
    }
    
    "6" {
        Write-ColorOutput "`n🚀 Быстрый старт..." $colors.Warning
        
        Check-GrafanaPod
        $password = Get-GrafanaPassword
        
        Write-ColorOutput "`n✅ Все готово! Учетные данные:" $colors.Success
        Write-ColorOutput "  Username: admin" $colors.Success
        Write-ColorOutput "  Password: $password" $colors.Success
        
        Write-ColorOutput "`nЗапускаю port-forward..." $colors.Info
        Start-PortForward
    }
    
    "0" {
        Write-ColorOutput "`n👋 До свидания!" $colors.Info
    }
    
    default {
        Write-ColorOutput "`n❌ Неверный выбор!" $colors.Error
    }
}
