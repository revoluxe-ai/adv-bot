#!/bin/bash

# Скрипт для просмотра логов pods мониторинга

COMPONENT="${1:-all}"

# Валидация компонента
case "$COMPONENT" in
    prometheus|alertmanager|grafana|operator|all) ;;
    *)
        echo -e "\033[1;31mОшибка: неизвестный компонент '$COMPONENT'\033[0m"
        echo "Допустимые значения: prometheus, alertmanager, grafana, operator, all"
        exit 1
        ;;
esac

echo -e "\033[1;32m📋 Просмотр логов мониторинга\033[0m"
echo ""

show_logs() {
    local pod_name="$1"
    local display_name="$2"
    local namespace="${3:-kube-prometheus-stack}"
    
    echo -e "\033[1;90m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
    echo -e "\033[1;36m📦 $display_name\033[0m"
    echo -e "\033[1;90m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
    echo ""
    
    if [ -z "$pod_name" ]; then
        echo -e "\033[1;31m❌ Pod не найден для компонента: $display_name\033[0m"
        echo ""
        return 1
    fi
    
    if kubectl logs -n "$namespace" "$pod_name" --tail=50 --timestamps; then
        echo ""
        echo ""
    else
        echo -e "\033[1;31m❌ Ошибка получения логов\033[0m"
        echo ""
        echo ""
        return 1
    fi
}

case "$COMPONENT" in
    "prometheus")
        pod=$(kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=prometheus -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
        show_logs "$pod" "Prometheus"
        ;;
    
    "alertmanager")
        pod=$(kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=alertmanager -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
        show_logs "$pod" "AlertManager"
        ;;
    
    "grafana")
        pod=$(kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=grafana -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
        show_logs "$pod" "Grafana"
        ;;
    
    "operator")
        pod=$(kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=kube-prometheus-stack-prometheus-operator -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
        show_logs "$pod" "Prometheus Operator"
        ;;
    
    "all")
        echo -e "\033[1;33m🔍 Показываю последние логи всех компонентов...\033[0m"
        echo ""
        
        # Prometheus
        prom_pod=$(kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=prometheus -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
        show_logs "$prom_pod" "Prometheus"
        
        # AlertManager
        am_pod=$(kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=alertmanager -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
        show_logs "$am_pod" "AlertManager"
        
        # Grafana
        grafana_pod=$(kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=grafana -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
        show_logs "$grafana_pod" "Grafana"
        
        # Operator
        op_pod=$(kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=kube-prometheus-stack-prometheus-operator -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
        show_logs "$op_pod" "Prometheus Operator"
        ;;
esac

echo -e "\033[1;90m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo ""
echo -e "\033[1;33m💡 Для живых логов используйте:\033[0m"
echo -e "\033[1;37m   kubectl logs -f -n kube-prometheus-stack <pod-name>\033[0m"
echo ""
echo -e "\033[1;33m💡 Список всех pods:\033[0m"
echo -e "\033[1;37m   kubectl get pods -n kube-prometheus-stack\033[0m"
echo ""

