#!/bin/bash

# Wetty Web Terminal Deployment Script
# Automated deployment for Kubernetes wetty terminals

set -e

echo "🚀 Starting Wetty Web Terminal Deployment"

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

# Check if required files exist
REQUIRED_FILES=(
    "secrets.yaml"
    "configmap.yaml"
    "middleware.yaml"
    "deployment.yaml"
    "wetty-runner.yaml"
    "wetty-opnsense.yaml"
    "wetty-truenas.yaml"
    "ingressroute.yaml"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        print_error "Required file not found: $file"
        exit 1
    fi
done

print_success "All required files found"

# Create wetty namespace if it doesn't exist
print_status "Creating wetty namespace..."
if kubectl get namespace wetty &> /dev/null; then
    print_warning "Namespace 'wetty' already exists"
else
    kubectl create namespace wetty
    print_success "Created namespace 'wetty'"
fi

# Deploy SSH keys and configuration
print_status "Deploying SSH keys and configuration..."
kubectl apply -f secrets.yaml
kubectl apply -f configmap.yaml
print_success "SSH configuration deployed"

# Deploy middleware for security headers
print_status "Deploying Traefik middleware..."
kubectl apply -f middleware.yaml
print_success "Middleware deployed"

# Deploy wetty services
print_status "Deploying wetty services..."

echo "  - Deploying k8s-control terminal..."
kubectl apply -f deployment.yaml

echo "  - Deploying k8s-runner-1 terminal..."
kubectl apply -f wetty-runner.yaml

echo "  - Deploying opnsense terminal..."
kubectl apply -f wetty-opnsense.yaml

echo "  - Deploying truenas terminal..."
kubectl apply -f wetty-truenas.yaml

print_success "All wetty services deployed"

# Configure ingress routes
print_status "Configuring Traefik ingress routes..."
kubectl apply -f ingressroute.yaml
print_success "Ingress routes configured"

# Wait for deployments to be ready
print_status "Waiting for deployments to be ready..."

DEPLOYMENTS=("wetty-k8s-control" "wetty-runner" "wetty-opnsense" "wetty-truenas")

for deployment in "${DEPLOYMENTS[@]}"; do
    echo "  - Waiting for $deployment..."
    kubectl wait --for=condition=available --timeout=300s deployment/$deployment -n wetty
done

print_success "All deployments are ready"

# Check pod status
print_status "Checking pod status..."
kubectl get pods -n wetty

# Display access URLs
echo ""
print_success "🎉 Wetty Web Terminal deployment completed successfully!"
echo ""
echo -e "${BLUE}Access URLs:${NC}"
echo "  • Kubernetes Control: https://k8s-control.pindaroli.org"
echo "  • Kubernetes Worker:  https://k8s-runner-1.pindaroli.org"
echo "  • OPNsense Firewall:  https://opnsense.pindaroli.org"
echo "  • TrueNAS Storage:     https://truenas.pindaroli.org"
echo ""

echo -e "${BLUE}Authentication:${NC}"
echo "  • k8s-control, k8s-runner-1, opnsense: SSH key (automatic)"
echo "  • truenas: Username 'olindo' with password"
echo ""

echo -e "${BLUE}Useful Commands:${NC}"
echo "  kubectl get pods -n wetty                    # Check pod status"
echo "  kubectl logs -n wetty deployment/wetty-k8s-control  # View logs"
echo "  kubectl get ingressroute -n wetty            # Check ingress routes"
echo ""

# Optional: Display resource usage
if command -v kubectl &> /dev/null && kubectl auth can-i get pods --subresource=metrics &> /dev/null; then
    print_status "Resource usage:"
    kubectl top pods -n wetty 2>/dev/null || print_warning "Metrics not available (metrics-server might not be installed)"
fi

print_success "Deployment script completed"