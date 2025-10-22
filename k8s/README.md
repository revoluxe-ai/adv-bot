## Структура каталога k8s/

Эта директория содержит все Kubernetes-манифесты проекта, разложенные по доменам для удобства сопровождения и GitOps.

Структура:

- apps/ — приложения и сервисы проекта (Deployments, Services, ConfigMaps)
- databases/ — СУБД и брокеры (Neo4j, Redis, ClickHouse, Postgres, Zookeeper)
- network/ — Ingress, Ingress Controller, сервисы уровня сети
- monitoring/ — Prometheus stack, node-exporter, metrics-server, алерты/заглушки
- logging/ — Promtail/Filebeat конфигурации и DaemonSets
- rbac/ — ServiceAccount, Role/RoleBinding, Secrets для доступа к реестрам
- storage/ — PVC/PV/StorageClass/CSI (только для справки, применять осторожно)
- cronjobs/ — CronJob ресурсы
- tools/ — отладочные поды и временные файлы
- cluster-snapshots/ — снимки состояния кластера и скрипты диагностики

Правила применения (PowerShell):

1) Всегда проверять перед применением:
```
kubectl apply --dry-run=client -f .\k8s\<path>\
```

2) Применение каталога целиком:
```
kubectl apply -f .\k8s\apps\
```

3) kubeconfig нового кластера находится по пути:
```
.\k8s\new-cluster\new-cluster-config.yaml
```
Пример запуска команды с kubeconfig:
```
kubectl --kubeconfig .\k8s\new-cluster\new-cluster-config.yaml get pods -A
```

См. также: `cluster-snapshots/collect.ps1` для автоматического сбора состояния кластера.


