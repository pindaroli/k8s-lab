#!/bin/bash

# Wetty Web Terminal Undeployment Script
# Removes all wetty components from Kubernetes cluster

set -e

echo "🗑️  Starting Wetty Web Terminal Undeployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl not found. Please install kubectl and configure access to your cluster."
    exit 1
fi

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

print_success "Connected to Kubernetes cluster"

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_status "Working directory: $SCRIPT_DIR"

# Check if wetty namespace exists
if ! kubectl get namespace wetty &> /dev/null; then
    print_warning "Namespace 'wetty' does not exist. Nothing to undeploy."
    exit 0
fi

# Confirmation prompt
echo ""
print_warning "This will remove all wetty components from your cluster:"
echo "  • All wetty deployments and pods"
echo "  • Services and ingress routes"
echo "  • SSH keys and configuration"
echo "  • The entire 'wetty' namespace"
echo ""

read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Undeployment cancelled by user"
    exit 0
fi

print_status "Starting undeployment process..."

# Remove ingress routes first to stop external access
if [[ -f "ingressroute.yaml" ]]; then
    print_status "Removing Traefik ingress routes..."
    kubectl delete -f ingressroute.yaml --ignore-not-found=true
    print_success "Ingress routes removed"
fi

# Remove individual deployments
DEPLOYMENT_FILES=(
    "deployment.yaml"
    "wetty-runner.yaml"
    "wetty-opnsense.yaml"
    "wetty-truenas.yaml"
)

print_status "Removing wetty services..."
for file in "${DEPLOYMENT_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "  - Removing components from $file..."
        kubectl delete -f "$file" --ignore-not-found=true
    fi
done

# Remove middleware
if [[ -f "middleware.yaml" ]]; then
    print_status "Removing Traefik middleware..."
    kubectl delete -f middleware.yaml --ignore-not-found=true
    print_success "Middleware removed"
fi

# Remove configuration and secrets
if [[ -f "configmap.yaml" ]]; then
    print_status "Removing configuration..."
    kubectl delete -f configmap.yaml --ignore-not-found=true
fi

if [[ -f "secrets.yaml" ]]; then
    print_status "Removing SSH keys and secrets..."
    kubectl delete -f secrets.yaml --ignore-not-found=true
fi

print_success "All components removed"

# Wait for pods to terminate
print_status "Waiting for pods to terminate..."
kubectl wait --for=delete pods --all -n wetty --timeout=60s 2>/dev/null || print_warning "Some pods may still be terminating"

# Remove namespace
print_status "Removing wetty namespace..."
kubectl delete namespace wetty --ignore-not-found=true
print_success "Namespace removed"

# Verify cleanup
print_status "Verifying cleanup..."
if kubectl get namespace wetty &> /dev/null; then
    print_warning "Namespace 'wetty' still exists (may be in terminating state)"
else
    print_success "Namespace 'wetty' successfully removed"
fi

echo ""
print_success "🎉 Wetty Web Terminal undeployment completed successfully!"
echo ""

echo -e "${BLUE}Cleanup Summary:${NC}"
echo "  ✓ All wetty deployments removed"
echo "  ✓ Services and ingress routes removed"
echo "  ✓ SSH keys and secrets removed"
echo "  ✓ Traefik middleware removed"
echo "  ✓ Namespace 'wetty' removed"
echo ""

echo -e "${YELLOW}Note:${NC} The following URLs are no longer accessible:"
echo "  • https://k8s-control.pindaroli.org"
echo "  • https://k8s-runner-1.pindaroli.org"
echo "  • https://opnsense.pindaroli.org"
echo "  • https://truenas.pindaroli.org"
echo ""

echo -e "${BLUE}To redeploy wetty:${NC}"
echo "  ./deploy.sh"
echo ""

print_success "Undeployment script completed"