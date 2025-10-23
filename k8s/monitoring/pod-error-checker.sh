#!/bin/bash

# 🚨 Pod Error Monitoring Tool
# Быстрый мониторинг ошибок в подах

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Функции для вывода
print_header() {
    echo -e "${CYAN}════════════════════════════════════════${NC}"
    echo -e "${WHITE}$1${NC}"
    echo -e "${CYAN}════════════════════════════════════════${NC}"
}

print_section() {
    echo -e "\n${BLUE}➜ $1${NC}"
}

print_ok() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Получить namespace из параметра или использовать default
NAMESPACE="${1:-default}"
PODS_LIMIT="${2:-50}"

print_header "🚨 POD ERROR MONITORING - $NAMESPACE"

# 1. Поды в CrashLoopBackOff
print_section "Поды в CrashLoopBackOff (КРИТИЧНО)"
CRASH_PODS=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Failed -o json | jq '.items[] | select(.status.containerStatuses[]?.state.waiting.reason=="CrashLoopBackOff") | .metadata.name' -r 2>/dev/null || true)

if [ -z "$CRASH_PODS" ]; then
    print_ok "Нет подов в CrashLoopBackOff"
else
    print_error "Найдены поды в CrashLoopBackOff:"
    while IFS= read -r POD; do
        [ -z "$POD" ] && continue
        REASON=$(kubectl get pod "$POD" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}' 2>/dev/null || echo "Unknown")
        RESTARTS=$(kubectl get pod "$POD" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null || echo "0")
        echo -e "${RED}  ✗ $POD (Restarts: $RESTARTS, Reason: $REASON)${NC}"
    done <<< "$CRASH_PODS"
fi

# 2. Поды, которые падали (имеют рестарты)
print_section "Поды с рестартами (за последний час)"
kubectl get pods -n "$NAMESPACE" \
    --sort-by='.status.containerStatuses[0].restartCount' \
    --field-selector=status.phase=Running \
    -o wide | tail -n +2 | awk '{if ($4 > 0) print}' | head -20 | while read -r line; do
    POD=$(echo "$line" | awk '{print $1}')
    RESTARTS=$(echo "$line" | awk '{print $4}')
    if [ "$RESTARTS" -gt 0 ]; then
        print_warn "  $POD: $RESTARTS рестартов"
    fi
done

# 3. Поды в ImagePullBackOff
print_section "Проблемы с загрузкой образов"
IMAGE_ISSUES=$(kubectl get pods -n "$NAMESPACE" -o json 2>/dev/null | \
    jq '.items[] | select(.status.containerStatuses[]?.state.waiting.reason=="ImagePullBackOff" or .status.containerStatuses[]?.state.waiting.reason=="ErrImagePull") | .metadata.name' -r 2>/dev/null || true)

if [ -z "$IMAGE_ISSUES" ]; then
    print_ok "Нет проблем с загрузкой образов"
else
    print_error "Найдены проблемы с загрузкой образов:"
    while IFS= read -r POD; do
        [ -z "$POD" ] && continue
        REASON=$(kubectl get pod "$POD" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}' 2>/dev/null || echo "Unknown")
        IMAGE=$(kubectl get pod "$POD" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].imageID}' 2>/dev/null || echo "Unknown")
        echo -e "${RED}  ✗ $POD (Reason: $REASON)${NC}"
    done <<< "$IMAGE_ISSUES"
fi

# 4. Поды в статусе Pending слишком долго
print_section "Поды в статусе Pending (зависают)"
PENDING=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Pending -o json 2>/dev/null | \
    jq '.items[] | {name: .metadata.name, age: .metadata.creationTimestamp}' -r 2>/dev/null || true)

if [ -z "$PENDING" ]; then
    print_ok "Нет зависших подов"
else
    print_warn "Найдены зависшие поды:"
    echo "$PENDING" | while read -r POD; do
        [ -z "$POD" ] && continue
        AGE=$(kubectl get pod "$POD" -n "$NAMESPACE" -o jsonpath='{.metadata.creationTimestamp}' 2>/dev/null)
        if [ ! -z "$AGE" ]; then
            echo -e "${YELLOW}  ⚠ $POD (Created: $AGE)${NC}"
        fi
    done
fi

# 5. Поды, убитые OOMKiller
print_section "Поды, убитые OOMKiller"
OOM_PODS=$(kubectl get pods -n "$NAMESPACE" -o json 2>/dev/null | \
    jq '.items[] | select(.status.containerStatuses[]?.lastState.terminated.reason=="OOMKilled") | .metadata.name' -r 2>/dev/null || true)

if [ -z "$OOM_PODS" ]; then
    print_ok "Нет подов, убитых OOMKiller"
else
    print_error "Найдены поды, убитые OOMKiller:"
    while IFS= read -r POD; do
        [ -z "$POD" ] && continue
        echo -e "${RED}  ✗ $POD${NC}"
    done <<< "$OOM_PODS"
fi

# 6. Все поды в плохом состоянии (сводная таблица)
print_section "Сводка по всем подам"
echo -e "\n${WHITE}Всего подов: $(kubectl get pods -n "$NAMESPACE" 2>/dev/null | tail -1 | awk '{print NF}')${NC}"

echo -e "\n${BLUE}Статусы подов:${NC}"
kubectl get pods -n "$NAMESPACE" -o json 2>/dev/null | jq -r '.items[] | .status.phase' | sort | uniq -c | while read count status; do
    case "$status" in
        Running)
            print_ok "$status: $count"
            ;;
        Pending)
            print_warn "$status: $count"
            ;;
        Failed|Unknown)
            print_error "$status: $count"
            ;;
    esac
done

# 7. Топ 10 подов с наибольшим количеством рестартов
print_section "Топ подов по количеству рестартов"
kubectl get pods -n "$NAMESPACE" -o json 2>/dev/null | \
    jq '.items[] | {name: .metadata.name, restarts: (.status.containerStatuses[0].restartCount // 0)}' | \
    jq -r '"\(.restarts) \(.name)"' | sort -rn | head -10 | while read count name; do
    if [ "$count" -gt 0 ]; then
        print_warn "  $name: $count рестартов"
    fi
done

# 8. Events по ошибкам
print_section "Последние события с ошибками"
kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' 2>/dev/null | grep -i "error\|warning\|fail" | tail -10 || echo "Нет ошибочных событий"

# 9. Pods Not Ready
print_section "Поды не в Ready статусе"
NOT_READY=$(kubectl get pods -n "$NAMESPACE" -o json 2>/dev/null | \
    jq '.items[] | select(.status.conditions[] | select(.type=="Ready" and .status=="False")) | .metadata.name' -r 2>/dev/null || true)

if [ -z "$NOT_READY" ]; then
    print_ok "Все поды в Ready статусе"
else
    print_warn "Поды не готовы:"
    while IFS= read -r POD; do
        [ -z "$POD" ] && continue
        REASON=$(kubectl get pod "$POD" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].reason}' 2>/dev/null || echo "Unknown")
        echo -e "${YELLOW}  ⚠ $POD (Reason: $REASON)${NC}"
    done <<< "$NOT_READY"
fi

# 10. Проверка resource limits
print_section "Поды близкие к лимитам памяти"
kubectl top pods -n "$NAMESPACE" 2>/dev/null | tail -n +2 | head -10 | while read line; do
    POD=$(echo "$line" | awk '{print $1}')
    MEM=$(echo "$line" | awk '{print $3}' | sed 's/Mi//')
    if [ ! -z "$MEM" ] && [ "$MEM" -gt 1000 ]; then
        print_warn "  $POD использует ${MEM}Mi памяти"
    fi
done || echo "Metrics Server не доступен"

print_header "✓ Мониторинг завершен"

# Рекомендации
echo -e "\n${CYAN}💡 Рекомендации для расследования:${NC}"
echo -e "${WHITE}1. Посмотреть логи:${NC} kubectl logs -n $NAMESPACE POD_NAME"
echo -e "${WHITE}2. Описание пода:${NC} kubectl describe pod -n $NAMESPACE POD_NAME"
echo -e "${WHITE}3. События в namespace:${NC} kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'"
echo -e "${WHITE}4. Prometheus UI:${NC} kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090"
echo -e "${WHITE}5. Grafana Dashboard:${NC} kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80"


