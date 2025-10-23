#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== АНАЛИЗ ИСПОЛЬЗОВАНИЯ ПАМЯТИ В КЛАСТЕРЕ ===${NC}\n"

# 1. Общая информация о узлах
echo -e "${YELLOW}1. ИНФОРМАЦИЯ О УЗЛАХ:${NC}"
kubectl get nodes -o custom-columns=NAME:.metadata.name,STATUS:.status.conditions[-1].type,CAPACITY:.status.capacity.memory,ALLOCATABLE:.status.allocatable.memory

# 2. Все Deployments с requests памяти
echo -e "\n${YELLOW}2. DEPLOYMENTS И ИХ REQUESTS ПАМЯТИ:${NC}"
kubectl get deployments --all-namespaces -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,REPLICAS:.spec.replicas,MEMORY_REQUEST:.spec.template.spec.containers[*].resources.requests.memory,MEMORY_LIMIT:.spec.template.spec.containers[*].resources.limits.memory

# 3. Все StatefulSets с requests памяти
echo -e "\n${YELLOW}3. STATEFULSETS И ИХ REQUESTS ПАМЯТИ:${NC}"
kubectl get statefulsets --all-namespaces -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,REPLICAS:.spec.replicas,MEMORY_REQUEST:.spec.template.spec.containers[*].resources.requests.memory,MEMORY_LIMIT:.spec.template.spec.containers[*].resources.limits.memory

# 4. Все DaemonSets с requests памяти
echo -e "\n${YELLOW}4. DAEMONSETS И ИХ REQUESTS ПАМЯТИ:${NC}"
kubectl get daemonsets --all-namespaces -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,MEMORY_REQUEST:.spec.template.spec.containers[*].resources.requests.memory,MEMORY_LIMIT:.spec.template.spec.containers[*].resources.limits.memory

# 5. Все запущенные поды и фактическое использование
echo -e "\n${YELLOW}5. ИСПОЛЬЗОВАНИЕ ПАМЯТИ ПО ПОДАМ:${NC}"
kubectl top pods --all-namespaces | head -30

# 6. Использование памяти по узлам
echo -e "\n${YELLOW}6. ИСПОЛЬЗОВАНИЕ ПАМЯТИ ПО УЗЛАМ:${NC}"
kubectl top nodes

# 7. Расчет общих requests по namespace
echo -e "\n${YELLOW}7. СУММАРНЫЕ REQUESTS ПО NAMESPACE:${NC}"
for ns in $(kubectl get namespaces -o name | cut -d'/' -f2); do
  echo -e "\nNamespace: ${BLUE}${ns}${NC}"
  kubectl get pods -n "$ns" -o json | \
    jq '.items[].spec.containers[].resources.requests.memory' | \
    grep -oE '^"[0-9]+(Mi|Gi|Ki)"' | \
    sed 's/"//g' | while read -r mem; do
    if [[ $mem == *"Gi" ]]; then
      echo "$mem" | sed 's/Gi//' | awk '{print $1 * 1024}'
    elif [[ $mem == *"Mi" ]]; then
      echo "$mem" | sed 's/Mi//'
    elif [[ $mem == *"Ki" ]]; then
      echo "$mem" | sed 's/Ki//' | awk '{print $1 / 1024}'
    fi
  done | awk '{sum+=$1} END {if (sum > 0) print "Total Requests: " sum " Mi (" int(sum/1024) " Gi)"}'
done

echo -e "\n${BLUE}=== КОНЕЦ АНАЛИЗА ===${NC}"


