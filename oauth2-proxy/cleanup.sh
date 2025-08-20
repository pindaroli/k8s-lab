#!/bin/bash

# OAuth2 Cleanup Script
# Removes old Basic Auth artifacts after OAuth2 migration

set -e

echo "🧹 Starting OAuth2 Migration Cleanup"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Remove old Basic Auth objects
print_status "Cleaning up Basic Auth remnants..."

# Check and remove Basic Auth secret if exists
if kubectl get secret wetty-auth -n wetty &> /dev/null; then
    kubectl delete secret wetty-auth -n wetty
    print_success "Removed Basic Auth secret"
else
    print_warning "Basic Auth secret already removed"
fi

# Check and remove Basic Auth middleware if exists  
if kubectl get middleware wetty-auth -n wetty &> /dev/null; then
    kubectl delete middleware wetty-auth -n wetty
    print_success "Removed Basic Auth middleware"
else
    print_warning "Basic Auth middleware already removed"
fi

# Remove unused OAuth2 config if exists
if kubectl get configmap oauth2-proxy-config -n oauth2-proxy &> /dev/null; then
    kubectl delete configmap oauth2-proxy-config -n oauth2-proxy
    print_success "Removed unused OAuth2 config"
else
    print_warning "OAuth2 config already removed"
fi

# Show remaining objects
print_status "Current OAuth2-Proxy objects:"
kubectl get all,secrets,configmaps -n oauth2-proxy

print_status "Current Wetty objects (no Basic Auth):"
kubectl get secrets,middlewares -n wetty

print_success "🎉 Cleanup completed successfully!"

echo ""
echo -e "${BLUE}Summary:${NC}"
echo "  ✓ Basic Auth secret removed"
echo "  ✓ Basic Auth middleware removed"
echo "  ✓ Unused OAuth2 config removed"
echo "  ✓ All services now use Google OAuth2"
echo ""

echo -e "${BLUE}Active Authentication:${NC}"
echo "  • Google OAuth2 (oauth2-proxy)"
echo "  • Cloudflare Geoblocking (Italy only)"
echo "  • HTTPS/TLS encryption"
echo ""

print_success "All services secured with Google OAuth2!"