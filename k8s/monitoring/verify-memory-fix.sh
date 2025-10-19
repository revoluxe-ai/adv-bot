#!/bin/bash

# Цвета
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ✅ ПРОВЕРКА ИСПРАВЛЕНИЙ MEMORY OVERCOMMIT                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

ERRORS=0
WARNINGS=0

# Функция для проверки
check() {
  local name=$1
  local command=$2
  
  echo -n "🔍 Проверяю: $name... "
  if eval "$command" &>/dev/null; then
    echo -e "${GREEN}✅${NC}"
    return 0
  else
    echo -e "${RED}❌${NC}"
    ((ERRORS++))
    return 1
  fi
}

# Функция для предупреждения
warn() {
  local name=$1
  local command=$2
  
  echo -n "⚠️  Проверяю: $name... "
  if eval "$command" &>/dev/null; then
    echo -e "${YELLOW}⚠️${NC}"
    ((WARNINGS++))
    return 1
  else
    echo -e "${GREEN}✅${NC}"
    return 0
  fi
}

echo -e "${CYAN}═══ 1. ПРОВЕРКА KUBERNETES КЛАСТЕРА ═══${NC}\n"

check "Кластер доступен" "kubectl cluster-info &>/dev/null"
check "Namespace 'default' существует" "kubectl get namespace default &>/dev/null"

echo ""
echo -e "${CYAN}═══ 2. ПРОВЕРКА DEPLOYMENT ═══${NC}\n"

check "Deployment 'wbgram-original' существует" "kubectl get deployment wbgram-original -n default &>/dev/null"

if kubectl get deployment wbgram-original -n default &>/dev/null; then
  # Проверить memory requests
  mem_req=$(kubectl get deployment wbgram-original -n default -o jsonpath='{.spec.template.spec.containers[0].resources.requests.memory}' 2>/dev/null)
  if [ "$mem_req" = "512Mi" ]; then
    echo -e "✅ Memory requests: ${GREEN}512Mi${NC} (правильно)"
  else
    echo -e "❌ Memory requests: ${RED}$mem_req${NC} (должно быть 512Mi)"
    ((ERRORS++))
  fi
  
  # Проверить memory limits
  mem_lim=$(kubectl get deployment wbgram-original -n default -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}' 2>/dev/null)
  if [ "$mem_lim" = "768Mi" ]; then
    echo -e "✅ Memory limits: ${GREEN}768Mi${NC} (правильно)"
  else
    echo -e "❌ Memory limits: ${RED}$mem_lim${NC} (должно быть 768Mi)"
    ((ERRORS++))
  fi
  
  # Проверить CPU requests
  cpu_req=$(kubectl get deployment wbgram-original -n default -o jsonpath='{.spec.template.spec.containers[0].resources.requests.cpu}' 2>/dev/null)
  if [ "$cpu_req" = "500m" ]; then
    echo -e "✅ CPU requests: ${GREEN}500m${NC} (правильно)"
  else
    echo -e "❌ CPU requests: ${RED}$cpu_req${NC} (должно быть 500m)"
    ((WARNINGS++))
  fi
fi

echo ""
echo -e "${CYAN}═══ 3. ПРОВЕРКА RESOURCEQUOTA ═══${NC}\n"

check "ResourceQuota 'default-quota' в namespace 'default'" "kubectl get resourcequota default-quota -n default &>/dev/null"
check "LimitRange 'default-limits' в namespace 'default'" "kubectl get limitrange default-limits -n default &>/dev/null"

if kubectl get namespace kube-prometheus-stack &>/dev/null; then
  check "ResourceQuota 'prometheus-quota' в namespace 'kube-prometheus-stack'" "kubectl get resourcequota prometheus-quota -n kube-prometheus-stack &>/dev/null"
  check "LimitRange 'prometheus-limits' в namespace 'kube-prometheus-stack'" "kubectl get limitrange prometheus-limits -n kube-prometheus-stack &>/dev/null"
fi

echo ""
echo -e "${CYAN}═══ 4. ПРОВЕРКА СТАТУСА ПОДОВ ═══${NC}\n"

check "Pod deployment/wbgram-original работает" "kubectl get deployment wbgram-original -n default -o jsonpath='{.status.replicas}' | grep -E '^[1-9]' &>/dev/null"

if kubectl get deployment wbgram-original -n default &>/dev/null; then
  ready=$(kubectl get deployment wbgram-original -n default -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
  total=$(kubectl get deployment wbgram-original -n default -o jsonpath='{.status.replicas}' 2>/dev/null)
  if [ "$ready" = "$total" ] && [ -n "$ready" ]; then
    echo -e "✅ Поды готовы: ${GREEN}${ready}/${total}${NC}"
  else
    echo -e "❌ Поды не готовы: ${RED}${ready}/${total}${NC}"
    ((ERRORS++))
  fi
fi

echo ""
echo -e "${CYAN}═══ 5. ПРОВЕРКА ОШИБОК RESOURCEQUOTA ═══${NC}\n"

exceeded=$(kubectl describe resourcequota default-quota -n default 2>/dev/null | grep -i "exceeded" | wc -l)
if [ "$exceeded" -eq 0 ]; then
  echo -e "✅ ResourceQuota не превышен: ${GREEN}OK${NC}"
else
  echo -e "⚠️  ResourceQuota превышен: ${YELLOW}$exceeded раз${NC}"
  ((WARNINGS++))
fi

echo ""
echo -e "${CYAN}═══ 6. ПРОВЕРКА ИСПОЛЬЗОВАНИЯ ПАМЯТИ ═══${NC}\n"

if command -v kubectl &> /dev/null; then
  if kubectl top nodes &>/dev/null; then
    echo -e "${GREEN}Информация об узлах:${NC}"
    kubectl top nodes 2>/dev/null | awk 'NR>1 {printf "  %s: Memory %s / %s\n", $1, $4, $5}'
  else
    echo -e "${YELLOW}Metrics Server не установлен или недоступен${NC}"
    ((WARNINGS++))
  fi
fi

echo ""
echo -e "${CYAN}═══ 7. ФИНАЛЬНАЯ ПРОВЕРКА ═══${NC}\n"

# Проверить, что сумма requests не превышает allocatable
total_req_gi=$(kubectl get pods -A -o json 2>/dev/null | jq '.items[].spec.containers[].resources.requests.memory' 2>/dev/null | grep -oE '^"[0-9]+(Mi|Gi)"' | sed 's/"//g' | awk '{
  if ($0 ~ /Gi/) sum += int(substr($0, 1, length($0)-2)) * 1024;
  else sum += int(substr($0, 1, length($0)-2))
} END {print int(sum/1024)}' 2>/dev/null)

if [ -z "$total_req_gi" ]; then
  echo -e "${YELLOW}⚠️  Не удалось рассчитать суммарные requests${NC}"
  ((WARNINGS++))
elif [ "$total_req_gi" -lt 100 ]; then
  echo -e "✅ Суммарные requests памяти: ${GREEN}~${total_req_gi}Gi${NC} (в допустимых пределах)"
else
  echo -e "⚠️  Суммарные requests памяти: ${YELLOW}~${total_req_gi}Gi${NC} (может быть перегружено)"
  ((WARNINGS++))
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  📊 ИТОГОВЫЙ РЕЗУЛЬТАТ                                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  echo -e "${GREEN}✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!${NC}\n"
  echo -e "${GREEN}Все исправления применены корректно.${NC}"
  echo -e "${GREEN}Алерт 'Cluster has overcommitted memory' должен исчезнуть.${NC}"
  exit 0
elif [ $ERRORS -eq 0 ]; then
  echo -e "${YELLOW}⚠️  ПРОВЕРКИ ПРОЙДЕНЫ С ПРЕДУПРЕЖДЕНИЯМИ${NC}\n"
  echo -e "Ошибок: ${RED}0${NC}"
  echo -e "Предупреждений: ${YELLOW}$WARNINGS${NC}\n"
  echo -e "${YELLOW}Рекомендуется проверить предупреждения выше.${NC}"
  exit 0
else
  echo -e "${RED}❌ ПРОВЕРКИ НЕ ПРОЙДЕНЫ${NC}\n"
  echo -e "Ошибок: ${RED}$ERRORS${NC}"
  echo -e "Предупреждений: ${YELLOW}$WARNINGS${NC}\n"
  echo -e "${RED}Требуется исправление ошибок выше.${NC}"
  exit 1
fi


