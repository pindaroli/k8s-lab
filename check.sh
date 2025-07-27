#!/bin/bash

echo "🔍 Checking MicroK8s Cluster and Megasetup Installation Status..."
echo

echo "🏗️ CLUSTER STATUS"
echo "=================="
echo "Cluster nodes:"
kubectl get nodes -o wide

echo
echo "Node resources:"
kubectl top nodes 2>/dev/null || echo "⚠️  Metrics server not available"

echo
echo "📦 NAMESPACE STATUS"
echo "==================="
kubectl get namespaces | grep -E "(NAME|arr|default|kube-system)"

echo
echo "🗄️ STORAGE CLASSES"
echo "==================="
kubectl get storageclass

echo
echo "💾 PERSISTENT VOLUMES"
echo "====================="
kubectl get pv

echo
echo "💿 PERSISTENT VOLUME CLAIMS"
echo "============================"
kubectl get pvc -n arr

echo
echo "🚀 NFS PROVISIONER STATUS"
echo "=========================="
echo "NFS Subdir Provisioner:"
kubectl get pods -n arr -l app=nfs-subdir-external-provisioner
kubectl get deployment -n arr nfs-subdir-provisioner 2>/dev/null || echo "NFS Subdir Provisioner deployment not found"

echo
echo "NFS CSI Driver:"
kubectl get pods -n kube-system | grep nfs-csi || echo "NFS CSI Driver pods not found"
kubectl get csidriver nfs.csi.k8s.io 2>/dev/null || echo "NFS CSI Driver not registered"

echo
echo "🎬 SERVARR APPLICATIONS STATUS"
echo "==============================="
echo "All pods in arr namespace:"
kubectl get pods -n arr -o wide

echo
echo "Services in arr namespace:"
kubectl get svc -n arr

echo
echo "Ingress resources:"
kubectl get ingress -n arr 2>/dev/null || echo "No ingress resources found"

echo
echo "🔧 HELM RELEASES"
echo "================"
helm list -n arr

echo
echo "📊 DETAILED POD STATUS"
echo "======================="
echo "Pod readiness and restart counts:"
kubectl get pods -n arr -o custom-columns=NAME:.metadata.name,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,STATUS:.status.phase

echo
echo "📋 RECENT EVENTS"
echo "================"
echo "Recent events in arr namespace:"
kubectl get events -n arr --sort-by='.lastTimestamp' | tail -10

echo
echo "🏥 HEALTH CHECK SUMMARY"
echo "======================="
NOT_READY=$(kubectl get pods -n arr --no-headers | grep -v Running | wc -l)
TOTAL_PODS=$(kubectl get pods -n arr --no-headers | wc -l)
READY_PODS=$((TOTAL_PODS - NOT_READY))

echo "📈 Pods Status: $READY_PODS/$TOTAL_PODS running"

if [ $NOT_READY -eq 0 ]; then
    echo "✅ All pods are running successfully!"
else
    echo "⚠️  Some pods are not ready. Check individual pod logs:"
    kubectl get pods -n arr | grep -v Running
    echo
    echo "💡 To debug, use: kubectl describe pod <pod-name> -n arr"
    echo "💡 To check logs: kubectl logs <pod-name> -n arr"
fi

echo
echo "🌐 ACCESS INFORMATION"
echo "====================="
echo "To access services, use port-forward:"
echo "kubectl port-forward svc/<service-name> <local-port>:<service-port> -n arr"
echo
echo "Available services:"
kubectl get svc -n arr --no-headers | awk '{print "- " $1 " (Port: " $5 ")"}'