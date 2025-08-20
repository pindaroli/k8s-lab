#!/bin/bash

# Wetty Deployment Script for K8s Lab
# Usage: ./deploy.sh

set -e

echo "🚀 Deploying Wetty Web Terminal..."

# 1. Deploy SSH public key to all targets
echo "📋 SSH Public Key (add to target hosts):"
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIByKEP2s/UBPL9/amLVJTF0pHbclzEwV5QNOBPkxIMTe wetty-service@k8s-lab"
echo ""

read -p "Have you added the SSH public key to all target hosts? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Please add the SSH public key to target hosts first"
    exit 1
fi

# 2. Copy TLS secret to wetty namespace
echo "🔐 Creating namespace and copying TLS secret..."
kubectl apply -f namespace.yaml

# Check if secret exists in default namespace
if kubectl get secret pindaroli-wildcard-tls >/dev/null 2>&1; then
    kubectl get secret pindaroli-wildcard-tls -o yaml | sed 's/namespace: .*/namespace: wetty/' | kubectl apply -f -
    echo "✅ TLS secret copied to wetty namespace"
else
    echo "⚠️  Warning: pindaroli-wildcard-tls secret not found in default namespace"
    echo "   Make sure TLS certificate is available for terminal.pindaroli.org"
fi

# 3. Deploy all components
echo "📦 Deploying Wetty components..."
kubectl apply -f secrets.yaml
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f middleware.yaml
kubectl apply -f ingressroute.yaml

# 4. Wait for deployment
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/wetty -n wetty

# 5. Show status
echo "📊 Deployment Status:"
kubectl get all -n wetty

echo ""
echo "✅ Wetty deployed successfully!"
echo "🌐 Access: https://terminal.pindaroli.org"
echo "🔑 Credentials: olindo / Compli61!"
echo ""
echo "📡 Target Hosts:"
echo "   • k8s-control (default): https://terminal.pindaroli.org"
echo "   • k8s-runner-1: https://terminal.pindaroli.org/?host=k8s-runner-1"
echo "   • Proxmox PVE: https://terminal.pindaroli.org/?host=pve"
echo "   • TrueNAS: https://terminal.pindaroli.org/?host=truenas"
echo ""
echo "🔍 To check logs: kubectl logs -n wetty -l app=wetty -f"