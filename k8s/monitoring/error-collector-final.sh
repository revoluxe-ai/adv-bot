#!/bin/sh

set -e

apk add --no-cache curl kubectl python3

BOT_TOKEN=$(kubectl get secret -n default devops-bot -o jsonpath='{.data.telegram-token}' 2>/dev/null | base64 -d 2>/dev/null || echo "")

if [ -z "$BOT_TOKEN" ]; then
  exit 1
fi

CHAT_ID="373435337"

send_msg() {
  local text="$1"
  local json_text=$(python3 -c "import json; print(json.dumps('''$text'''))" 2>/dev/null || echo "\"Error formatting\"")
  
  curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\": ${CHAT_ID}, \"text\": ${json_text}, \"parse_mode\": \"HTML\"}" > /dev/null || true
}

echo "Collecting errors..."

TOTAL=0
SUMMARY=""
POD_COUNT=0

for NS in default sellerspub; do
  PODS=$(kubectl get pods -n $NS -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)
  
  for POD in $PODS; do
    if [ -z "$POD" ]; then continue; fi
    
    LOGS=$(kubectl logs -n $NS $POD --tail=2000 2>/dev/null || true)
    CNT=$(echo "$LOGS" | grep -ic "ERROR\|Exception\|CRITICAL" 2>/dev/null || echo "0")
    CNT=${CNT:-0}
    
    if [ "$CNT" -gt 0 ] 2>/dev/null; then
      TOTAL=$((TOTAL + CNT))
      POD_COUNT=$((POD_COUNT + 1))
      SUMMARY="$SUMMARY$NS/$POD: $CNT
"
      
      if [ "$POD_COUNT" -le 8 ]; then
        TRACES=$(echo "$LOGS" | grep -i "ERROR\|Exception\|CRITICAL" | head -12)
        send_msg "📋 <b>$NS/$POD</b> - $CNT errors

$TRACES"
        sleep 0.2
      fi
    fi
  done
done

if [ "$TOTAL" -gt 5 ]; then
  send_msg "🚨 <b>ERROR REPORT</b>
━━━━━━━━━━━━
📊 Total: $TOTAL errors
📦 Pods: $POD_COUNT

$SUMMARY
━━━━━━━━━━━━"
  
  echo "Sent to Telegram"
else
  echo "Less than 5 errors"
fi

