#!/bin/bash

echo "=== Bazarr Pod Diagnostic Check ==="
echo "Timestamp: $(date)"
echo

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "ERROR: kubectl not found in PATH"
    exit 1
fi

# Check cluster connectivity
echo "1. Checking cluster connectivity..."
if ! kubectl cluster-info &> /dev/null; then
    echo "ERROR: Cannot connect to Kubernetes cluster"
    exit 1
fi
echo "✓ Cluster is reachable"
echo

# Check bazarr pod status
echo "2. Checking bazarr pod status..."
kubectl get pods -n arr | grep bazarr
echo

# Check PVC status
echo "3. Checking PVC status..."
echo "--- Config PVC ---"
kubectl get pvc servarr-bazarr -n arr
echo
echo "--- Media PVC ---"
kubectl get pvc servarr-jellyfin-media -n arr
echo

# Check PV status
echo "4. Checking PV status..."
kubectl get pv | grep -E "(servarr-bazarr|jellyfin-media)"
echo

# Check storage classes
echo "5. Checking storage classes..."
kubectl get storageclass
echo

# Check CSI driver pods
echo "6. Checking CSI driver status..."
kubectl get pods -A | grep csi
echo

# Check events for the bazarr pod
echo "7. Recent events for bazarr pod..."
kubectl get events -n arr --field-selector involvedObject.name=servarr-bazarr-ff667ff64-bn8rp --sort-by='.lastTimestamp' | tail -10
echo

# Check node status
echo "8. Checking node status..."
kubectl get nodes -o wide
echo

# Check if NFS server is accessible (if using NFS)
echo "9. Checking NFS connectivity..."
if kubectl get pv -o yaml | grep -q "nfs"; then
    echo "NFS PVs detected, checking connectivity..."
    NFS_SERVER=$(kubectl get pv -o yaml | grep -A5 "nfs:" | grep "server:" | head -1 | awk '{print $2}')
    if [ ! -z "$NFS_SERVER" ]; then
        echo "Testing NFS server: $NFS_SERVER"
        ping -c 1 $NFS_SERVER &> /dev/null && echo "✓ NFS server is reachable" || echo "✗ NFS server is not reachable"
    fi
else
    echo "No NFS PVs detected"
fi
echo

# Check volume mounts on the node
echo "10. Checking volume status on k8s-runner-1..."
kubectl get pods -n arr -o wide | grep bazarr
echo

echo "=== End of Diagnostic Check ==="