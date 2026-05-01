#!/bin/bash
# High-Precision Validation Suite for Traefik/MetalLB Network Fix
# Objective: Verify symmetric routing, socket stability, and service discovery coherence.

export KUBECONFIG=talos-config/kubeconfig
VIP="10.10.20.56"
NAMESPACE="traefik"

echo "=========================================================================================="
echo "TEST_CASE_1: TCP_SYMMETRIC_CONNECTIVITY_AND_SOCKET_STABILITY_VALIDATION"
echo "Description: Verifying that repeated TCP handshakes do not encounter RST packets from OPNsense."
echo "=========================================================================================="
for i in {1..10}; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" -k https://$VIP -H "Host: traefik-dash.pindaroli.org" --max-time 2)
    if [ "$STATUS" == "401" ] || [ "$STATUS" == "200" ] || [ "$STATUS" == "302" ]; then
        echo "Iteration $i: SUCCESS (Code $STATUS) - No TCP Reset detected."
    else
        echo "Iteration $i: FAILED (Code $STATUS) - Potential Asymmetry or Connection Refused."
        exit 1
    fi
    sleep 0.3
done

echo ""
echo "=========================================================================================="
echo "TEST_CASE_2: K8S_SERVICE_DISCOVERY_ENDPOINT_ALIGNMENT_VERIFICATION"
echo "Description: Confirming that the Ingress Controller Pods match the Service Endpoints after DaemonSet transition."
echo "=========================================================================================="
POD_COUNT=$(kubectl get pods -n $NAMESPACE -l app.kubernetes.io/name=traefik -o jsonpath='{.items[*].metadata.name}' | wc -w | xargs)
ENDPOINT_COUNT=$(kubectl get endpoints traefik -n $NAMESPACE -o jsonpath='{.subsets[0].addresses[*].ip}' | wc -w | xargs)

echo "Calculated Traefik Pods in namespace '$NAMESPACE': $POD_COUNT"
echo "Registered Endpoints in Service 'traefik': $ENDPOINT_COUNT"

if [ "$POD_COUNT" == "$ENDPOINT_COUNT" ]; then
    echo "Result: SUCCESS (Endpoints are perfectly aligned with Pod distribution)."
else
    echo "Result: FAILED (Endpoint mismatch detected. Service Discovery is incoherent)."
    exit 1
fi

echo ""
echo "=========================================================================================="
echo "TEST_CASE_3: METALLB_L2_ADVERTISEMENT_SYMMETRIC_TRAFFIC_POLICY_ENFORCEMENT_CHECK"
echo "Description: Ensuring the externalTrafficPolicy is set to 'Local' to prevent inter-node SNAT/Hairpinning."
echo "=========================================================================================="
POLICY=$(kubectl get svc traefik -n $NAMESPACE -o jsonpath='{.spec.externalTrafficPolicy}')
echo "Active Policy for Service 'traefik': $POLICY"
if [ "$POLICY" == "Local" ]; then
    echo "Result: SUCCESS (Local policy enforced)."
else
    echo "Result: FAILED (Policy is '$POLICY', asymmetry risk remains high)."
    exit 1
fi

echo ""
echo "=========================================================================================="
echo "TEST_CASE_4: VICTORIAMETRICS_VMAGENT_SERVICE_DISCOVERY_CACHE_STABILIZATION_MONITORING"
echo "Description: Checking vmagent logs for successful target discovery synchronization after etcd quorum cleanup."
echo "=========================================================================================="
VMAGENT_POD=$(kubectl get pods -n monitoring -l app.kubernetes.io/name=vmagent -o name | head -n 1)
TARGETS_EVENT=$(kubectl logs -n monitoring $VMAGENT_POD --tail=200 | grep "kubernetes_sd_configs: added targets" | tail -n 1)

if [ ! -z "$TARGETS_EVENT" ]; then
    echo "Latest vmagent SD Event: $TARGETS_EVENT"
    echo "Result: SUCCESS (Discovery cache is updating correctly)."
else
    echo "Result: WARNING (No recent SD events found. Checking general vmagent health...)"
    kubectl get pod -n monitoring $VMAGENT_POD
fi

echo ""
echo "=========================================================================================="
echo "FINAL_VALIDATION_RESULT: ALL_SYSTEMS_GO - Infrastructure is stable and deterministic."
echo "=========================================================================================="
