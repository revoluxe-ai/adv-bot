#!/bin/bash

# Get All Pod Errors - bash version
# Ищет все ошибки в логах всех подов

echo "======================================================"
echo "GET ALL POD ERRORS - Poisk oshibok vo vsekh podakh"
echo "======================================================"

NAMESPACE="${1:-all}"
PATTERN="${2:-error|failed|exception|crash}"

if [ "$NAMESPACE" = "all" ]; then
    echo "Namespace: VSE (all)"
    NAMESPACES=$(kubectl get ns -o jsonpath='{.items[*].metadata.name}')
else
    echo "Namespace: $NAMESPACE"
    NAMESPACES=$NAMESPACE
fi

ERROR_COUNT=0
POD_COUNT=0
PODS_WITH_ERRORS=0

for ns in $NAMESPACES; do
    echo ""
    echo "───────────────────────────────────────────────────"
    echo "Namespace: $ns"
    echo "───────────────────────────────────────────────────"
    
    PODS=$(kubectl get pods -n "$ns" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    if [ -z "$PODS" ]; then
        echo "  (net podov ili oshibka dostupa)"
        continue
    fi
    
    for pod in $PODS; do
        POD_COUNT=$((POD_COUNT + 1))
        
        # Get pod status
        STATUS=$(kubectl get pod -n "$ns" "$pod" -o jsonpath='{.status.phase}' 2>/dev/null)
        
        # Get logs
        LOGS=$(kubectl logs -n "$ns" "$pod" --tail=100 2>/dev/null)
        
        if [ -z "$LOGS" ]; then
            LOGS=$(kubectl logs -n "$ns" "$pod" --previous --tail=100 2>/dev/null)
        fi
        
        # Search for errors (grep with case-insensitive)
        ERRORS=$(echo "$LOGS" | grep -iE "$PATTERN" 2>/dev/null)
        
        if [ ! -z "$ERRORS" ]; then
            PODS_WITH_ERRORS=$((PODS_WITH_ERRORS + 1))
            
            echo "  [ERROR] $pod [$STATUS]"
            echo "$ERRORS" | while read line; do
                ERROR_COUNT=$((ERROR_COUNT + 1))
                echo "    > $line"
            done
        else
            echo "  [OK] $pod [$STATUS]"
        fi
    done
done

# Summary
echo ""
echo "======================================================"
echo "ITOGI:"
echo "======================================================"
echo "Vsego proverenno podov: $POD_COUNT"
echo "Podov s oshibkami: $PODS_WITH_ERRORS"
echo "======================================================"

echo "Done!"

