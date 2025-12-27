#!/bin/bash
# Kubernetes Cluster Startup Script
# This script starts the microk8s cluster in the correct order

set -e

echo "=========================================="
echo "Kubernetes Cluster Startup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Start control plane VM
echo -e "${YELLOW}Step 1: Starting control plane (k8s-control)...${NC}"
ssh root@192.168.2.10 "qm start 1500"
echo -e "${GREEN}Control plane VM started${NC}"
echo ""

# Step 2: Wait for control plane to boot
echo -e "${YELLOW}Step 2: Waiting for control plane to boot (60 seconds)...${NC}"
sleep 60
echo ""

# Step 3: Check control plane status
echo -e "${YELLOW}Step 3: Checking control plane status...${NC}"
ssh root@192.168.2.10 "qm status 1500"
echo ""

# Step 4: Wait for Kubernetes API to be ready
echo -e "${YELLOW}Step 4: Waiting for Kubernetes API to be ready...${NC}"
max_attempts=30
attempt=0
while ! kubectl get nodes &>/dev/null; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo -e "${RED}Kubernetes API did not become ready in time${NC}"
        exit 1
    fi
    echo "Waiting for Kubernetes API... (attempt $attempt/$max_attempts)"
    sleep 10
done
echo -e "${GREEN}Kubernetes API is ready${NC}"
echo ""

# Step 5: Check control plane node status
echo -e "${YELLOW}Step 5: Checking control plane node status...${NC}"
kubectl get node k8s-control
echo ""

# Step 6: Start worker node VM
echo -e "${YELLOW}Step 6: Starting worker node (k8s-runner-1)...${NC}"
ssh root@192.168.2.10 "qm start 1100"
echo -e "${GREEN}Worker node VM started${NC}"
echo ""

# Step 7: Wait for worker node to boot
echo -e "${YELLOW}Step 7: Waiting for worker node to boot (60 seconds)...${NC}"
sleep 60
echo ""

# Step 8: Check worker node status
echo -e "${YELLOW}Step 8: Checking worker node status...${NC}"
ssh root@192.168.2.10 "qm status 1100"
echo ""

# Step 9: Wait for worker node to join cluster
echo -e "${YELLOW}Step 9: Waiting for worker node to join cluster...${NC}"
max_attempts=30
attempt=0
while ! kubectl get node k8s-runner-1 &>/dev/null; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo -e "${RED}Worker node did not join cluster in time${NC}"
        exit 1
    fi
    echo "Waiting for worker node... (attempt $attempt/$max_attempts)"
    sleep 10
done
echo -e "${GREEN}Worker node joined cluster${NC}"
echo ""

# Step 10: Uncordon nodes
echo -e "${YELLOW}Step 10: Uncordoning nodes...${NC}"
kubectl uncordon k8s-control || true
kubectl uncordon k8s-runner-1 || true
echo -e "${GREEN}Nodes uncordoned${NC}"
echo ""

# Step 11: Wait for all nodes to be Ready
echo -e "${YELLOW}Step 11: Waiting for all nodes to be Ready...${NC}"
max_attempts=30
attempt=0
while [ $(kubectl get nodes --no-headers | grep -c "Ready") -lt 2 ]; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo -e "${RED}Not all nodes became Ready in time${NC}"
        kubectl get nodes
        exit 1
    fi
    echo "Waiting for nodes to be Ready... (attempt $attempt/$max_attempts)"
    sleep 10
done
echo -e "${GREEN}All nodes are Ready${NC}"
echo ""

# Step 12: Check cluster status
echo -e "${YELLOW}Step 12: Checking cluster status...${NC}"
kubectl get nodes -o wide
echo ""

# Step 13: Check system pods
echo -e "${YELLOW}Step 13: Checking system pods...${NC}"
kubectl get pods -n kube-system
echo ""

# Step 14: Wait for all pods to be running
echo -e "${YELLOW}Step 14: Waiting for critical pods to be running (60 seconds)...${NC}"
sleep 60
echo ""

# Step 15: Final cluster status
echo -e "${YELLOW}Step 15: Final cluster status...${NC}"
echo ""
echo "Nodes:"
kubectl get nodes
echo ""
echo "Pods by namespace:"
kubectl get pods --all-namespaces -o wide
echo ""

echo -e "${GREEN}=========================================="
echo "Cluster startup complete!"
echo "==========================================${NC}"
echo ""
echo -e "${YELLOW}Note: Some pods may still be initializing. Check with:${NC}"
echo "  kubectl get pods --all-namespaces"
