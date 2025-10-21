#!/bin/bash

set -e  # Exit on error

# Цвета
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🔧 ПРИМЕНЕНИЕ ИСПРАВЛЕНИЙ ПЕРЕГРУЗКИ ПАМЯТИ              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

# ШАГ 1: Обновить deployment
echo -e "${YELLOW}[1/5]${NC} Обновляю deployment wbgram-original..."
kubectl apply -f wbgram-original-deployment.yaml
echo -e "${GREEN}✅ Deployment обновлен${NC}\n"

# ШАГ 2: Применить ResourceQuota для default namespace
echo -e "${YELLOW}[2/5]${NC} Применяю ResourceQuota и LimitRange для namespace default..."
kubectl apply -f k8s/monitoring/resourcequota-default.yaml
echo -e "${GREEN}✅ ResourceQuota для default применен${NC}\n"

# ШАГ 3: Применить ResourceQuota для kube-prometheus-stack
echo -e "${YELLOW}[3/5]${NC} Проверяю наличие namespace kube-prometheus-stack..."
if kubectl get namespace kube-prometheus-stack &> /dev/null; then
  echo -e "${YELLOW}[3/5]${NC} Применяю ResourceQuota и LimitRange для kube-prometheus-stack..."
  kubectl apply -f k8s/monitoring/resourcequota-kube-prometheus-stack.yaml
  echo -e "${GREEN}✅ ResourceQuota для kube-prometheus-stack применен${NC}\n"
else
  echo -e "${YELLOW}[3/5]${NC} Namespace kube-prometheus-stack не найден. Пропускаю...${NC}\n"
fi

# ШАГ 4: Перезагрузить deployment
echo -e "${YELLOW}[4/5]${NC} Перезагружаю deployment wbgram-original..."
kubectl rollout restart deployment wbgram-original -n default
kubectl rollout status deployment wbgram-original -n default --timeout=5m
echo -e "${GREEN}✅ Deployment перезагружен успешно${NC}\n"

# ШАГ 5: Проверить статус
echo -e "${YELLOW}[5/5]${NC} Проверяю статус ресурсов...\n"

echo -e "${BLUE}═══ ResourceQuota ═══${NC}"
kubectl get resourcequota -A
echo ""

echo -e "${BLUE}═══ LimitRange ═══${NC}"
kubectl get limitrange -A
echo ""

echo -e "${BLUE}═══ Использование памяти по узлам ═══${NC}"
kubectl top nodes 2>/dev/null || echo "Metrics Server не установлен. Пропускаю..."
echo ""

echo -e "${BLUE}═══ Статус подов ═══${NC}"
kubectl get pods -n default --field-selector=metadata.name=wbgram-original
echo ""

echo -e "${GREEN}✅ ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ УСПЕШНО!${NC}\n"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  📋 СЛЕДУЮЩИЕ ДЕЙСТВИЯ:                                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

echo "1. Проверить логи подов:"
echo -e "   ${YELLOW}kubectl logs deployment/wbgram-original -n default${NC}\n"

echo "2. Проверить статус ResourceQuota:"
echo -e "   ${YELLOW}kubectl describe resourcequota default-quota -n default${NC}\n"

echo "3. Мониторить использование памяти:"
echo -e "   ${YELLOW}kubectl top pods -A --sort-by=memory${NC}\n"

echo "4. Проверить, исчезла ли ошибка в Prometheus/Alertmanager"
echo ""

echo -e "${GREEN}📖 Полная документация в k8s/MEMORY_OVERCOMMIT_FIX.md${NC}"


