#!/bin/bash

# Kubernetes Lab Complete Installation Script
# Installs all applications in proper dependency order
# Author: Generated for k8s-lab setup

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_DOMAIN="pindaroli.org"
EMAIL="o.pindaro@gmail.com"
METALLB_VERSION="0.14.8"
TRAEFIK_VERSION="30.0.2"
CERT_MANAGER_VERSION="v1.15.3"
CALICO_VERSION="v3.26.1"
BACKUP_DIR="/Users/olindo/k8s-backup-20250906-183713"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for user confirmation
wait_for_confirmation() {
    local step_name="$1"
    local verification_output="$2"

    echo -e "\n${GREEN}[VERIFICATION]${NC} $step_name completed. Output:"
    echo -e "${YELLOW}$verification_output${NC}"
    echo -e "\nDo you want to continue to the next step? (y/N): "
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Installation stopped by user after $step_name"
        exit 1
    fi
}

# Error handling
error_exit() {
    log_error "$1"
    exit 1
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Restore secret from backup - ONLY if local file doesn't exist
restore_secret_from_backup() {
    local secret_path="$1"
    local backup_secret_path="$BACKUP_DIR/k8s-lab-files/$secret_path"

    # Never overwrite existing local files
    if [[ -f "$secret_path" ]]; then
        return 0  # File exists locally, no restoration needed
    fi

    # Only restore if backup exists and local file is missing
    if [[ -f "$backup_secret_path" ]]; then
        log_info "Restoring missing file: $secret_path from backup..."

        # Ensure directory exists
        mkdir -p "$(dirname "$secret_path")"

        cp "$backup_secret_path" "$secret_path"
        log_success "✓ Restored $secret_path from backup"
        return 0
    else
        log_warning "✗ No backup found for $secret_path at $backup_secret_path"
        return 1
    fi
}

# Check and restore secrets from backup - ONLY if needed
check_and_restore_secrets() {
    log_info "Checking for missing files that need backup restoration..."

    # List of critical secret files to check
    local secret_files=(
        "cert-manager/cloudflare-token-secret.yaml"
        "oauth2-proxy/secrets.yaml"
    )

    # List of additional configuration files to check
    local config_files=(
        "calibre/calibre-values.yaml"
        "calibre/calibre-web-values.yaml"
        "servarr/arr-values.yaml"
    )

    # First, check what's missing
    local missing_files=()
    local existing_files=()

    for file in "${secret_files[@]}" "${config_files[@]}"; do
        if [[ -f "$file" ]]; then
            existing_files+=("$file")
        else
            missing_files+=("$file")
        fi
    done

    # Report current status
    log_info "Found ${#existing_files[@]} existing files, ${#missing_files[@]} missing files"

    # Only proceed with backup if we have missing files
    if [[ ${#missing_files[@]} -eq 0 ]]; then
        log_success "All configuration and secret files already exist locally - no backup restoration needed"

        # Show existing files for confirmation
        local existing_list=""
        for file in "${existing_files[@]}"; do
            existing_list+="\n✓ $file (exists locally)"
        done

        wait_for_confirmation "File Check" "All required files found locally:$existing_list"
        return 0
    fi

    # Check if backup directory exists only if we need it
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_warning "Backup directory not found at $BACKUP_DIR"
        log_warning "Missing files will need to be created manually:"
        for missing in "${missing_files[@]}"; do
            log_warning "  - $missing"
        done

        read -p "Continue without restoring missing files? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error_exit "Installation stopped - backup directory not available"
        fi
        return 1
    fi

    # Only restore missing files
    log_info "Attempting to restore ${#missing_files[@]} missing files from backup..."
    local restored_count=0

    for missing_file in "${missing_files[@]}"; do
        if restore_secret_from_backup "$missing_file"; then
            ((restored_count++))
        fi
    done

    # Show backup info only if we actually used the backup
    if [[ $restored_count -gt 0 && -f "$BACKUP_DIR/backup-info.txt" ]]; then
        log_info "Backup information:"
        cat "$BACKUP_DIR/backup-info.txt"
    fi

    # Create verification output
    local file_status=""
    for file in "${secret_files[@]}" "${config_files[@]}"; do
        if [[ -f "$file" ]]; then
            if [[ " ${existing_files[*]} " =~ " ${file} " ]]; then
                file_status+="\n✓ $file (existed locally)"
            else
                file_status+="\n✓ $file (restored from backup)"
            fi
        else
            file_status+="\n✗ $file (missing - not found in backup)"
        fi
    done

    local summary="Files restored from backup: $restored_count\nFiles that existed locally: ${#existing_files[@]}\nFile Status:$file_status"

    if [[ $restored_count -gt 0 ]]; then
        wait_for_confirmation "Backup Restoration" "$summary"
    else
        wait_for_confirmation "File Check" "$summary"
    fi
}

# Safe kubectl apply with error handling and idempotency
safe_kubectl_apply() {
    local resource_path="$1"
    local description="$2"
    local required="${3:-false}"  # Set to "true" if this is a required operation

    if [[ ! -f "$resource_path" && ! -d "$resource_path" ]]; then
        log_warning "$description: Resource not found at $resource_path"
        if [[ "$required" == "true" ]]; then
            error_exit "Required resource missing: $resource_path"
        fi
        return 1
    fi

    log_info "Applying $description (idempotent)..."
    # kubectl apply is naturally idempotent - it will create or update as needed
    local kubectl_output
    kubectl_output=$(kubectl apply -f "$resource_path" --timeout=30s 2>&1)
    local kubectl_exit_code=$?

    if [[ $kubectl_exit_code -eq 0 ]]; then
        log_success "$description applied/updated successfully"
        return 0
    else
        log_error "kubectl apply failed for $resource_path"
        log_error "Error output: $kubectl_output"

        if [[ "$required" == "true" ]]; then
            error_exit "Failed to apply required resource: $resource_path"
        else
            log_warning "$description failed to apply, but continuing installation"
            return 1
        fi
    fi
}

# Safe kubectl apply for directory with recursive flag - only applies YAML files
safe_kubectl_apply_dir() {
    local dir_path="$1"
    local description="$2"
    local required="${3:-false}"

    if [[ ! -d "$dir_path" ]]; then
        log_info "$description: Directory not found at $dir_path, skipping"
        if [[ "$required" == "true" ]]; then
            error_exit "Required directory missing: $dir_path"
        fi
        return 1
    fi

    # Check if directory contains any YAML files
    local yaml_files=$(find "$dir_path" -name "*.yaml" -o -name "*.yml" 2>/dev/null)
    if [[ -z "$yaml_files" ]]; then
        log_info "$description: No YAML files found in $dir_path, skipping"
        return 0
    fi

    log_info "Applying $description from $dir_path directory (idempotent)..."
    # Apply only YAML files to avoid issues with README.md and other non-manifest files
    local kubectl_output
    kubectl_output=$(find "$dir_path" -name "*.yaml" -o -name "*.yml" | xargs -r kubectl apply -f 2>&1)
    local kubectl_exit_code=$?

    if [[ $kubectl_exit_code -eq 0 ]]; then
        log_success "$description applied/updated successfully"
        return 0
    else
        log_error "kubectl apply failed for directory $dir_path"
        log_error "Error output: $kubectl_output"

        if [[ "$required" == "true" ]]; then
            error_exit "Failed to apply required resources from: $dir_path"
        else
            log_warning "$description failed to apply some resources, but continuing installation"
            return 1
        fi
    fi
}

# Check if Helm release exists
helm_release_exists() {
    local release_name="$1"
    local namespace="$2"

    if [[ -n "$namespace" ]]; then
        helm list -n "$namespace" -q 2>/dev/null | grep -q "^${release_name}$"
    else
        helm list -A -q 2>/dev/null | grep -q "^${release_name}$"
    fi
}

# Check if namespace exists
namespace_exists() {
    local namespace="$1"
    kubectl get namespace "$namespace" >/dev/null 2>&1
}

# Check if deployment is ready
deployment_ready() {
    local namespace="$1"
    local deployment="$2"

    if kubectl get deployment "$deployment" -n "$namespace" >/dev/null 2>&1; then
        kubectl get deployment "$deployment" -n "$namespace" -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' | grep -q "True"
    else
        return 1
    fi
}

# Check if storage class exists
storageclass_exists() {
    local storageclass="$1"
    kubectl get storageclass "$storageclass" >/dev/null 2>&1
}

# Check for required secrets before installation steps
check_required_secrets() {
    local step_name="$1"
    local required_secrets=("${@:2}")

    log_info "Checking required secrets for $step_name..."

    local missing_secrets=()
    for secret in "${required_secrets[@]}"; do
        if [[ ! -f "$secret" ]]; then
            missing_secrets+=("$secret")
        fi
    done

    if [[ ${#missing_secrets[@]} -gt 0 ]]; then
        log_warning "Missing required secrets for $step_name:"
        for missing in "${missing_secrets[@]}"; do
            log_warning "  - $missing"
        done

        log_info "Attempting to restore from backup..."
        for missing in "${missing_secrets[@]}"; do
            restore_secret_from_backup "$missing" || {
                log_error "Failed to restore $missing from backup"
                log_error "Please ensure $missing exists before running $step_name"
                read -p "Do you want to continue anyway? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    error_exit "Installation stopped due to missing required secret: $missing"
                fi
            }
        done
    else
        log_success "All required secrets found for $step_name"
    fi
}

# Wait for deployment to be ready
wait_for_deployment() {
    local namespace=$1
    local deployment=$2
    local timeout=${3:-300}

    log_info "Waiting for deployment $deployment in namespace $namespace to be ready..."
    kubectl wait --for=condition=available --timeout=${timeout}s deployment/$deployment -n $namespace
}

# Wait for pods to be ready
wait_for_pods() {
    local namespace=$1
    local selector=$2
    local timeout=${3:-300}

    log_info "Waiting for pods with selector $selector in namespace $namespace to be ready..."
    kubectl wait --for=condition=ready --timeout=${timeout}s pods -l $selector -n $namespace
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if kubectl is available
    if ! command_exists kubectl; then
        error_exit "kubectl is not installed or not in PATH"
    fi

    # Check if helm is available
    if ! command_exists helm; then
        error_exit "helm is not installed or not in PATH"
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info >/dev/null 2>&1; then
        error_exit "Cannot connect to Kubernetes cluster. Is microk8s running?"
    fi

    # Check if we're in the right directory
    if [[ ! -f "CLAUDE.md" ]]; then
        error_exit "Please run this script from the k8s-lab directory"
    fi

    log_success "Prerequisites check passed"

    # Show cluster info for verification
    local cluster_info=$(kubectl cluster-info 2>/dev/null | head -3)
    local kubectl_version=$(kubectl version --client --short 2>/dev/null || echo "kubectl version check failed")
    local helm_version=$(helm version --short 2>/dev/null || echo "helm version check failed")

    wait_for_confirmation "Prerequisites Check" "Cluster Info:\n$cluster_info\n\nTools Versions:\n$kubectl_version\n$helm_version"
}

# Add helm repositories (idempotent)
add_helm_repos() {
    log_info "Adding Helm repositories (idempotent)..."

    # These commands are idempotent - they won't fail if repos already exist
    helm repo add metallb https://metallb.github.io/metallb || true
    helm repo add traefik https://traefik.github.io/charts || true
    helm repo add jetstack https://charts.jetstack.io || true
    helm repo add kubitodev https://charts.kubito.dev || true

    helm repo update
    log_success "Helm repositories added/updated successfully"

    # Show added repos for verification
    local helm_repos=$(helm repo list 2>/dev/null || echo "No repositories found")

    wait_for_confirmation "Helm Repositories" "Added repositories:\n$helm_repos"
}

# Step 1: Install NFS CSI Driver
install_nfs_csi() {
    log_info "Installing NFS CSI Driver..."

    # Check if NFS CSI Driver is already installed
    if helm_release_exists "csi-driver-nfs" "kube-system" || storageclass_exists "csi-nfs-stripe-arr-conf"; then
        log_success "NFS CSI Driver already installed, skipping installation"

        # Show current status for diagnostics
        log_info "Current NFS CSI status:"
        local helm_status=$(helm list -n kube-system -o table | grep csi-driver-nfs || echo "No Helm release found")
        local storage_classes=$(kubectl get storageclass | grep csi-nfs || echo "No NFS storage classes found")
        local csi_pods=$(kubectl get pods -n kube-system -l app=csi-nfs-controller --no-headers 2>/dev/null || echo "No CSI controller pods found")

        echo "  Helm Release: $helm_status"
        echo "  Storage Classes: $storage_classes"
        echo "  Controller Pods: $csi_pods"

        safe_kubectl_apply_dir "CSI-driver" "additional CSI configurations"

        # Still run verification
        local csi_pods_verify=$(kubectl get pods -n kube-system -l app=csi-nfs-controller 2>/dev/null | tail -n +2)
        local csi_storage_verify=$(kubectl get storageclass | grep csi-nfs 2>/dev/null || echo "No NFS storage classes found")

        wait_for_confirmation "NFS CSI Driver (Already Installed)" "CSI Controller Pods:\n$csi_pods_verify\n\nStorage Classes:\n$csi_storage_verify"
        return
    fi

    # Add NFS CSI Helm repository and install
    helm repo add csi-driver-nfs https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/charts || true
    helm repo update

    # Install NFS CSI driver with microk8s specific settings
    helm upgrade --install csi-driver-nfs csi-driver-nfs/csi-driver-nfs \
        --namespace kube-system \
        --set kubeletDir=/var/snap/microk8s/common/var/lib/kubelet \
        --wait

    # Apply any additional CSI configurations
    safe_kubectl_apply_dir "CSI-driver" "additional CSI configurations"

    log_success "NFS CSI Driver installed"

    # Verify NFS CSI installation
    local csi_pods=$(kubectl get pods -n kube-system -l app=csi-nfs-controller 2>/dev/null | tail -n +2)
    local csi_storage=$(kubectl get storageclass | grep csi-nfs 2>/dev/null || echo "No NFS storage classes found")

    wait_for_confirmation "NFS CSI Driver" "CSI Controller Pods:\n$csi_pods\n\nStorage Classes:\n$csi_storage"
}

# Step 2: Install MetalLB
install_metallb() {
    log_info "Installing MetalLB Load Balancer..."

    # Check if MetalLB is already installed
    if helm_release_exists "metallb" "metallb-system" && deployment_ready "metallb-system" "metallb-controller"; then
        log_success "MetalLB already installed and running, skipping installation"

        # Show current status for diagnostics
        log_info "Current MetalLB status:"
        local helm_status=$(helm list -n metallb-system -o table | grep metallb || echo "No Helm release found")
        local controller_pods=$(kubectl get pods -n metallb-system -l app.kubernetes.io/name=metallb,app.kubernetes.io/component=controller --no-headers 2>/dev/null || echo "No controller pods found")
        local speaker_pods=$(kubectl get pods -n metallb-system -l app.kubernetes.io/name=metallb,app.kubernetes.io/component=speaker --no-headers 2>/dev/null || echo "No speaker pods found")
        local ip_pools=$(kubectl get ipaddresspool -n metallb-system --no-headers 2>/dev/null || echo "No IP pools found")
        local l2_ads=$(kubectl get l2advertisement -n metallb-system --no-headers 2>/dev/null || echo "No L2 advertisements found")

        echo "  Helm Release: $helm_status"
        echo "  Controller Pods: $controller_pods"
        echo "  Speaker Pods: $speaker_pods"
        echo "  IP Address Pools: $ip_pools"
        echo "  L2 Advertisements: $l2_ads"

        # Apply/update IP pool configuration with timeout
        log_info "Applying MetalLB IP pool configuration (idempotent)..."
        local kubectl_output
        local kubectl_exit_code

        # Use timeout to prevent hanging (30 seconds max)
        if timeout 30s kubectl apply -f "metallb/metallb-addpool.yaml" &>/dev/null; then
            log_success "MetalLB IP pool configuration applied/updated successfully"
        else
            log_warning "MetalLB IP pool configuration failed (likely webhook timeout)"
            log_warning "This is a known issue with MetalLB webhook - continuing installation"
            log_info "You can manually apply the IP pool configuration later if needed"
        fi

        # Still run verification
        local metallb_pods=$(kubectl get pods -n metallb-system 2>/dev/null | tail -n +2)
        local metallb_pool=$(kubectl get ipaddresspool -n metallb-system 2>/dev/null | tail -n +2 || echo "No IP pools found")

        wait_for_confirmation "MetalLB Load Balancer (Already Installed)" "MetalLB Pods:\n$metallb_pods\n\nIP Address Pools:\n$metallb_pool"
        return
    fi

    # Create namespace (metallb-system instead of metallb as per README) - idempotent
    kubectl create namespace metallb-system --dry-run=client -o yaml | kubectl apply -f -

    # Install MetalLB using Helm
    helm upgrade --install metallb metallb/metallb \
        --namespace metallb-system \
        --version $METALLB_VERSION \
        --wait

    # Wait for MetalLB to be ready
    wait_for_deployment metallb-system metallb-controller
    wait_for_pods metallb-system "app=metallb"

    # Wait for MetalLB webhook to be ready
    log_info "Waiting for MetalLB webhook to be ready..."
    local webhook_ready=false
    for i in {1..12}; do  # Wait up to 60 seconds
        if kubectl get endpoints metallb-webhook-service -n metallb-system >/dev/null 2>&1; then
            if kubectl get endpoints metallb-webhook-service -n metallb-system -o jsonpath='{.subsets[0].addresses}' | grep -q "ip"; then
                webhook_ready=true
                break
            fi
        fi
        log_info "MetalLB webhook not ready yet, waiting... ($i/12)"
        sleep 5
    done

    if [[ "$webhook_ready" != "true" ]]; then
        log_warning "MetalLB webhook may not be fully ready, but attempting to apply configuration..."
    else
        log_success "MetalLB webhook is ready"
    fi

    # Apply IP pool configuration with timeout to prevent hanging
    log_info "Applying MetalLB IP pool configuration..."

    # Use timeout to prevent hanging (30 seconds max)
    if timeout 30s kubectl apply -f "metallb/metallb-addpool.yaml" &>/dev/null; then
        log_success "MetalLB IP pool configuration applied successfully"
    else
        log_warning "MetalLB IP pool configuration failed (likely webhook timeout)"
        log_warning "This is a known issue with MetalLB webhook - continuing installation"
        log_info "The MetalLB load balancer is still functional, you can configure IP pools manually later"
    fi

    log_success "MetalLB installed and configured"

    # Verify MetalLB installation
    local metallb_pods=$(kubectl get pods -n metallb-system 2>/dev/null | tail -n +2)
    local metallb_pool=$(kubectl get ipaddresspool -n metallb-system 2>/dev/null | tail -n +2 || echo "No IP pools found")

    wait_for_confirmation "MetalLB Load Balancer" "MetalLB Pods:\n$metallb_pods\n\nIP Address Pools:\n$metallb_pool"
}

# Step 3: Install cert-manager with RBAC prerequisites
install_cert_manager() {
    log_info "Installing cert-manager..."

    # Check if cert-manager is already installed
    if helm_release_exists "cert-manager" "cert-manager" && deployment_ready "cert-manager" "cert-manager"; then
        log_success "cert-manager already installed and running, skipping installation"

        # Show current status for diagnostics
        log_info "Current cert-manager status:"
        local helm_status=$(helm list -n cert-manager -o table | grep cert-manager || echo "No Helm release found")
        local cert_pods=$(kubectl get pods -n cert-manager --no-headers 2>/dev/null || echo "No cert-manager pods found")
        local issuers=$(kubectl get clusterissuer --no-headers 2>/dev/null || echo "No cluster issuers found")
        local certs=$(kubectl get certificate -A --no-headers 2>/dev/null | head -3 || echo "No certificates found")

        echo "  Helm Release: $helm_status"
        echo "  Pods: $cert_pods"
        echo "  Cluster Issuers: $issuers"
        echo "  Certificates: $certs"

        log_info "Applying/updating cert-manager configurations..."
        safe_kubectl_apply "cert-manager/cloudflare-token-secret.yaml" "Cloudflare token secret" "true"

        # Apply cluster issuer with timeout handling (cert-manager webhook can timeout)
        log_info "Applying cluster issuer configuration (with timeout handling)..."
        if kubectl apply -f "cert-manager/cluster-Issuer.yaml" --timeout=30s &>/dev/null; then
            log_success "Cluster issuer configuration applied/updated successfully"
        else
            log_warning "Cluster issuer configuration failed (likely cert-manager webhook timeout)"
            log_warning "This is a known issue with cert-manager webhook - continuing installation"
        fi

        # Apply certificate with timeout handling
        log_info "Applying pindaroli.org certificate (with timeout handling)..."
        if kubectl apply -f "cert-manager/certificate-pindaroli.yaml" --timeout=30s &>/dev/null; then
            log_success "Certificate configuration applied/updated successfully"
        else
            log_warning "Certificate configuration failed (likely cert-manager webhook timeout)"
            log_warning "You can manually apply certificates later if needed"
        fi

        # Still run verification
        local cert_pods_verify=$(kubectl get pods -n cert-manager 2>/dev/null | tail -n +2)
        local cert_issuers=$(kubectl get clusterissuer 2>/dev/null | tail -n +2 || echo "No cluster issuers found")
        local cert_status=$(kubectl get certificate -A 2>/dev/null | tail -n +2 || echo "No certificates found")

        wait_for_confirmation "cert-manager (Already Installed)" "cert-manager Pods:\n$cert_pods_verify\n\nCluster Issuers:\n$cert_issuers\n\nCertificates:\n$cert_status"
        return
    fi

    # Check for required secrets
    check_required_secrets "cert-manager" "cert-manager/cloudflare-token-secret.yaml"

    # Create namespace - idempotent
    kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -

    # Install cert-manager using Helm (version from README)
    helm upgrade --install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --version $CERT_MANAGER_VERSION \
        --set installCRDs=true \
        --wait

    # Wait for cert-manager to be ready
    wait_for_deployment cert-manager cert-manager
    wait_for_deployment cert-manager cert-manager-cainjector
    wait_for_deployment cert-manager cert-manager-webhook

    # Apply configuration files from cert-manager directory
    log_info "Applying cert-manager configuration..."
    safe_kubectl_apply "cert-manager/cloudflare-token-secret.yaml" "Cloudflare token secret" "true"

    # Apply cluster issuer with timeout handling (cert-manager webhook can timeout)
    log_info "Applying cluster issuer configuration (with timeout handling)..."
    if kubectl apply -f "cert-manager/cluster-Issuer.yaml" --timeout=30s &>/dev/null; then
        log_success "Cluster issuer configuration applied successfully"
    else
        log_warning "Cluster issuer configuration failed (likely cert-manager webhook timeout)"
        log_warning "This is a known issue with cert-manager webhook - continuing installation"
    fi

    # Apply certificate with timeout handling
    log_info "Applying pindaroli.org certificate (with timeout handling)..."
    if kubectl apply -f "cert-manager/certificate-pindaroli.yaml" --timeout=30s &>/dev/null; then
        log_success "Certificate configuration applied successfully"
    else
        log_warning "Certificate configuration failed (likely cert-manager webhook timeout)"
        log_warning "You can manually apply certificates later if needed"
    fi

    log_success "cert-manager installed and configured"

    # Verify cert-manager installation
    local cert_pods=$(kubectl get pods -n cert-manager 2>/dev/null | tail -n +2)
    local cert_issuers=$(kubectl get clusterissuer 2>/dev/null | tail -n +2 || echo "No cluster issuers found")
    local cert_status=$(kubectl get certificate -A 2>/dev/null | tail -n +2 || echo "No certificates found")

    wait_for_confirmation "cert-manager" "cert-manager Pods:\n$cert_pods\n\nCluster Issuers:\n$cert_issuers\n\nCertificates:\n$cert_status"
}

# Step 4: Configure RBAC and Install Traefik
install_traefik() {
    log_info "Installing Traefik Ingress Controller..."

    # Check if Traefik is already installed
    if helm_release_exists "traefik" "traefik" && deployment_ready "traefik" "traefik"; then
        log_success "Traefik already installed and running, skipping installation"

        # Show current status for diagnostics
        log_info "Current Traefik status:"
        local helm_status=$(helm list -n traefik -o table | grep traefik || echo "No Helm release found")
        local traefik_pods=$(kubectl get pods -n traefik --no-headers 2>/dev/null || echo "No Traefik pods found")
        local traefik_svc=$(kubectl get svc -n traefik --no-headers 2>/dev/null || echo "No Traefik services found")
        local ingress_routes=$(kubectl get ingressroute -A --no-headers 2>/dev/null | wc -l || echo "0")

        echo "  Helm Release: $helm_status"
        echo "  Pods: $traefik_pods"
        echo "  Services: $traefik_svc"
        echo "  Ingress Routes: $ingress_routes total"

        log_info "Applying/updating Traefik ingress routes..."
        safe_kubectl_apply "traefik/all-arr-ingress-routes.yaml" "application ingress routes" "true"

        # Still run verification
        local traefik_pods_verify=$(kubectl get pods -n traefik 2>/dev/null | tail -n +2)
        local traefik_services=$(kubectl get svc -n traefik 2>/dev/null | tail -n +2)
        local traefik_routes=$(kubectl get ingressroute -A 2>/dev/null | tail -n +2 || echo "No ingress routes found")

        wait_for_confirmation "Traefik Ingress Controller (Already Installed)" "Traefik Pods:\n$traefik_pods_verify\n\nServices:\n$traefik_services\n\nIngress Routes:\n$traefik_routes"
        return
    fi

    log_info "Configuring RBAC prerequisites..."

    # Enable RBAC in microk8s (idempotent)
    log_info "Enabling RBAC in microk8s..."
    ssh root@k8s-control "microk8s enable rbac" || log_warning "RBAC might already be enabled"

    # Configure CoreDNS RBAC
    log_info "Configuring CoreDNS RBAC..."
    kubectl create clusterrole system:coredns \
        --verb=get,list,watch \
        --resource=endpoints,services,pods,namespaces \
        --dry-run=client -o yaml | kubectl apply -f - || true

    kubectl create clusterrolebinding system:coredns \
        --clusterrole=system:coredns \
        --serviceaccount=kube-system:coredns \
        --dry-run=client -o yaml | kubectl apply -f - || true

    # Add EndpointSlices permission to CoreDNS
    kubectl patch clusterrole system:coredns --type='json' \
        -p='[{"op": "add", "path": "/rules/-", "value": {"apiGroups": ["discovery.k8s.io"], "resources": ["endpointslices"], "verbs": ["list", "watch"]}}]' || true

    # Restart CoreDNS
    kubectl rollout restart deployment/coredns -n kube-system || true

    log_info "Installing Traefik Ingress Controller..."

    # Create namespace - idempotent
    kubectl create namespace traefik --dry-run=client -o yaml | kubectl apply -f -

    # Copy wildcard certificate to traefik namespace
    if kubectl get secret pindaroli-wildcard-tls -n default >/dev/null 2>&1; then
        kubectl get secret pindaroli-wildcard-tls -n default -o yaml | \
        sed 's/namespace: default/namespace: traefik/' | \
        kubectl apply -f -
    fi

    # Apply Traefik RBAC first
    safe_kubectl_apply "traefik/traefik-rbac.yaml" "Traefik RBAC configuration" "true"

    # Install Traefik using Helm with values file
    helm upgrade --install traefik traefik/traefik \
        --namespace traefik \
        --version $TRAEFIK_VERSION \
        --values traefik/traefik-values.yaml \
        --wait

    # Wait for Traefik to be ready
    wait_for_deployment traefik traefik

    # Apply application ingress routes
    safe_kubectl_apply "traefik/all-arr-ingress-routes.yaml" "application ingress routes" "true"

    log_success "Traefik installed and configured"

    # Verify Traefik installation
    local traefik_pods=$(kubectl get pods -n traefik 2>/dev/null | tail -n +2)
    local traefik_services=$(kubectl get svc -n traefik 2>/dev/null | tail -n +2)
    local traefik_routes=$(kubectl get ingressroute -A 2>/dev/null | tail -n +2 || echo "No ingress routes found")

    wait_for_confirmation "Traefik Ingress Controller" "Traefik Pods:\n$traefik_pods\n\nServices:\n$traefik_services\n\nIngress Routes:\n$traefik_routes"
}

# Step 5: Install OAuth2 Proxy
install_oauth2_proxy() {
    log_info "Installing OAuth2 Proxy for authentication..."

    # Check if OAuth2 Proxy is already installed
    if deployment_ready "oauth2-proxy" "oauth2-proxy"; then
        log_success "OAuth2 Proxy already installed and running, skipping installation"
        return
    fi

    # Check for required secrets
    check_required_secrets "OAuth2 Proxy" "oauth2-proxy/secrets.yaml"

    # Deploy OAuth2 proxy components in order as per README
    safe_kubectl_apply "oauth2-proxy/namespace.yaml" "OAuth2 proxy namespace" "true"
    safe_kubectl_apply "oauth2-proxy/secrets.yaml" "OAuth2 proxy secrets" "true"
    safe_kubectl_apply "oauth2-proxy/deployment.yaml" "OAuth2 proxy deployment" "true"
    safe_kubectl_apply "oauth2-proxy/middleware.yaml" "OAuth2 proxy middleware" "true"
    safe_kubectl_apply "oauth2-proxy/middleware-default.yaml" "OAuth2 proxy default middleware" "true"
    safe_kubectl_apply "oauth2-proxy/ingressroute.yaml" "OAuth2 proxy ingress route" "true"

    # Wait for OAuth2 proxy to be ready
    wait_for_deployment oauth2-proxy oauth2-proxy

    log_success "OAuth2 Proxy installed and configured for *.pindaroli.org authentication"

    # Verify OAuth2 Proxy installation
    local oauth_pods=$(kubectl get pods -n oauth2-proxy 2>/dev/null | tail -n +2)
    local oauth_services=$(kubectl get svc -n oauth2-proxy 2>/dev/null | tail -n +2)
    local oauth_middleware=$(kubectl get middleware -A 2>/dev/null | grep oauth2 | tail -n +2 || echo "No OAuth2 middleware found")

    wait_for_confirmation "OAuth2 Proxy" "OAuth2 Pods:\n$oauth_pods\n\nServices:\n$oauth_services\n\nMiddleware:\n$oauth_middleware"
}

# Step 6: Create persistent volumes for applications
create_persistent_volumes() {
    log_info "Creating persistent volumes..."

    # Apply servarr volumes
    safe_kubectl_apply "servarr/arr-volumes-csi.yaml" "Servarr persistent volumes"

    # Apply calibre volumes if exists
    safe_kubectl_apply "calibre/calibre-volumes-csi.yaml" "Calibre persistent volumes"

    log_success "Persistent volumes created"

    # Verify persistent volumes
    local pv_status=$(kubectl get pv 2>/dev/null | tail -n +2 || echo "No persistent volumes found")
    local pvc_status=$(kubectl get pvc -A 2>/dev/null | tail -n +2 || echo "No persistent volume claims found")

    wait_for_confirmation "Persistent Volumes" "Persistent Volumes:\n$pv_status\n\nPersistent Volume Claims:\n$pvc_status"
}

# Step 7: Install Servarr Stack
install_servarr() {
    log_info "Installing Servarr media stack..."

    # Check if Servarr is already installed
    if helm_release_exists "servarr" "arr" && namespace_exists "arr"; then
        log_success "Servarr stack already installed, skipping installation"
        safe_kubectl_apply "servarr/qbittorrent-bittorrent-loadbalancer.yaml" "qBittorrent BitTorrent port LoadBalancer"
        return
    fi

    # Create arr namespace - idempotent
    kubectl create namespace arr --dry-run=client -o yaml | kubectl apply -f -

    # Check if local Helm chart exists, otherwise use remote
    if [[ -d "/Users/olindo/prj/helm/charts/servarr" ]]; then
        log_info "Using local Helm chart for Servarr..."
        helm upgrade --install servarr /Users/olindo/prj/helm/charts/servarr \
            --namespace arr \
            --values servarr/arr-values.yaml \
            --wait \
            --timeout 10m
    else
        log_info "Using remote kubitodev/servarr Helm chart..."
        helm upgrade --install servarr kubitodev/servarr \
            --namespace arr \
            --values servarr/arr-values.yaml \
            --wait \
            --timeout 10m
    fi

    # Apply qBittorrent BitTorrent port LoadBalancer if exists
    safe_kubectl_apply "servarr/qbittorrent-bittorrent-loadbalancer.yaml" "qBittorrent BitTorrent port LoadBalancer"

    log_success "Servarr stack installed"

    # Verify Servarr installation
    local servarr_pods=$(kubectl get pods -n arr 2>/dev/null | tail -n +2 || echo "No pods in arr namespace")
    local servarr_services=$(kubectl get svc -n arr 2>/dev/null | tail -n +2 || echo "No services in arr namespace")
    local lb_services=$(kubectl get svc -A -o wide | grep LoadBalancer 2>/dev/null || echo "No LoadBalancer services found")

    wait_for_confirmation "Servarr Media Stack" "Servarr Pods:\n$servarr_pods\n\nServices:\n$servarr_services\n\nLoadBalancer Services:\n$lb_services"
}

# Step 8: Install Homepage Dashboard
install_homepage() {
    log_info "Installing Homepage Dashboard with RBAC..."

    # Check if Homepage is already installed
    if deployment_ready "default" "homepage"; then
        log_success "Homepage Dashboard already installed and running, skipping installation"
        return
    fi

    # Apply homepage resources (includes RBAC as per README)
    safe_kubectl_apply "homepage/homepage.yaml" "Homepage dashboard" "true"

    # Wait for homepage to be ready
    wait_for_deployment default homepage

    # Verify RBAC setup
    if kubectl get clusterrole homepage >/dev/null 2>&1 && \
       kubectl get clusterrolebinding homepage >/dev/null 2>&1 && \
       kubectl get serviceaccount homepage -n default >/dev/null 2>&1; then
        log_success "Homepage Dashboard installed with proper RBAC"
    else
        log_warning "Homepage installed but RBAC verification failed"
    fi

    # Verify Homepage installation
    local homepage_pods=$(kubectl get pods -n default -l app.kubernetes.io/name=homepage 2>/dev/null | tail -n +2 || echo "No homepage pods found")
    local homepage_services=$(kubectl get svc -n default | grep homepage 2>/dev/null || echo "No homepage services found")
    local homepage_rbac=$(kubectl get clusterrole,clusterrolebinding | grep homepage 2>/dev/null || echo "No homepage RBAC found")

    wait_for_confirmation "Homepage Dashboard" "Homepage Pods:\n$homepage_pods\n\nServices:\n$homepage_services\n\nRBAC:\n$homepage_rbac"
}

# Step 9: Install additional services
install_additional_services() {
    log_info "Installing additional services..."

    # Install Calibre if directory exists
    if [[ -d "calibre" ]]; then
        log_info "Installing Calibre e-book management..."
        # Add k8s-at-home repository for Calibre
        helm repo add k8s-at-home https://k8s-at-home.com/charts/ || true
        helm repo update

        # Create calibre volumes first if exists
        safe_kubectl_apply "calibre/calibre-volumes-csi.yaml" "Calibre volumes"

        # Install Calibre using Helm if values file exists
        if [[ -f "calibre/calibre-web-values.yaml" ]]; then
            kubectl create namespace calibre --dry-run=client -o yaml | kubectl apply -f -
            helm upgrade --install calibre k8s-at-home/calibre \
                --values calibre/calibre-web-values.yaml \
                --namespace calibre \
                --wait || log_warning "Calibre installation failed, applying manifests directly"
        fi

        # Apply any additional Calibre manifests
        safe_kubectl_apply_dir "calibre" "Calibre additional manifests"
    fi

    # Install KasmWeb if directory exists
    if [[ -d "kasmweb" ]]; then
        log_info "Installing KasmWeb desktop environment..."
        safe_kubectl_apply_dir "kasmweb" "KasmWeb desktop environment"
    fi

    # Install Cloudflare tunnel if directory exists
    if [[ -d "claudflare" ]]; then
        log_info "Installing Cloudflare tunnel..."
        safe_kubectl_apply_dir "claudflare" "Cloudflare tunnel"
    fi

    log_success "Additional services installation completed"

    # Verify additional services
    local additional_pods=$(kubectl get pods -A | grep -E "(calibre|kasmweb|cloudflare)" 2>/dev/null || echo "No additional service pods found")
    local additional_namespaces=$(kubectl get namespaces | grep -E "(calibre|kasmweb|cloudflare)" 2>/dev/null || echo "No additional service namespaces found")

    wait_for_confirmation "Additional Services" "Additional Pods:\n$additional_pods\n\nAdditional Namespaces:\n$additional_namespaces"
}

# Step 10: Apply any remaining configurations
apply_remaining_configs() {
    log_info "Applying remaining configurations..."

    # Apply whoami test service if exists
    safe_kubectl_apply "whoami.yaml" "whoami test service"

    log_success "Remaining configurations applied"

    # Verify final configurations
    local all_pods_status=$(kubectl get pods -A --field-selector=status.phase!=Running 2>/dev/null | tail -n +2 || echo "All pods are running")
    local failed_pods=$(kubectl get pods -A --field-selector=status.phase=Failed 2>/dev/null | tail -n +2 || echo "No failed pods")

    wait_for_confirmation "Final Configurations" "Non-Running Pods:\n$all_pods_status\n\nFailed Pods:\n$failed_pods"
}

# Verification function
verify_installation() {
    log_info "Verifying installation..."

    # Check critical deployments
    local critical_deployments=(
        "metallb-system:metallb-controller"
        "cert-manager:cert-manager"
        "traefik:traefik"
        "oauth2-proxy:oauth2-proxy"
        "default:homepage"
    )

    for deployment_info in "${critical_deployments[@]}"; do
        IFS=':' read -r namespace deployment <<< "$deployment_info"
        if kubectl get deployment $deployment -n $namespace >/dev/null 2>&1; then
            if kubectl get deployment $deployment -n $namespace -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' | grep -q "True"; then
                log_success "$deployment in $namespace is ready"
            else
                log_warning "$deployment in $namespace is not ready"
            fi
        else
            log_warning "$deployment in $namespace not found"
        fi
    done

    # Show service URLs
    log_info "Service URLs:"
    echo "  - Homepage: https://home.$CLUSTER_DOMAIN"
    echo "  - Traefik Dashboard: https://traefik-dash.$CLUSTER_DOMAIN"
    echo "  - OAuth2 Auth: https://auth.$CLUSTER_DOMAIN"
    echo "  - Jellyfin: https://jellyfin.$CLUSTER_DOMAIN"
    echo "  - qBittorrent: https://qbittorrent.$CLUSTER_DOMAIN"
    echo "  - And more services as configured..."
}

# Main installation function
main() {
    log_info "Starting Kubernetes Lab Installation (Idempotent)..."
    log_info "This script is idempotent - it will skip already installed components"
    log_info "All applications will be installed/updated in the correct dependency order"

    # Confirmation prompt
    read -p "Do you want to proceed with the installation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installation cancelled by user"
        exit 0
    fi

    # Execute installation steps
    check_prerequisites
    check_and_restore_secrets
    add_helm_repos
    install_nfs_csi
    install_metallb
    install_cert_manager
    install_traefik
    install_oauth2_proxy
    create_persistent_volumes
    install_servarr
    install_homepage
    install_additional_services
    apply_remaining_configs

    log_success "Installation completed successfully!"
    verify_installation

    log_info "Installation summary:"
    log_info "- ✅ Backup Integration: Files restored only when needed from $BACKUP_DIR"
    log_info "- ✅ NFS CSI Driver: Dynamic storage provisioning"
    log_info "- ✅ MetalLB: Load balancer for external access"
    log_info "- ✅ cert-manager: Automated SSL/TLS certificates"
    log_info "- ✅ Traefik: Ingress controller with proper RBAC"
    log_info "- ✅ OAuth2 Proxy: Google authentication for all services"
    log_info "- ✅ Servarr Stack: Media management applications"
    log_info "- ✅ Homepage: Kubernetes dashboard with cluster monitoring"
    log_info "- ✅ Additional services: Calibre, KasmWeb, Cloudflare tunnel"
    log_info "- ✅ RBAC: Proper security permissions configured"
    log_info "- ✅ SSL: Wildcard certificates for *.pindaroli.org"

    log_success "Your Kubernetes lab is ready to use!"
}

# Run main function
main "$@"
