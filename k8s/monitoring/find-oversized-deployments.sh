#!/bin/bash

# Цвета
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🔍 ПОИСК DEPLOYMENTS С ИЗБЫТОЧНЫМИ ЛИМИТАМИ ПАМЯТИ       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

# Функция для преобразования памяти в МБ
memory_to_mb() {
  local memory=$1
  if [[ $memory =~ ^([0-9]+)Gi$ ]]; then
    echo $((${BASH_REMATCH[1]} * 1024))
  elif [[ $memory =~ ^([0-9]+)Mi$ ]]; then
    echo ${memory%Mi}
  elif [[ $memory =~ ^([0-9]+)Ki$ ]]; then
    echo $((${memory%Ki} / 1024))
  else
    echo 0
  fi
}

echo -e "${YELLOW}Сканирую все deployments в кластере...${NC}\n"

# Порог для алерта (в МБ)
THRESHOLD_MB=512

found_oversized=false

# Для каждого deployment
kubectl get deployments -A -o json | jq -r '.items[] | 
  "\(.metadata.namespace)|\(.metadata.name)|\(.spec.replicas)|\(.spec.template.spec.containers[0].resources.requests.memory // "none")|\(.spec.template.spec.containers[0].resources.limits.memory // "none")"' | \
while IFS='|' read -r namespace name replicas req_mem lim_mem; do
  if [ "$req_mem" != "none" ] && [ "$req_mem" != "" ]; then
    req_mb=$(memory_to_mb "$req_mem")
    total_req_mb=$((req_mb * replicas))
    
    if [ $total_req_mb -gt $THRESHOLD_MB ]; then
      found_oversized=true
      
      lim_mb=$(memory_to_mb "$lim_mem")
      total_lim_mb=$((lim_mb * replicas))
      
      echo -e "${YELLOW}⚠️  Найден deployment с избыточными лимитами:${NC}"
      echo -e "   Namespace: ${BLUE}$namespace${NC}"
      echo -e "   Name:      ${BLUE}$name${NC}"
      echo -e "   Replicas:  ${RED}$replicas${NC}"
      echo -e "   Request/pod: ${YELLOW}$req_mem${NC} (total: $total_req_mb MB)"
      if [ "$lim_mem" != "none" ]; then
        echo -e "   Limit/pod:   ${YELLOW}$lim_mem${NC} (total: $total_lim_mb MB)"
      fi
      echo -e "   ${YELLOW}Рекомендуемое значение: 256Mi-512Mi${NC}"
      echo ""
    fi
  fi
done

if [ "$found_oversized" = false ]; then
  echo -e "${GREEN}✅ Не найдено deployments с избыточными лимитами памяти${NC}\n"
fi

# Также проверяем StatefulSets
echo -e "${YELLOW}Сканирую все statefulsets в кластере...${NC}\n"

kubectl get statefulsets -A -o json | jq -r '.items[] | 
  "\(.metadata.namespace)|\(.metadata.name)|\(.spec.replicas)|\(.spec.template.spec.containers[0].resources.requests.memory // "none")|\(.spec.template.spec.containers[0].resources.limits.memory // "none")"' | \
while IFS='|' read -r namespace name replicas req_mem lim_mem; do
  if [ "$req_mem" != "none" ] && [ "$req_mem" != "" ]; then
    req_mb=$(memory_to_mb "$req_mem")
    total_req_mb=$((req_mb * replicas))
    
    if [ $total_req_mb -gt $THRESHOLD_MB ]; then
      found_oversized=true
      
      lim_mb=$(memory_to_mb "$lim_mem")
      total_lim_mb=$((lim_mb * replicas))
      
      echo -e "${YELLOW}⚠️  Найден statefulset с избыточными лимитами:${NC}"
      echo -e "   Namespace: ${BLUE}$namespace${NC}"
      echo -e "   Name:      ${BLUE}$name${NC}"
      echo -e "   Replicas:  ${RED}$replicas${NC}"
      echo -e "   Request/pod: ${YELLOW}$req_mem${NC} (total: $total_req_mb MB)"
      if [ "$lim_mem" != "none" ]; then
        echo -e "   Limit/pod:   ${YELLOW}$lim_mem${NC} (total: $total_lim_mb MB)"
      fi
      echo -e "   ${YELLOW}Рекомендуемое значение: 256Mi-512Mi${NC}"
      echo ""
    fi
  fi
done

# Итоговая статистика
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}📊 ИТОГОВАЯ СТАТИСТИКА:${NC}\n"

total_mem_mb=0

kubectl get deployments,statefulsets -A -o json | jq -r '.items[] | 
  "\(.spec.replicas // 1)|\(.spec.template.spec.containers[0].resources.requests.memory // "none")"' | \
while IFS='|' read -r replicas req_mem; do
  if [ "$req_mem" != "none" ] && [ "$req_mem" != "" ]; then
    req_mb=$(memory_to_mb "$req_mem")
    total_req_mb=$((req_mb * replicas))
    echo "$total_req_mb"
  fi
done | awk '{sum+=$1} END {
  if (sum > 0) {
    printf "Суммарные requests памяти: %.2f Gi (%d MB)\n", sum/1024, sum
    if (sum > 97500) {
      printf "🚨 ПРЕВЫШЕНИЕ НА: %.2f Gi (суммарный allocatable ~97.5Gi)\n", (sum-97500)/1024
    }
  }
}'

echo ""
echo -e "${GREEN}Рекомендация: уменьшить requests для deployments выше 512MB${NC}"


