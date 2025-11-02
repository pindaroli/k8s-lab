#!/bin/bash
# Graceful Kubernetes Cluster Shutdown Script
# This script safely shuts down the microk8s cluster in the correct order

set -e

echo "=========================================="
echo "Kubernetes Cluster Graceful Shutdown"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Drain worker node
echo -e "${YELLOW}Step 1: Draining worker node k8s-runner-1...${NC}"
kubectl drain k8s-runner-1 --ignore-daemonsets --delete-emptydir-data --force || true
echo -e "${GREEN}Worker node drained${NC}"
echo ""

# Step 2: Wait for pods to migrate
echo -e "${YELLOW}Step 2: Waiting for pods to migrate (30 seconds)...${NC}"
sleep 30
echo ""

# Step 3: Drain control plane
echo -e "${YELLOW}Step 3: Draining control plane k8s-control...${NC}"
kubectl drain k8s-control --ignore-daemonsets --delete-emptydir-data --force || true
echo -e "${GREEN}Control plane drained${NC}"
echo ""

# Step 4: Check remaining pods
echo -e "${YELLOW}Step 4: Checking remaining pods...${NC}"
kubectl get pods --all-namespaces -o wide
echo ""

# Step 5: Shutdown worker node VM
echo -e "${YELLOW}Step 5: Shutting down worker node (k8s-runner-1)...${NC}"
ssh root@192.168.1.10 "qm shutdown 1100 --timeout 120"
echo -e "${GREEN}Worker node shutdown initiated${NC}"
echo ""

# Step 6: Wait for worker to shutdown
echo -e "${YELLOW}Step 6: Waiting for worker node to shutdown (60 seconds)...${NC}"
sleep 60
echo ""

# Step 7: Shutdown control plane VM
echo -e "${YELLOW}Step 7: Shutting down control plane (k8s-control)...${NC}"
ssh root@192.168.1.10 "qm shutdown 1500 --timeout 120"
echo -e "${GREEN}Control plane shutdown initiated${NC}"
echo ""

# Step 8: Wait for control plane to shutdown
echo -e "${YELLOW}Step 8: Waiting for control plane to shutdown (60 seconds)...${NC}"
sleep 60
echo ""

# Step 9: Verify shutdown
echo -e "${YELLOW}Step 9: Verifying VMs are stopped...${NC}"
ssh root@192.168.1.10 "qm status 1100 && qm status 1500"
echo ""

echo -e "${GREEN}=========================================="
echo "Cluster shutdown complete!"
echo "==========================================${NC}"
