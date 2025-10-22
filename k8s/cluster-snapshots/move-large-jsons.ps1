$ErrorActionPreference = "Stop"

$srcFiles = @(
  "pods.json",
  "services.json",
  "deployments.json",
  "daemonsets.json",
  "statefulsets.json",
  "ingresses.json",
  "pvcs.json",
  "pvs.json",
  "configmaps.json"
)

$dstDir = ".\k8s\cluster-snapshots\imported"
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null

foreach ($f in $srcFiles) {
  if (Test-Path $f) {
    Write-Host "Moving $f -> $dstDir"
    Move-Item -Force -Path $f -Destination $dstDir
  } else {
    Write-Host "Skip: $f not found"
  }
}

Write-Host "Done."


