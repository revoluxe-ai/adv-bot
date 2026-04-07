$ErrorActionPreference = "Stop"

$ns = "logging"
$cmName = "fluent-bit"

$conf = kubectl get configmap $cmName -n $ns -o jsonpath="{.data.fluent-bit\.conf}"
if (-not $conf) {
    Write-Host "ERROR: Cannot read fluent-bit.conf from ConfigMap $ns/$cmName" -ForegroundColor Red
    exit 1
}

$rewriteTagBlock = @"
[FILTER]
    Name rewrite_tag
    Match kube.var.log.containers.*
    Rule `$log (?i)(traceback|exception|error|critical|fatal) kube.errors true
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

$lokiOutBlock = @"

[OUTPUT]
    Name loki
    Match kube.var.log.containers.*
    Host loki.logging.svc.cluster.local
    Port 3100
    Labels job=fluent-bit, namespace=`$kubernetes_namespace_name, pod=`$kubernetes_pod_name, container=`$kubernetes_container_name
    Line_Format json
    Retry_Limit False
"@

# Normalize source matches to avoid recursive kubernetes filter warnings on kube.errors
$newConf = $conf
$newConf = $newConf -replace '(?m)^(\s*Match\s+)kube\.\*$', '${1}kube.var.log.containers.*'

if ($newConf -notmatch "(?ms)^\s*\[FILTER\]\s*\r?\n\s*Name\s+rewrite_tag\b.*?kube\.errors") {
    $pattern = '(?ms)^\s*\[FILTER\]\s*\r?\n\s*Name\s+kubernetes\b'
    if (-not ([regex]::IsMatch($newConf, $pattern))) {
        Write-Host "ERROR: Cannot find kubernetes filter block in fluent-bit.conf; aborting to avoid breaking config." -ForegroundColor Red
        exit 1
    }
    $newConf = [regex]::Replace($newConf, $pattern, { param($m) $rewriteTagBlock + $m.Value }, 1)
}

if ($newConf -notmatch "(?ms)^\s*\[OUTPUT\]\s*\r?\n\s*Name\s+http\b.*?error-collector\.logging\.svc\.cluster\.local") {
    $newConf = $newConf + $httpOutBlock
}

if ($newConf -notmatch "(?ms)^\s*\[OUTPUT\]\s*\r?\n\s*Name\s+loki\b") {
    $newConf = $newConf + $lokiOutBlock
}

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


