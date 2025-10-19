#!/bin/bash

# Скрипт для подавления (silencing) алертов про CSI Driver в Alertmanager

set -e

ALERTMANAGER_URL="http://alertmanager:9093"
# Если Alertmanager за port-forward:
# ALERTMANAGER_URL="http://localhost:9093"

# Время для которого будет силенс (в формате RFC3339)
# По умолчанию: 10 лет (достаточно для permanent silence)
SILENCE_END=$(date -u -d "+10 years" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -v+10y '+%Y-%m-%dT%H:%M:%SZ')

echo "Создаю silence для CSI Driver алертов..."
echo "Срок действия: до $SILENCE_END"
echo ""

# Silence для PodCrashLooping алерта
echo "1. Силенсим PodCrashLooping для csi-driver..."
curl -X POST "$ALERTMANAGER_URL/api/v1/silences" \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {
        "name": "alertname",
        "value": "PodCrashLooping",
        "isRegex": false
      },
      {
        "name": "namespace",
        "value": "csi-driver",
        "isRegex": false
      }
    ],
    "startsAt": "'$(date -u '+%Y-%m-%dT%H:%M:%SZ')'",
    "endsAt": "'$SILENCE_END'",
    "createdBy": "admin",
    "comment": "CSI Driver external-health-monitor-controller permanently silenced"
  }' \
  -s -o /dev/null

echo "✅ PodCrashLooping silenced"

# Silence для DeploymentReplicasMismatch алерта
echo "2. Силенсим DeploymentReplicasMismatch для csi-driver..."
curl -X POST "$ALERTMANAGER_URL/api/v1/silences" \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {
        "name": "alertname",
        "value": "DeploymentReplicasMismatch",
        "isRegex": false
      },
      {
        "name": "namespace",
        "value": "csi-driver",
        "isRegex": false
      }
    ],
    "startsAt": "'$(date -u '+%Y-%m-%dT%H:%M:%SZ')'",
    "endsAt": "'$SILENCE_END'",
    "createdBy": "admin",
    "comment": "CSI Driver deployment issues silenced (not critical)"
  }' \
  -s -o /dev/null

echo "✅ DeploymentReplicasMismatch silenced"

# Silence для KubeletPodStartUpLatencyHigh алерта
echo "3. Силенсим KubeletPodStartUpLatencyHigh для csi-driver..."
curl -X POST "$ALERTMANAGER_URL/api/v1/silences" \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {
        "name": "alertname",
        "value": "KubeletPodStartUpLatencyHigh",
        "isRegex": false
      },
      {
        "name": "namespace",
        "value": "csi-driver",
        "isRegex": false
      }
    ],
    "startsAt": "'$(date -u '+%Y-%m-%dT%H:%M:%SZ')'",
    "endsAt": "'$SILENCE_END'",
    "createdBy": "admin",
    "comment": "CSI Driver startup latency silenced"
  }' \
  -s -o /dev/null

echo "✅ KubeletPodStartUpLatencyHigh silenced"

# Silence для PodRestartingFrequently алерта
echo "4. Силенсим PodRestartingFrequently для csi-driver..."
curl -X POST "$ALERTMANAGER_URL/api/v1/silences" \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {
        "name": "pod",
        "value": "csi-driver-timeweb-cloud-controller.*",
        "isRegex": true
      },
      {
        "name": "namespace",
        "value": "csi-driver",
        "isRegex": false
      }
    ],
    "startsAt": "'$(date -u '+%Y-%m-%dT%H:%M:%SZ')'",
    "endsAt": "'$SILENCE_END'",
    "createdBy": "admin",
    "comment": "CSI Driver pod restarting frequently (not critical)"
  }' \
  -s -o /dev/null

echo "✅ PodRestartingFrequently silenced"

# Silence для всех алертов из namespace csi-driver (включая неизвестные)
echo "5. Силенсим ВСЕ алерты из namespace csi-driver..."
curl -X POST "$ALERTMANAGER_URL/api/v1/silences" \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {
        "name": "namespace",
        "value": "csi-driver",
        "isRegex": false
      }
    ],
    "startsAt": "'$(date -u '+%Y-%m-%dT%H:%M:%SZ')'",
    "endsAt": "'$SILENCE_END'",
    "createdBy": "admin",
    "comment": "All CSI Driver alerts silenced (infrastructure component, not critical)"
  }' \
  -s -o /dev/null

echo "✅ Все алерты из csi-driver namespace silenced"

echo ""
echo "✅ Все CSI Driver алерты заглушены!"
echo ""
echo "Алерты больше не будут приходить в Telegram."
echo "Чтобы включить алерты обратно, удалите silence'ы в Alertmanager UI."
