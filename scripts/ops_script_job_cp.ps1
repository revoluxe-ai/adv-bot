<#
.SYNOPSIS
  Retry kubectl cp из Running ops-script pod с backoff и проверкой sha256.

.DESCRIPTION
  Общий helper для /opsx-scripts RUN: копирует declared outputs из pod
  пока контейнер в hold window (Running). Не полагается на один cp-вызов;
  переживает кратковременные kubectl TLS timeout.

  Успех = все Files скопированы локально; если задан PrimaryFile — файл
  существует и digest совпадает с sidecar *.sha256 или ExpectedPrimarySha256.

.PARAMETER PodName
  Имя pod (job-name suffix).

.PARAMETER Namespace
  Kubernetes namespace (default prod-adv-bot).

.PARAMETER Container
  Container name (default ops-script).

.PARAMETER RemoteDir
  Каталог в pod, например /app/scripts/wb_api_readonly_ops/outputs

.PARAMETER LocalOutputDir
  Локальный каталог назначения (создаётся при необходимости).

.PARAMETER Files
  Список имён файлов для копирования (basename).

.PARAMETER PrimaryFile
  Имя primary artifact для sha256 gate (optional but recommended).

.PARAMETER ExpectedPrimarySha256
  Ожидаемый digest primary (optional; иначе читается из sidecar).

.PARAMETER MaxAttempts
  Максимум попыток cp-цикла (default 36 ≈ 15 min при backoff).

.PARAMETER InitialBackoffSec
  Начальный backoff между попытками.

.PARAMETER MaxBackoffSec
  Потолок backoff.

.EXAMPLE
  .\scripts\ops_script_job_cp.ps1 `
    -PodName ops-script-wb-ro-...-abc12 `
    -RemoteDir /app/scripts/wb_api_readonly_ops/outputs `
    -LocalOutputDir .tmp\opsx-scripts\run\outputs `
    -Files @('COL-R04-003B_ORDERS_FAMILY_PREFLIGHT_RETURN.zip',
             'COL-R04-003B_ORDERS_FAMILY_PREFLIGHT_RETURN.zip.sha256',
             'report.json') `
    -PrimaryFile COL-R04-003B_ORDERS_FAMILY_PREFLIGHT_RETURN.zip
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $PodName,

    [string] $Namespace = "prod-adv-bot",

    [string] $Container = "ops-script",

    [Parameter(Mandatory = $true)]
    [string] $RemoteDir,

    [Parameter(Mandatory = $true)]
    [string] $LocalOutputDir,

    [Parameter(Mandatory = $true)]
    [string[]] $Files,

    [string] $PrimaryFile = "",

    [string] $ExpectedPrimarySha256 = "",

    [int] $MaxAttempts = 36,

    [int] $InitialBackoffSec = 5,

    [int] $MaxBackoffSec = 60
)

$ErrorActionPreference = "Stop"

function Get-PodPhase {
    param([string] $Name, [string] $Ns)
    $phase = kubectl get pod $Name -n $Ns -o jsonpath='{.status.phase}' 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($phase)) {
        return "Unknown"
    }
    return $phase.Trim()
}

function Test-AllLocalFilesPresent {
    param([string] $Dir, [string[]] $Names)
    foreach ($name in $Names) {
        $path = Join-Path $Dir $name
        if (-not (Test-Path -LiteralPath $path)) {
            return $false
        }
        if ((Get-Item -LiteralPath $path).Length -le 0) {
            return $false
        }
    }
    return $true
}

function Get-PrimarySha256FromSidecar {
    param([string] $Dir, [string] $Primary, [string[]] $AllFiles)
    $sidecarName = "$Primary.sha256"
    if ($AllFiles -notcontains $sidecarName) {
        return $null
    }
    $sidecarPath = Join-Path $Dir $sidecarName
    if (-not (Test-Path -LiteralPath $sidecarPath)) {
        return $null
    }
    $line = (Get-Content -LiteralPath $sidecarPath -Raw).Trim()
    if ($line -match '^([0-9a-fA-F]{64})\s') {
        return $Matches[1].ToLowerInvariant()
    }
    return $null
}

function Test-PrimarySha256Gate {
    param(
        [string] $Dir,
        [string] $Primary,
        [string[]] $AllFiles,
        [string] $Expected
    )
    if ([string]::IsNullOrWhiteSpace($Primary)) {
        return $true
    }
    $primaryPath = Join-Path $Dir $Primary
    if (-not (Test-Path -LiteralPath $primaryPath)) {
        return $false
    }
    $onDisk = (Get-FileHash -LiteralPath $primaryPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $expectedNorm = $Expected.Trim().ToLowerInvariant()
    if (-not [string]::IsNullOrWhiteSpace($expectedNorm)) {
        return $onDisk -eq $expectedNorm
    }
    $fromSidecar = Get-PrimarySha256FromSidecar -Dir $Dir -Primary $Primary -AllFiles $AllFiles
    if ($null -ne $fromSidecar) {
        return $onDisk -eq $fromSidecar
    }
    return $true
}

if (-not (Test-Path -LiteralPath $LocalOutputDir)) {
    New-Item -ItemType Directory -Path $LocalOutputDir -Force | Out-Null
}

$remoteDirNorm = ($RemoteDir -replace '\\', '/').TrimEnd('/')
if (-not $remoteDirNorm.StartsWith('/')) {
    $remoteDirNorm = "/$remoteDirNorm"
}
$backoff = $InitialBackoffSec
$lastPhase = ""
$attempt = 0

while ($attempt -lt $MaxAttempts) {
    $attempt++
    $phase = Get-PodPhase -Name $PodName -Ns $Namespace
    if ($phase -ne $lastPhase) {
        Write-Host "ops_script_job_cp: pod phase=$phase attempt=$attempt/$MaxAttempts"
        $lastPhase = $phase
    }

    if ($phase -eq "Succeeded" -or $phase -eq "Failed") {
        break
    }

    if ($phase -eq "Running") {
        Push-Location -LiteralPath $LocalOutputDir
        try {
            foreach ($file in $Files) {
                $localPath = Join-Path (Get-Location) $file
                if (Test-Path -LiteralPath $localPath) {
                    if ((Get-Item -LiteralPath $localPath).Length -gt 0) {
                        continue
                    }
                }
                $remotePath = "$remoteDirNorm/$file"
                $src = "${Namespace}/${PodName}:${remotePath}"
                Write-Host "ops_script_job_cp: cp ${src} -> ${localPath}"
                & kubectl cp $src $file -c $Container 2>&1 | ForEach-Object { Write-Host $_ }
            }
        } finally {
            Pop-Location
        }

        if ((Test-AllLocalFilesPresent -Dir $LocalOutputDir -Names $Files) -and
            (Test-PrimarySha256Gate -Dir $LocalOutputDir -Primary $PrimaryFile -AllFiles $Files -Expected $ExpectedPrimarySha256)) {
            $primaryPath = if ($PrimaryFile) { Join-Path $LocalOutputDir $PrimaryFile } else { "" }
            $digest = if ($primaryPath -and (Test-Path -LiteralPath $primaryPath)) {
                (Get-FileHash -LiteralPath $primaryPath -Algorithm SHA256).Hash.ToLowerInvariant()
            } else { "" }
            Write-Host "LOCAL_ARTIFACT_HANDOFF=PASS"
            Write-Host "LOCAL_OUTPUT_DIR=$((Resolve-Path -LiteralPath $LocalOutputDir).Path)"
            if ($PrimaryFile) {
                Write-Host "PRIMARY_LOCAL=$((Resolve-Path -LiteralPath $primaryPath).Path)"
                Write-Host "PRIMARY_SHA256=$digest"
            }
            exit 0
        }
    }

    Start-Sleep -Seconds $backoff
    $backoff = [Math]::Min($backoff * 2, $MaxBackoffSec)
}

Write-Host "LOCAL_ARTIFACT_HANDOFF=FAIL"
Write-Host "ops_script_job_cp: exhausted attempts or pod terminated before copy"
Get-ChildItem -LiteralPath $LocalOutputDir -ErrorAction SilentlyContinue |
    Format-Table Name, Length
exit 1
