#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="prod-analytics"
RELEASE="my-neo4j"
VALUES_PATH="k8s/new-cluster/neo4j-values.yaml"
STORAGE_CLASS="hdd.network-drives.csi.timeweb.cloud"
IMAGE="my-registry.registry.twcstorage.ru/wb-adv-bot/neo4j-gds-apoc:2025.07.1"
PASSWORD="shelf-life-alarm-dublin-mono-4359"

echo "��� Установка Neo4j в namespace: $NAMESPACE"
echo "��� Образ: $IMAGE"
echo "��� StorageClass: $STORAGE_CLASS"
echo "-------------------------------------------"

# 1️⃣ Удаление старой установки
echo "��� Удаляем старую установку..."
helm uninstall "$RELEASE" -n "$NAMESPACE" --ignore-not-found || true
kubectl delete statefulset "$RELEASE" -n "$NAMESPACE" --ignore-not-found || true
kubectl delete pvc -n "$NAMESPACE" -l app="$RELEASE" --ignore-not-found || true
kubectl delete pvc data-"$RELEASE"-0 -n "$NAMESPACE" --ignore-not-found --force --grace-period=0 || true

PV_LIST=$(kubectl get pv 2>/dev/null | grep "$RELEASE" | awk '{print $1}' || true)
if [[ -n "$PV_LIST" ]]; then
  echo "��� Удаляем PV: $PV_LIST"
  echo "$PV_LIST" | xargs -r kubectl delete pv --ignore-not-found
fi

echo "✅ Очистка завершена"
kubectl get pvc -n "$NAMESPACE" | grep neo4j || echo "PVC clean ✅"
echo "-------------------------------------------"

# 2️⃣ Проверка Helm-репозитория
echo "��� Проверяем Helm репозиторий..."
helm repo add neo4j https://neo4j.github.io/helm-charts --force-update >/dev/null
helm repo update >/dev/null
echo "✅ Helm репозиторий обновлён"
echo "-------------------------------------------"

# 3️⃣ Namespace
echo "��� Проверяем namespace..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
echo "✅ Namespace готов"
echo "-------------------------------------------"

# 4️⃣ Создание values-файла
echo "��� Создаём values-файл $VALUES_PATH ..."
mkdir -p "$(dirname "$VALUES_PATH")"

cat > "$VALUES_PATH" <<EOF
neo4j:
  name: $RELEASE
  password: $PASSWORD
  acceptLicenseAgreement: "yes"
  edition: community
  config:
    db.checkpoint.interval.time: 15m
    db.checkpoint.interval.tx: "10000"
    db.tx_log.rotation.retention_policy: 1G size
    db.tx_log.rotation.size: 250M
    dbms.security.procedures.allowlist: gds.*,apoc.*
    dbms.security.procedures.unrestricted: gds.*,apoc.*
    dbms.security.tls_reload_enabled: "true"
    internal.dbms.sharded_property_database.enabled: "false"
    server.config.strict_validation.enabled: "false"
    server.memory.heap.initial_size: 24g
    server.memory.heap.max_size: 24g
    server.memory.pagecache.size: 512m
    db.tx_log.rotation.keep_logical_logs: "true"

image:
  customImage: $IMAGE
  imagePullPolicy: IfNotPresent
  imagePullSecrets:
    - registry

env:
  NEO4J_PLUGINS: '["graph-data-science", "apoc"]'

logging:
  serverLogsXml: ""
  userLogsXml: ""

volumes:
  data:
    mode: dynamic
    dynamic:
      accessModes:
        - ReadWriteOnce
      requests:
        storage: 50Gi
      storageClassName: $STORAGE_CLASS

services:
  neo4j:
    enabled: true
    spec:
      type: NodePort
    ports:
      bolt:
        enabled: true
        nodePort: 30074
      http:
        enabled: true
        nodePort: 30075
      https:
        enabled: true
        nodePort: 30443

resources:
  limits:
    cpu: 4
    memory: 32Gi
  requests:
    cpu: 4
    memory: 32Gi

securityContext:
  fsGroup: 7474
  fsGroupChangePolicy: Always
  runAsGroup: 7474
  runAsNonRoot: true
  runAsUser: 7474

livenessProbe:
  failureThreshold: 40
  periodSeconds: 5
  tcpSocket:
    port: 7687
  timeoutSeconds: 10

readinessProbe:
  failureThreshold: 20
  periodSeconds: 5
  tcpSocket:
    port: 7687
  timeoutSeconds: 10

startupProbe:
  failureThreshold: 1000
  periodSeconds: 5
  tcpSocket:
    port: 7687
EOF

echo "✅ Values-файл создан"
echo "-------------------------------------------"

# 5️⃣ Установка Helm
echo "��� Устанавливаем Neo4j..."
helm upgrade --install "$RELEASE" neo4j/neo4j \
  -n "$NAMESPACE" \
  -f "$VALUES_PATH" \
  --wait --timeout 15m

echo "✅ Установка завершена"
echo "-------------------------------------------"

# 6️⃣ Проверка состояния
echo "��� Проверяем ресурсы..."
kubectl get pods,statefulset,pvc,svc -n "$NAMESPACE" | grep "$RELEASE" || true
echo "-------------------------------------------"

echo "��� Успех! Neo4j развернут в namespace $NAMESPACE"
echo "Bolt доступен на NodePort 30074"
echo "Пароль: $PASSWORD"

