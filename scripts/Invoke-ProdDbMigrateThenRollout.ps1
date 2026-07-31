<#
.SYNOPSIS
  Apply migrate Job then document Deployment CAS (PowerShell).

.DESCRIPTION
  Staff helper for prod-adv-bot. Prefer protected CI workflow as the sole
  release path. This script is emergency/client of that path, not the gate.

  Deployment updates MUST use JSON Patch test+replace on container image
  (not kubectl set image alone) to avoid TOCTOU.

  EXPECTED_CURRENT_REVISION_SETS is rendered as JSON list-of-lists for
  python -m app.db.migrate (never substitute the bare token EXPECTED_CURRENT
  inside the env var name EXPECTED_CURRENT_REVISION_SETS).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $ReleaseId,

    [Parameter(Mandatory = $true)]
    [string] $ImageDigest,

    [Parameter(Mandatory = $true)]
    [string] $ExpectedTargetRevision,

    [Parameter(Mandatory = $true)]
    [string] $ExpectedCurrentRevision,

    [Parameter(Mandatory = $false)]
    [string[]] $AdditionalAllowedCurrentRevisions = @(),

    [string] $Namespace = "prod-adv-bot",

    [string] $JobTemplate = ".\k8s\jobs\app-db-migrate.yaml",

    [int] $TimeoutSeconds = 1800,

    [switch] $WhatIf
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $JobTemplate)) {
    throw "Job template not found: $JobTemplate"
}

Write-Host "ReleaseId=$ReleaseId ImageDigest=$ImageDigest"
Write-Host "NOTE: Ensure provenance bound manifest hash was verified by CONTROL Job first."

# Build [["rev1"],["rev2"],...] — each revision is its own allowed current set.
# YAML template uses single-quoted value so JSON double-quotes stay literal.
$allCurrent = @($ExpectedCurrentRevision) + @($AdditionalAllowedCurrentRevisions)
$parts = foreach ($rev in $allCurrent) {
    if ([string]::IsNullOrWhiteSpace($rev)) { continue }
    $escaped = $rev.Trim().Replace('\', '\\').Replace('"', '\"').Replace("'", "''")
    "[`"$escaped`"]"
}
if (-not $parts -or @($parts).Count -lt 1) {
    throw "ExpectedCurrentRevision must be non-empty"
}
$expectedCurrentRevisionSetsJson = "[" + (@($parts) -join ",") + "]"

$tmp = New-TemporaryFile
$rendered = (Get-Content -Raw -LiteralPath $JobTemplate) `
    -replace "RELEASE_ID", $ReleaseId `
    -replace "RELEASE_PLATFORM_MANIFEST_DIGEST", $ImageDigest `
    -replace "EXPECTED_TARGET_REVISION", $ExpectedTargetRevision `
    -replace "EXPECTED_CURRENT_REVISION_SETS_JSON", $expectedCurrentRevisionSetsJson

if ($rendered -notmatch "(?m)^\s+value:\s+'\[\[") {
    throw "Rendered Job YAML missing single-quoted EXPECTED_CURRENT_REVISION_SETS JSON (YAML would break on double quotes)."
}

# PowerShell 5.x Set-Content -Encoding utf8 writes BOM; kubectl rejects BOM YAML.
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($tmp.FullName, $rendered, $utf8NoBom)

if ($WhatIf) {
    Write-Host "WhatIf: would apply Job from $($tmp.FullName)"
    Write-Host "EXPECTED_CURRENT_REVISION_SETS=$expectedCurrentRevisionSetsJson"
    Get-Content -LiteralPath $tmp.FullName | Select-Object -First 50
    exit 0
}

$jobName = "app-db-migrate-$ReleaseId"
kubectl apply --dry-run=client -f $tmp.FullName
if ($LASTEXITCODE -ne 0) { throw "kubectl apply --dry-run failed" }
kubectl apply -f $tmp.FullName
if ($LASTEXITCODE -ne 0) { throw "kubectl apply failed" }

# Complete OR Failed — do not wait full timeout when Job already Failed.
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$finished = $false
while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
    $raw = kubectl get "job/$jobName" -n $Namespace -o json 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($raw)) {
        Start-Sleep -Seconds 3
        continue
    }
    $job = $raw | ConvertFrom-Json
    $conditions = @($job.status.conditions)
    $isComplete = $conditions | Where-Object { $_.type -eq "Complete" -and $_.status -eq "True" }
    $isFailed = $conditions | Where-Object { $_.type -eq "Failed" -and $_.status -eq "True" }
    if ($isComplete) {
        $finished = $true
        break
    }
    if ($isFailed) {
        Write-Host "Migrate Job Failed; dumping logs:"
        kubectl logs -n $Namespace -l "job-name=$jobName" --tail=120
        throw "Migrate Job failed; do not rollout. Inspect logs; PARTIAL_OR_UNKNOWN forbids blind retry."
    }
    Start-Sleep -Seconds 5
}
if (-not $finished) {
    throw "Timed out waiting for job/$jobName (neither Complete nor Failed within ${TimeoutSeconds}s)."
}

Write-Host @"
Migrate Job completed. Next: Deployment CAS per frozen manifest, e.g.:

kubectl patch deployment/<name> -n $Namespace --type=json -p "[
  {`"op`":`"test`",`"path`":`"/spec/template/spec/containers/0/image`",`"value`":`"harbor...@sha256:CURRENT`"},
  {`"op`":`"replace`",`"path`":`"/spec/template/spec/containers/0/image`",`"value`":`"harbor...@sha256:$ImageDigest`"}
]"

Do not kubectl set image without test op.
"@
