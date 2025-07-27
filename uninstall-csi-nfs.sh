#!/bin/bash

echo "=== Uninstalling CSI NFS Driver ==="
echo "Timestamp: $(date)"
echo

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "ERROR: kubectl not found in PATH"
    exit 1
fi

# Check cluster connectivity
if ! kubectl cluster-info &> /dev/null; then
    echo "ERROR: Cannot connect to Kubernetes cluster"
    exit 1
fi

echo "1. Checking current CSI NFS driver installation..."
kubectl get pods -A | grep -i nfs

echo
echo "2. Removing CSI NFS driver components..."

# Remove CSI NFS driver pods
kubectl delete -f https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/deploy/example/kubernetes/csi-nfs-driverinfo.yaml --ignore-not-found=true
kubectl delete -f https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/deploy/example/kubernetes/csi-nfs-controller.yaml --ignore-not-found=true
kubectl delete -f https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/deploy/example/kubernetes/csi-nfs-node.yaml --ignore-not-found=true

# Remove RBAC
kubectl delete -f https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/deploy/example/kubernetes/rbac-csi-nfs.yaml --ignore-not-found=true

# Remove storage class if exists
kubectl delete storageclass nfs-csi --ignore-not-found=true

echo
echo "3. Checking for any remaining CSI NFS components..."
kubectl get csidriver | grep nfs
kubectl get pods -A | grep -i nfs

echo
echo "4. Cleaning up any stuck resources..."
# Force delete any stuck pods
kubectl get pods -A | grep -i nfs | grep Terminating | awk '{print $2 " -n " $1}' | xargs -r kubectl delete pod --force --grace-period=0

# Clean up finalizers if needed
kubectl get csidriver nfs.csi.k8s.io -o yaml | kubectl patch csidriver nfs.csi.k8s.io --type merge -p '{"metadata":{"finalizers":null}}' 2>/dev/null

echo
echo "=== CSI NFS Driver Uninstallation Complete ==="