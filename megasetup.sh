#!/bin/bash

set -e

echo "🚀 Starting NFS Provisioner and Servarr Mega Setup..."

echo "📦 Step 1: Installing NFS Subdir Provisioner..."
# Add the NFS subdir provisioner Helm repository
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm repo update

# Create the arr namespace
kubectl create namespace arr || echo "Namespace 'arr' already exists"

# Install NFS subdir provisioner
helm install nfs-subdir-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --namespace arr \
  --values nfs-provisioner/nfs-subdir-prov-values.yaml

echo "✅ NFS Subdir Provisioner installed successfully"

echo "💾 Step 2: Installing NFS CSI Driver and volumes..."
# Install NFS CSI driver
curl -skSL https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/deploy/install-driver.sh | bash

# Apply NFS CSI storage class and volumes
kubectl apply -f servarr/sc-nfs-csi.yaml
kubectl apply -f servarr/arr-volumes-csi.yaml

echo "✅ NFS CSI Driver and volumes configured successfully"

echo "🎬 Step 3: Installing Servarr Applications..."
# Add the servarr Helm repository
helm repo add kubitodev https://kubitodev.github.io/helm-charts/
helm repo update

# Install servarr stack
helm install servarr kubitodev/servarr \
  --namespace arr \
  --values servarr/arr-values.yaml

echo "✅ Servarr stack installed successfully"

echo "🎉 Mega Setup Complete!"
echo "📊 Check status with: kubectl get pods -n arr"
echo "🌐 Access services via their configured ingress or port-forwards"