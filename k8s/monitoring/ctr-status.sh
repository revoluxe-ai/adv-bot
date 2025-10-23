#!/bin/bash

# Скрипт для проверки статуса сервисов CTR v2

echo -e "\033[1;32m🔍 Проверка статуса сервисов CTR v2\033[0m"
echo ""

# Проверяем поды
echo -e "\033[1;36m📦 Статус подов:\033[0m"
kubectl get pods -n default -l app=predict-ctr-updater,app=predict-ctr-service -o wide 2>/dev/null || kubectl get pods -n default 2>/dev/null | grep -i ctr

echo ""
echo -e "\033[1;36m⏱️  Время перезагрузки podов:\033[0m"
kubectl get pods -n default -o custom-columns=NAME:.metadata.name,AGE:.metadata.creationTimestamp,RESTART:.status.containerStatuses[0].restartCount 2>/dev/null | grep -i ctr

echo ""
echo -e "\033[1;36m🔴 Последние ошибки:\033[0m"
echo ""

# Ошибки из predict-ctr-updater
UPDATER_POD=$(kubectl get pods -n default -l app=predict-ctr-updater -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
if [ -n "$UPDATER_POD" ]; then
    echo -e "predict-ctr-updater:"
    kubectl logs -n default "$UPDATER_POD" --tail=50 2>&1 | grep -i "error\|ERROR\|exception\|failed" || echo "  ✅ Ошибок не найдено"
fi

echo ""

# Ошибки из predict-ctr-service  
SERVICE_POD=$(kubectl get pods -n default -l app=predict-ctr-service -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
if [ -n "$SERVICE_POD" ]; then
    echo -e "predict-ctr-service:"
    kubectl logs -n default "$SERVICE_POD" --tail=50 2>&1 | grep -i "error\|ERROR\|exception\|failed" || echo "  ✅ Ошибок не найдено"
fi

echo ""
echo -e "\033[1;36m📊 Статистика обновлений (последний час):\033[0m"
echo ""

UPDATER_POD=$(kubectl get pods -n default -l app=predict-ctr-updater -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
if [ -n "$UPDATER_POD" ]; then
    echo "Обработано кампаний:"
    kubectl logs -n default "$UPDATER_POD" --tail=500 2>&1 | grep "Обработка кампании" | wc -l
    
    echo ""
    echo "Предсказаний выполнено:"
    kubectl logs -n default "$UPDATER_POD" --tail=500 2>&1 | grep "Предсказание завершено" | wc -l
    
    echo ""
    echo "Медленные запросы (>10s):"
    kubectl logs -n default "$UPDATER_POD" --tail=500 2>&1 | grep "Slow query" | wc -l
fi

echo ""
echo -e "\033[1;33m💡 Для полной отладки используйте:\033[0m"
echo "  ./debug-ctr.sh <shop_id>          # Отладка для конкретного магазина"
echo "  ./view-logs.sh all                # Все логи мониторинга"
echo ""

