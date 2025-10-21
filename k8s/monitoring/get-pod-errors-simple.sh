#!/bin/bash

# ============================================================
# GET POD ERRORS FROM LOGS - Получить все ошибки из логов
# ============================================================

NAMESPACE="${1:---all-namespaces}"
TAIL_LINES="${2:-50}"

echo "======================================================"
echo "Poisk oshibok v logakh podov"
echo "======================================================"
echo "Namespace: $NAMESPACE"
echo "Tail lines: $TAIL_LINES"
echo ""

# Get all pods
if [ "$NAMESPACE" = "--all-namespaces" ]; then
    PODS=$(kubectl get pods --all-namespaces -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\n"}{end}')
else
    PODS=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\n"}{end}')
fi

if [ -z "$PODS" ]; then
    echo "No pods found"
    exit 1
fi

ERROR_COUNT=0
POD_WITH_ERRORS=0

echo "Scanning pods for errors..."
echo ""

while IFS=$'\t' read -r ns pod; do
    # Get logs
    LOGS=$(kubectl logs -n "$ns" "$pod" --tail=$TAIL_LINES 2>/dev/null)
    
    if [ -z "$LOGS" ]; then
        LOGS=$(kubectl logs -n "$ns" "$pod" --previous --tail=$TAIL_LINES 2>/dev/null)
    fi
    
    # Search for errors
    ERRORS=$(echo "$LOGS" | grep -i "error\|failed\|exception\|crash\|fatal\|panic")
    
    if [ ! -z "$ERRORS" ]; then
        POD_WITH_ERRORS=$((POD_WITH_ERRORS + 1))
        
        echo "=============================================="
        echo "POD: $pod"
        echo "NAMESPACE: $ns"
        echo "=============================================="
        echo "$ERRORS" | head -20
        echo ""
    fi
done <<< "$PODS"

echo "======================================================"
echo "RESULTS:"
echo "======================================================"
echo "Total pods with errors: $POD_WITH_ERRORS"
echo "======================================================"
