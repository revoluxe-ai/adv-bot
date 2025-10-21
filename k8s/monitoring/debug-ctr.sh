#!/bin/bash

# Скрипт для отладки проблем с CTR v2 по номеру магазина
# Использование: ./debug-ctr.sh <shop_id>

SHOP_ID="${1:-}"
LINES="${2:-200}"

if [ -z "$SHOP_ID" ]; then
    echo -e "\033[1;31m❌ Ошибка: укажите ID магазина\033[0m"
    echo "Использование: ./debug-ctr.sh <shop_id> [количество_строк]"
    echo ""
    echo "Примеры:"
    echo "  ./debug-ctr.sh 12345          # Последние 200 строк логов"
    echo "  ./debug-ctr.sh 12345 500      # Последние 500 строк логов"
    exit 1
fi

echo -e "\033[1;32m🔍 Отладка CTR v2 для магазина: $SHOP_ID\033[0m"
echo ""

# Проверим логи predict-ctr-updater
echo -e "\033[1;36m📊 Логи predict-ctr-updater:\033[0m"
echo ""
UPDATER_POD=$(kubectl get pods -n default -l app=predict-ctr-updater -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)

if [ -z "$UPDATER_POD" ]; then
    echo -e "\033[1;31m❌ Pod predict-ctr-updater не найден\033[0m"
else
    kubectl logs -n default "$UPDATER_POD" --tail="$LINES" 2>&1 | grep -i "shop_id\|shop\|$SHOP_ID" || echo "Нет логов для этого магазина"
fi

echo ""
echo -e "\033[1;36m📊 Логи predict-ctr-service:\033[0m"
echo ""
SERVICE_POD=$(kubectl get pods -n default -l app=predict-ctr-service -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)

if [ -z "$SERVICE_POD" ]; then
    echo -e "\033[1;31m❌ Pod predict-ctr-service не найден\033[0m"
else
    kubectl logs -n default "$SERVICE_POD" --tail="$LINES" 2>&1 | grep -i "error\|ERROR\|exception\|failed" || echo "Нет ошибок в логах"
fi

echo ""
echo -e "\033[1;36m📊 Логи run-shop-update-worker:\033[0m"
echo ""
WORKER_POD=$(kubectl get pods -n default -l app=run-shop-update-worker -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)

if [ -z "$WORKER_POD" ]; then
    echo -e "\033[1;31m❌ Pod run-shop-update-worker не найден\033[0m"
else
    kubectl logs -n default "$WORKER_POD" --tail="$LINES" 2>&1 | grep -i "$SHOP_ID\|shop_id" || echo "Нет логов для этого магазина"
fi

echo ""
echo -e "\033[1;33m💡 Полезные команды:\033[0m"
echo "  # Просмотр всех подов с CTR:"
echo "  kubectl get pods -n default | grep -i ctr"
echo ""
echo "  # Живые логи:"
echo "  kubectl logs -f -n default <pod-name>"
echo ""
echo "  # Поиск всех ошибок:"
echo "  kubectl logs -n default <pod-name> --tail=500 | grep -i error"
echo ""

