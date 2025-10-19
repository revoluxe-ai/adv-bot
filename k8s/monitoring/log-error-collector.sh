#!/bin/sh

set -e

apk add --no-cache curl kubectl

echo "🔍 Получаю BOT_TOKEN..."
BOT_TOKEN=$(kubectl get secret -n default devops-bot -o jsonpath='{.data.telegram-token}' 2>/dev/null | base64 -d 2>/dev/null || echo "")

if [ -z "$BOT_TOKEN" ]; then
  echo "❌ BOT_TOKEN не найден"
  exit 1
fi

CHAT_ID="373435337"

send_telegram() {
  curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\": ${CHAT_ID}, \"text\": \"$1\", \"parse_mode\": \"HTML\"}" > /dev/null || true
}

echo "📊 Начинаю сбор ошибок..."

TOTAL_ERRORS=0
ERROR_LIST=""

for NS in default sellerspub; do
  echo "  Проверяю namespace: $NS"
  
  PODS=$(kubectl get pods -n $NS -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)
  
  for POD in $PODS; do
    if [ -z "$POD" ]; then
      continue
    fi
    
    COUNT=$(kubectl logs -n $NS $POD --tail=500 2>/dev/null | grep -ic "ERROR\|Exception\|CRITICAL" || echo "0")
    
    if [ "$COUNT" -gt 0 ]; then
      TOTAL_ERRORS=$((TOTAL_ERRORS + COUNT))
      ERROR_LIST="$ERROR_LIST🔴 $NS/$POD: $COUNT errors%0A"
      echo "    ✓ $COUNT ошибок"
    fi
  done
done

echo "━━━━━━━━━━━━━━━━━"
echo "Всего найдено ошибок: $TOTAL_ERRORS"

if [ "$TOTAL_ERRORS" -gt 5 ]; then
  echo "✅ Отправляю в Telegram..."
  
  MESSAGE="🚨 Application Errors Report%0A━━━━━━━━━━━━━━━%0A📊 Total: $TOTAL_ERRORS%0A%0A$ERROR_LIST━━━━━━━━━━━━━━━%0Aℹ️ kubectl logs -n NS POD"
  
  send_telegram "$MESSAGE"
  
  echo "✅ Отправлено!"
else
  echo "ℹ️ Меньше 5 ошибок - отправка пропущена"
fi

