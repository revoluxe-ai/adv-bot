#!/bin/bash

# ===================================================
# Error Log Monitoring Installation Script
# ===================================================
# Установит систему сбора ошибок и отправки в Telegram
# 
# Usage: ./INSTALL_ERROR_MONITORING.sh
# ===================================================

set -e

echo "🚀 Installing Error Log Monitoring System..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. RBAC
echo ""
echo "1️⃣  Applying RBAC Permissions..."
kubectl apply -f k8s/monitoring/log-error-aggregator-rbac.yaml

# 2. CronJob + ConfigMap
echo ""
echo "2️⃣  Applying CronJob + ConfigMap..."
kubectl apply -f k8s/monitoring/log-error-aggregator-final.yaml

# 3. PrometheusRules
echo ""
echo "3️⃣  Applying PrometheusRules..."
kubectl apply -f k8s/monitoring/application-error-rule.yaml

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Installation Complete!"
echo ""
echo "📊 Status:"
kubectl get cronjob -n kube-prometheus-stack log-error-aggregator
echo ""
echo "🧪 Test the installation:"
echo "   kubectl create job --from=cronjob/log-error-aggregator test-job -n kube-prometheus-stack"
echo "   kubectl logs -n kube-prometheus-stack job/test-job --tail=20"
echo ""
echo "📚 Documentation: ERROR_MONITORING_COMPLETE_SETUP.md"

