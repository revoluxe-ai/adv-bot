<#
.SYNOPSIS
  Apply migrate Job then document Deployment CAS (PowerShell).

.DESCRIPTION
  Staff helper for prod-adv-bot. Prefer protected CI workflow as the sole
  release path. This script is emergency/client of that path, not the gate.

  Deployment updates MUST use JSON Patch test+replace on container image
  (not kubectl set image alone) to avoid TOCTOU.

  EXPECTED_CURRENT_REVISION_SETS is rendered as JSON list-of-lists for
  python -m app.db.migrate. Template placeholders use __TOKEN__ form so
  value substitution cannot rewrite YAML env key names.
  BackfillKind is empty for ordinary releases and explicit for a one-time
  classifier-owned data transition.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $ReleaseId,

    [Parameter(Mandatory = $true)]
    [string] $ImageRef,

    [Parameter(Mandatory = $true)]
    [string] $ExpectedTargetRevision,

    [Parameter(Mandatory = $true)]
    [string] $ExpectedCurrentRevision,

    [Parameter(Mandatory = $false)]
    [string] $BackfillKind = "",

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

Write-Host "ReleaseId=$ReleaseId ImageRef=$ImageRef"
Write-Host "NOTE: Ensure provenance bound manifest hash was verified by CONTROL Job first."

# Build [["rev1"],["rev2"],...] — each revision is its own allowed current set.
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

# Job name suffix: DNS-1123-ish (lowercase alnum and '-')
$jobSuffix = ($ReleaseId.ToLower() -replace '[^a-z0-9-]', '-').Trim('-')
if ([string]::IsNullOrWhiteSpace($jobSuffix)) {
    throw "ReleaseId produced empty job name suffix"
}

$tmp = New-TemporaryFile
$rendered = (Get-Content -Raw -LiteralPath $JobTemplate) `
    -replace "__JOB_NAME_SUFFIX__", $jobSuffix `
    -replace "__RELEASE_ID__", $ReleaseId `
    -replace "__IMAGE_REF__", $ImageRef `
    -replace "__EXPECTED_TARGET_REVISION__", $ExpectedTargetRevision `
    -replace "__EXPECTED_CURRENT_REVISION_SETS_JSON__", $expectedCurrentRevisionSetsJson `
    -replace "__MIGRATION_BACKFILL_KIND__", $BackfillKind

if ($rendered -match "__[A-Z0-9_]+__") {
    throw "Unresolved template placeholders remain in rendered Job YAML."
}
if ($rendered -notmatch "(?m)^\s+value:\s+'\[\[") {
    throw "Rendered Job YAML missing single-quoted EXPECTED_CURRENT_REVISION_SETS JSON."
}

# PowerShell 5.x Set-Content -Encoding utf8 writes BOM; kubectl rejects BOM YAML.
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($tmp.FullName, $rendered, $utf8NoBom)

if ($WhatIf) {
    Write-Host "WhatIf: would apply Job from $($tmp.FullName)"
    Write-Host "EXPECTED_CURRENT_REVISION_SETS=$expectedCurrentRevisionSetsJson"
    Get-Content -LiteralPath $tmp.FullName | Select-Object -First 55
    exit 0
}

$jobName = "app-db-migrate-$jobSuffix"
kubectl apply --dry-run=client -f $tmp.FullName
if ($LASTEXITCODE -ne 0) { throw "kubectl apply --dry-run failed" }
kubectl apply -f $tmp.FullName
if ($LASTEXITCODE -ne 0) { throw "kubectl apply failed" }

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
  {`"op`":`"replace`",`"path`":`"/spec/template/spec/containers/0/image`",`"value`":`"$ImageRef`"}
]"

Do not kubectl set image without test op.
"@
