# Bebra Proxy Location Switch Runbook (No Downtime)

## Scope
This runbook rotates Bebra location for `wb-sky-bot` using blue/green proxy deployments in `prod-adv-bot`.

## Prerequisites
- New Bebra JSON config is available locally.
- Current active proxy is `bebra-shared-proxy` (blue).

## 1) Create green secrets from new config
```powershell
kubectl create secret generic bebra-proxy-config-green `
  -n prod-adv-bot `
  --from-file=config.json="C:\path\to\new-bebra-profile.json" `
  --dry-run=client -o yaml | kubectl apply -f -
```

```powershell
$raw = kubectl get secret bebra-proxy-config-green -n prod-adv-bot -o jsonpath='{.data.config\.json}'
$json = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($raw))
$obj = $json | ConvertFrom-Json
kubectl delete secret bebra-proxy-params-green -n prod-adv-bot --ignore-not-found
kubectl create secret generic bebra-proxy-params-green -n prod-adv-bot `
  --from-literal=server="$($obj.server)" `
  --from-literal=server_port="$($obj.server_port)" `
  --from-literal=password="$($obj.password)" `
  --from-literal=method="$($obj.method)"
```

## 2) Deploy green proxy
- Duplicate `bebra-shared-proxy` Deployment with:
  - name: `bebra-shared-proxy-green`
  - secret: `bebra-proxy-params-green`
  - service: `bebra-shared-proxy-green`

## 3) Validate green proxy before switch
```powershell
kubectl rollout status deployment/bebra-shared-proxy-green -n prod-adv-bot --timeout=120s
kubectl run proxy-smoke --rm -i --restart=Never -n prod-adv-bot --image=python:3.11-alpine -- `
  python -c "import urllib.request; p='http://bebra-shared-proxy-green.prod-adv-bot.svc.cluster.local:8080'; o=urllib.request.build_opener(urllib.request.ProxyHandler({'http':p,'https':p})); print(o.open('https://api.telegram.org', timeout=15).status)"
```

## 4) Switch bot to green proxy
```powershell
kubectl set env deployment/wb-sky-bot -n prod-adv-bot `
  PROXY="http://bebra-shared-proxy-green.prod-adv-bot.svc.cluster.local:8080" `
  HTTPS_PROXY="http://bebra-shared-proxy-green.prod-adv-bot.svc.cluster.local:8080" `
  HTTP_PROXY="http://bebra-shared-proxy-green.prod-adv-bot.svc.cluster.local:8080" `
  ALL_PROXY="http://bebra-shared-proxy-green.prod-adv-bot.svc.cluster.local:8080"
kubectl rollout status deployment/wb-sky-bot -n prod-adv-bot --timeout=180s
```

## 5) Observe for 10-15 minutes
```powershell
$pod = kubectl get pod -n prod-adv-bot -l app=wb-sky-bot -o jsonpath='{.items[0].metadata.name}'
kubectl logs $pod -n prod-adv-bot --since=15m | Select-String "TelegramNetworkError|query is too old|Failed to fetch updates|Unhandled exception"
```

## 6) Finalize or rollback
- If stable: remove blue proxy resources after a grace window.
- If unstable: switch env values back to blue service and run rollout again.
