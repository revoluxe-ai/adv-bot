#!/bin/bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-kube-prometheus-stack}"
TELEGRAM_CHAT_ID=${CHAT_ID:-373435337}

# Получаем токен из секрета devops-bot (из namespace default, как указано)
BOT_TOKEN_B64=$(kubectl -n default get secret devops-bot -o jsonpath="{.data.telegram-token}")
BOT_TOKEN=$(echo "$BOT_TOKEN_B64" | base64 -d)

cat > /tmp/alertmanager-telegram.yaml <<EOF
global:
  resolve_timeout: 5m

route:
  receiver: 'telegram'
  group_by: ['alertname','namespace','pod']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 1h

receivers:
- name: 'telegram'
  telegram_configs:
  - bot_token: '${BOT_TOKEN}'
    chat_id: '${TELEGRAM_CHAT_ID}'
    parse_mode: HTML
    message: |
      🚨 <b>{{ .Status | toUpper }}</b>
      🔹 <b>Alert:</b> {{ .CommonAnnotations.summary }}
      🔹 <b>Severity:</b> {{ .CommonLabels.severity }}
      🔹 <b>Namespace:</b> {{ .CommonLabels.namespace }}
      🔹 <b>Pod:</b> {{ .CommonLabels.pod }}
      🔹 <b>Description:</b> {{ .CommonAnnotations.description }}
EOF

# Создаем Secret для Alertmanager из сгенерированного YAML
# Важно: имя секрета должно быть таким, как Alertmanager ожидает.
# Для kube-prometheus-stack это обычно 'alertmanager-<release-name>-alertmanager' или 'alertmanager-main'
# Мы заменим существующий Secret, чтобы обновить конфигурацию

# Проверяем, существует ли уже Secret с именем alertmanager-kube-prometheus-stack-alertmanager
if kubectl get secret alertmanager-kube-prometheus-stack-alertmanager -n ${NAMESPACE} &>/dev/null; then
  echo "Обновляю существующий Secret: alertmanager-kube-prometheus-stack-alertmanager"
  kubectl create secret generic alertmanager-kube-prometheus-stack-alertmanager -n ${NAMESPACE} \
    --from-file=alertmanager.yaml=/tmp/alertmanager-telegram.yaml \
    --dry-run=client -o yaml | kubectl apply -f -
else
  echo "Создаю новый Secret: alertmanager-kube-prometheus-stack-alertmanager"
  kubectl create secret generic alertmanager-kube-prometheus-stack-alertmanager -n ${NAMESPACE} \
    --from-file=alertmanager.yaml=/tmp/alertmanager-telegram.yaml \
    --dry-run=client -o yaml | kubectl apply -f -
fi

# Перезагружаем Alertmanager Deployment, чтобы он подхватил новый конфиг
echo "Перезапускаю Alertmanager deployment..."
kubectl rollout restart deployment -n ${NAMESPACE} kube-prometheus-stack-alertmanager

echo "Telegram-уведомления настроены и Alertmanager перезапускается!"
echo "Пожалуйста, проверьте логи Alertmanager для подтверждения загрузки конфигурации."
