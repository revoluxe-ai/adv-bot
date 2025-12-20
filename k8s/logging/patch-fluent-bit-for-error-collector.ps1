$ErrorActionPreference = "Stop"

$ns = "logging"
$cmName = "fluent-bit"

$conf = kubectl get configmap $cmName -n $ns -o jsonpath="{.data.fluent-bit\.conf}"
if (-not $conf) {
    Write-Host "ERROR: Cannot read fluent-bit.conf from ConfigMap $ns/$cmName" -ForegroundColor Red
    exit 1
}

if ($conf -match "kube\.errors") {
    Write-Host "kube.errors config already present, skipping." -ForegroundColor Yellow
    exit 0
}

$rewriteTagBlock = @"
[FILTER]
    Name rewrite_tag
    Match kube.*
    Rule `$log (Traceback|Exception|ERROR|CRITICAL|FATAL) kube.errors true
    Emitter_Name error_emitter
    Emitter_Storage.type memory

"@

$httpOutBlock = @"

[OUTPUT]
    Name http
    Match kube.errors
    Host error-collector.logging.svc.cluster.local
    Port 8000
    URI /ingest
    Format json
    Retry_Limit False
"@

# Insert rewrite_tag right before the kubernetes filter so it can see the original `log` field.
# Note: fluent-bit.conf inside ConfigMap is indented, so allow leading spaces.
$pattern = '(?ms)^\s*\[FILTER\]\s*\r?\n\s*Name\s+kubernetes\b'
if (-not ([regex]::IsMatch($conf, $pattern))) {
    Write-Host "ERROR: Cannot find kubernetes filter block in fluent-bit.conf; aborting to avoid breaking config." -ForegroundColor Red
    exit 1
}

$newConf = [regex]::Replace($conf, $pattern, { param($m) $rewriteTagBlock + $m.Value }, 1)
$newConf = $newConf + $httpOutBlock

# Patch ConfigMap using --patch-file to avoid command-line length limits.
$patchObj = @{ data = @{ "fluent-bit.conf" = $newConf } }
$tmpPatch = New-TemporaryFile
try {
    $patchObj | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 $tmpPatch
    kubectl patch configmap $cmName -n $ns --type merge --patch-file $tmpPatch
    Write-Host "ConfigMap $ns/$cmName patched OK." -ForegroundColor Green
} finally {
    Remove-Item $tmpPatch -ErrorAction SilentlyContinue
}

Write-Host "Restarting DaemonSet fluent-bit..." -ForegroundColor Yellow
kubectl rollout restart daemonset/fluent-bit -n $ns

Write-Host "Done. Check logs:" -ForegroundColor Cyan
Write-Host "kubectl logs -n $ns -l app.kubernetes.io/name=fluent-bit --tail=50" -ForegroundColor White


