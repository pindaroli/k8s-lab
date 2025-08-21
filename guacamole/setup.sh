#!/bin/bash

# Guacamole Remote Desktop Gateway Setup Script
# Automatic installation of Apache Guacamole on Kubernetes

set -e

echo "🚀 Starting Guacamole installation..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl not found. Please install kubectl first."
    exit 1
fi

# Check if helm is available
if ! command -v helm &> /dev/null; then
    print_error "helm not found. Please install helm first."
    exit 1
fi

# Create namespace
print_status "Creating guacamole namespace..."
kubectl create namespace guacamole --dry-run=client -o yaml | kubectl apply -f -

# Add Helm repositories
print_status "Adding Helm repositories..."
helm repo add beryju https://charts.beryju.io
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install PostgreSQL
print_status "Installing PostgreSQL..."
helm upgrade --install postgresql bitnami/postgresql \
    --namespace guacamole \
    --set auth.username=guacamole \
    --set auth.password=password \
    --set auth.postgresPassword=password \
    --set auth.database=guacamole \
    --wait

# Install Guacamole
print_status "Installing Guacamole..."
helm upgrade --install guacamole beryju/guacamole \
    --namespace guacamole

# Wait for PostgreSQL to be ready
print_status "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod/postgresql-0 -n guacamole --timeout=300s

# Initialize database schema (workaround for init-container bug)
print_status "Initializing Guacamole database schema..."
print_warning "This step is required due to a bug in the BeryJu chart init-container"

kubectl run temp-init --image=guacamole/guacamole:1.6.0 --restart=Never -n guacamole --rm -i --tty -- /opt/guacamole/bin/initdb.sh --postgresql | kubectl exec -i postgresql-0 -n guacamole -- env PGPASSWORD=password psql -U guacamole -d guacamole

# Wait for Guacamole to be ready
print_status "Waiting for Guacamole pods to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=guacamole-guacamole -n guacamole --timeout=300s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=guacamole-guacd -n guacamole --timeout=300s

# Apply OAuth2 middleware
print_status "Creating OAuth2 middleware..."
kubectl apply -f oauth2-middleware.yaml

# Copy TLS secret from default namespace
print_status "Copying TLS certificate..."
if kubectl get secret pindaroli-wildcard-tls -n default &>/dev/null; then
    kubectl get secret pindaroli-wildcard-tls -o yaml | \
        sed 's/namespace: default/namespace: guacamole/' | \
        grep -v resourceVersion | \
        grep -v uid | \
        grep -v creationTimestamp | \
        kubectl apply -f -
else
    print_warning "TLS secret 'pindaroli-wildcard-tls' not found in default namespace"
    print_warning "You may need to manually create the TLS certificate"
fi

# Apply Traefik IngressRoute
print_status "Creating Traefik IngressRoute..."
kubectl apply -f guacamole-ingress-route.yaml

# Final status check
print_status "Checking deployment status..."
kubectl get pods -n guacamole

echo ""
echo "🎉 Guacamole installation completed!"
echo ""
echo "📋 Access Information:"
echo "   URL: https://guacamole.pindaroli.org"
echo "   Default Username: guacadmin"
echo "   Default Password: guacadmin"
echo ""
echo "🔐 Authentication:"
echo "   OAuth2 via Traefik middleware (Google)"
echo ""
echo "📊 Components:"
echo "   - Guacamole Web Interface (port 80)"
echo "   - Guacamole Daemon (port 4822)"
echo "   - PostgreSQL Database (port 5432)"
echo ""
echo "⚠️  Remember to:"
echo "   1. Change the default password after first login"
echo "   2. Configure your remote connections (VNC/RDP/SSH)"
echo "   3. Set up proper user permissions"
echo ""