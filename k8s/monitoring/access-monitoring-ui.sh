#!/bin/bash

# Скрипт для доступа к UI мониторинга
# Запускает port-forward для Prometheus, Grafana и AlertManager

echo -e "\033[1;32m🚀 Запуск доступа к мониторингу...\033[0m"
echo ""

# Prometheus
echo -e "\033[1;36m📊 Prometheus UI: http://localhost:9090\033[0m"
(
    echo -e "\033[1;34m🔵 Prometheus port-forward активен\033[0m"
    kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
) &
PROM_PID=$!

sleep 2

# Grafana
echo -e "\033[1;36m📈 Grafana UI: http://localhost:3000\033[0m"
GRAFANA_PASSWORD=$(kubectl get secret -n kube-prometheus-stack kube-prometheus-stack-grafana -o jsonpath="{.data.admin-password}" | base64 -d)
echo -e "\033[1;33m   Логин: admin\033[0m"
echo -e "\033[1;33m   Пароль: $GRAFANA_PASSWORD\033[0m"

(
    echo -e "\033[1;32m🟢 Grafana port-forward активен\033[0m"
    kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
) &
GRAFANA_PID=$!

sleep 2

# AlertManager
echo -e "\033[1;36m🚨 AlertManager UI: http://localhost:9093\033[0m"
(
    echo -e "\033[1;33m🟠 AlertManager port-forward активен\033[0m"
    kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-alertmanager 9093:9093
) &
AM_PID=$!

echo ""
echo -e "\033[1;32m✅ Все сервисы запущены!\033[0m"
echo ""
echo -e "\033[1;37m📌 Открывайте в браузере:\033[0m"
echo -e "   • Prometheus:    http://localhost:9090   (алерты и метрики)"
echo -e "   • Grafana:       http://localhost:3000   (дашборды)"
echo -e "   • AlertManager:  http://localhost:9093   (управление алертами)"
echo ""
echo -e "\033[1;33m⚠️  Для остановки закройте все окна port-forward\033[0m"
echo ""

# Открываем браузер автоматически
sleep 3

# Кроссплатформное открытие браузера
if command -v xdg-open > /dev/null; then
    xdg-open "http://localhost:9090"
    xdg-open "http://localhost:3000"
    xdg-open "http://localhost:9093"
elif command -v open > /dev/null; then
    open "http://localhost:9090"
    open "http://localhost:3000"
    open "http://localhost:9093"
elif command -v start > /dev/null; then
    start "http://localhost:9090"
    start "http://localhost:3000"
    start "http://localhost:9093"
fi

# Ждем завершения фоновых процессов
wait $PROM_PID $GRAFANA_PID $AM_PID
