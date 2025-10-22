$ErrorActionPreference = "Stop"

param(
  [string]$KubeConfig = ".\k8s\new-cluster\new-cluster-config.yaml",
  [string]$OutDir = ".\k8s\cluster-snapshots\new-cluster"
)

if (!(Test-Path $KubeConfig)) {
  Write-Error "Kubeconfig not found: $KubeConfig"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Save-Json($name, $cmd) {
  $path = Join-Path $OutDir $name
  Write-Host "Collecting $name"
  $result = Invoke-Expression $cmd
  $result | Out-File -FilePath $path -Encoding UTF8
}

$K = "kubectl --kubeconfig $KubeConfig"

# Core lists
Save-Json "nodes.json" "$K get nodes -o json"
Save-Json "namespaces.json" "$K get ns -o json"
Save-Json "pods.json" "$K get pods -A -o json"
Save-Json "services.json" "$K get svc -A -o json"
Save-Json "deployments.json" "$K get deploy -A -o json"
Save-Json "statefulsets.json" "$K get sts -A -o json"
Save-Json "daemonsets.json" "$K get ds -A -o json"
Save-Json "ingresses.json" "$K get ing -A -o json"
Save-Json "configmaps.json" "$K get cm -A -o json"
Save-Json "secrets.json" "$K get secret -A -o json"
Save-Json "pvcs.json" "$K get pvc -A -o json"
Save-Json "pvs.json" "$K get pv -o json"

# Top (may require metrics-server)
try { Save-Json "top-nodes.txt" "$K top nodes" } catch { Write-Warning $_ }
try { Save-Json "top-pods.txt" "$K top pods -A" } catch { Write-Warning $_ }

Write-Host "Done. Output: $OutDir"


