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

    [switch] $WhatIf
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $JobTemplate)) {
    throw "Job template not found: $JobTemplate"
}

Write-Host "ReleaseId=$ReleaseId ImageDigest=$ImageDigest"
Write-Host "NOTE: Ensure provenance bound manifest hash was verified by CONTROL Job first."

# Build [["rev1"],["rev2"],...] — each revision is its own allowed current set.
$allCurrent = @($ExpectedCurrentRevision) + @($AdditionalAllowedCurrentRevisions)
$parts = foreach ($rev in $allCurrent) {
    if ([string]::IsNullOrWhiteSpace($rev)) { continue }
    $escaped = $rev.Trim().Replace('\', '\\').Replace('"', '\"')
    "[`"$escaped`"]"
}
if (-not $parts -or @($parts).Count -lt 1) {
    throw "ExpectedCurrentRevision must be non-empty"
}
$expectedCurrentRevisionSetsJson = "[" + (@($parts) -join ",") + "]"

$tmp = New-TemporaryFile
(Get-Content -Raw -LiteralPath $JobTemplate) `
    -replace "RELEASE_ID", $ReleaseId `
    -replace "RELEASE_PLATFORM_MANIFEST_DIGEST", $ImageDigest `
    -replace "EXPECTED_TARGET_REVISION", $ExpectedTargetRevision `
    -replace "EXPECTED_CURRENT_REVISION_SETS_JSON", $expectedCurrentRevisionSetsJson `
    | Set-Content -Path $tmp -Encoding utf8

if ($WhatIf) {
    Write-Host "WhatIf: would apply Job from $tmp"
    Write-Host "EXPECTED_CURRENT_REVISION_SETS=$expectedCurrentRevisionSetsJson"
    Get-Content $tmp | Select-Object -First 50
    exit 0
}

kubectl apply --dry-run=client -f $tmp
kubectl apply -f $tmp
kubectl wait --for=condition=complete "job/app-db-migrate-$ReleaseId" -n $Namespace --timeout=1800s
if ($LASTEXITCODE -ne 0) {
    throw "Migrate Job failed; do not rollout. Inspect logs; PARTIAL_OR_UNKNOWN forbids blind retry."
}

Write-Host @"
Migrate Job completed. Next: Deployment CAS per frozen manifest, e.g.:

kubectl patch deployment/<name> -n $Namespace --type=json -p "[
  {`"op`":`"test`",`"path`":`"/spec/template/spec/containers/0/image`",`"value`":`"harbor...@sha256:CURRENT`"},
  {`"op`":`"replace`",`"path`":`"/spec/template/spec/containers/0/image`",`"value`":`"harbor...@sha256:$ImageDigest`"}
]"

Do not kubectl set image without test op.
"@
