# Cloudflare Argo Tunnel with Traefik Integration - Complete Solution

## Overview

This solution demonstrates how to configure Cloudflare Argo Tunnel to forward all external traffic to a Kubernetes cluster's Traefik ingress controller using pure Kubernetes manifests.

## Architecture Diagram

```
Internet Traffic (*.pindaroli.org)
         ↓
Cloudflare Edge Network
         ↓
Cloudflare Argo Tunnel (cloudflared pods)
         ↓
Traefik LoadBalancer Service (192.168.1.3:80)
         ↓
Traefik Ingress Controller
         ↓
Application Services (Jellyfin, Sonarr, etc.)
```

## Problem Statement

**Challenge**: Route all external domain traffic (`*.pindaroli.org`) through Cloudflare's secure tunnel to reach internal Kubernetes services without exposing ports directly to the internet.

**Requirements**:
- All CNAME records should use Argo tunnel
- Forward all traffic to Traefik ingress controller
- Manage configuration entirely through Kubernetes manifests
- Support up to 10 concurrent users

## Solution Components

### 1. Configuration Strategy

Instead of using only a tunnel token, we use a **configuration file approach** that allows granular traffic routing rules.

**Key Concept**: Cloudflared can use a YAML configuration file that defines ingress rules - similar to how Traefik IngressRoutes work, but at the tunnel level.

### 2. Kubernetes Resources Required

#### A. ConfigMap for Tunnel Configuration
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cloudflared-config
data:
  config.yaml: |
    tunnel: YOUR_TUNNEL_ID
    credentials-file: /etc/cloudflared/creds/credentials.json
    
    ingress:
      # Route all *.pindaroli.org traffic to Traefik
      - hostname: "*.pindaroli.org"
        service: http://traefik.traefik.svc.cluster.local:80
      # Catch-all rule (required as last rule)
      - service: http_status:404
```

**Explanation**:
- `tunnel`: Your unique tunnel identifier from Cloudflare
- `credentials-file`: Path to the tunnel authentication credentials
- `ingress`: Rules defining where traffic should be routed
  - Wildcard hostname `*.pindaroli.org` catches all subdomains
  - Service URL points to Traefik's Kubernetes service
  - Catch-all rule returns 404 for unmatched requests

#### B. Secret for Tunnel Credentials
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: tunnel-credentials
type: Opaque
data:
  credentials.json: BASE64_ENCODED_CREDENTIALS
```

**Explanation**:
- Contains the tunnel authentication credentials downloaded from Cloudflare
- Must be base64 encoded for Kubernetes Secret storage
- Mounted as a file in the cloudflared container

#### C. Enhanced Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudflared-deployment
spec:
  replicas: 2  # High availability
  template:
    spec:
      containers:
        - name: cloudflared
          image: cloudflare/cloudflared:2025.8.0
          resources:
            requests:
              memory: "100Mi"
              cpu: "50m"
            limits:
              memory: "200Mi"
              cpu: "200m"
          command:
            - cloudflared
            - tunnel
            - --config
            - /etc/cloudflared/config/config.yaml  # Use config file
            - run
          volumeMounts:
            - name: config
              mountPath: /etc/cloudflared/config
            - name: creds
              mountPath: /etc/cloudflared/creds
      volumes:
        - name: config
          configMap:
            name: cloudflared-config
        - name: creds
          secret:
            secretName: tunnel-credentials
```

**Key Changes**:
- Removed `TUNNEL_TOKEN` environment variable
- Added `--config` flag pointing to mounted configuration file
- Added volume mounts for both config and credentials
- Resource limits sized for 10 concurrent users

## Implementation Steps

### Step 0: Setup Tunnel Token Secret

For the existing deployment that uses tunnel token, create the required Secret:

```bash
kubectl create secret generic tunnel-token \
  --from-literal=token="YOUR_TUNNEL_TOKEN_HERE" \
  --namespace=default
```

To get the tunnel token:

#### From Cloudflare Dashboard:
1. **Zero Trust > Networks > Tunnels**
2. Create new tunnel or use existing
3. Copy the token from the configuration

#### Using cloudflared CLI:
```bash
cloudflared tunnel login
cloudflared tunnel create k8s-tunnel
cloudflared tunnel token k8s-tunnel
```

### Step 1: Prepare Tunnel Credentials

All methods produce equivalent results - choose based on your preference and available tools.

#### Method 1: macOS Machine (Recommended)
```bash
# Install cloudflared if not already installed
brew install cloudflared

# Login to Cloudflare account
cloudflared tunnel login

# List existing tunnels to verify
cloudflared tunnel list

# Get credentials file for your tunnel
cloudflared tunnel token --cred-file /tmp/creds.json eb4581bd-3011-4f40-8956-29f1ba634f39

# Base64 encode the credentials
base64 -i /tmp/creds.json
```

#### Method 2: k8s-control Node
```bash
# SSH to control plane
ssh root@k8s-control

# Install cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Login to Cloudflare account
cloudflared tunnel login

# Get credentials file
cloudflared tunnel token --cred-file /tmp/creds.json eb4581bd-3011-4f40-8956-29f1ba634f39

# Base64 encode the credentials
base64 -w 0 /tmp/creds.json
```

#### Method 3: Cloudflare Dashboard Download
1. **Navigate to**: Zero Trust → Networks → Tunnels
2. **Click on your tunnel**: `eb4581bd-3011-4f40-8956-29f1ba634f39`
3. **Go to**: Configure tab
4. **Download**: credentials.json file
5. **Base64 encode locally**:
   ```bash
   base64 -i ~/Downloads/credentials.json
   ```

#### What You Get
All methods produce a base64 string like:
```
eyJBY2NvdW50VGFnIjoiYWJjZGVmZ2hpamtsbW5vcCIsIlR1bm5lbFNlY3JldCI6Ii4uLiJ9Cg==
```

**Security Note**: Keep credentials secure - they authenticate your tunnel to Cloudflare.

### Step 2: Update Configuration

1. Edit `cloudflared-config.yaml`:
   - Replace `YOUR_TUNNEL_ID` with your actual tunnel ID
   - Replace `YOUR_BASE64_ENCODED_CREDENTIALS_JSON` with the encoded credentials

### Step 3: Deploy the Solution

1. **Apply new configuration**:
   ```bash
   kubectl apply -f cloudflared-config.yaml
   ```

2. **Remove old deployment** (if exists):
   ```bash
   kubectl delete -f claudeFlare-deployment.yaml
   ```

3. **Verify deployment**:
   ```bash
   kubectl get pods -l pod=cloudflared
   kubectl logs -l pod=cloudflared
   ```

### Step 4: Configure Cloudflare DNS

For each service subdomain, create CNAME records in Cloudflare:

```
jellyfin     CNAME   YOUR_TUNNEL_ID.cfargotunnel.com
sonarr       CNAME   YOUR_TUNNEL_ID.cfargotunnel.com
radarr       CNAME   YOUR_TUNNEL_ID.cfargotunnel.com
qbittorrent  CNAME   YOUR_TUNNEL_ID.cfargotunnel.com
# ... etc
```

## Traffic Flow Explanation

### 1. DNS Resolution
- User requests `jellyfin.pindaroli.org`
- DNS resolves to `YOUR_TUNNEL_ID.cfargotunnel.com`
- Cloudflare edge servers receive the request

### 2. Tunnel Routing
- Cloudflare routes traffic through the secure tunnel to your cloudflared pods
- Cloudflared checks its ingress rules
- Wildcard rule `*.pindaroli.org` matches the request
- Traffic is forwarded to `http://traefik.traefik.svc.cluster.local:80`

### 3. Traefik Processing
- Traefik receives the request with original hostname (`jellyfin.pindaroli.org`)
- Traefik matches the hostname against existing IngressRoutes
- Request is forwarded to the appropriate service (e.g., Jellyfin)

### 4. Response Path
- Application response travels back through the same path
- Traefik → Cloudflared → Cloudflare Edge → User

## Benefits of This Approach

### Security
- **No port exposure**: No need to open ports 80/443 on your router
- **DDoS protection**: Cloudflare handles malicious traffic
- **SSL termination**: Cloudflare manages certificates automatically

### Scalability
- **Multiple replicas**: 2 cloudflared pods for high availability
- **Resource limits**: Prevents resource exhaustion
- **Kubernetes native**: Integrates with existing cluster infrastructure

### Maintainability
- **GitOps ready**: All configuration in version-controlled YAML
- **No manual tunnel configuration**: Everything defined in Kubernetes
- **Consistent with existing setup**: Uses same Traefik IngressRoutes

## Troubleshooting

### Check Tunnel Status
```bash
kubectl logs -l pod=cloudflared
```

### Verify Traefik Service
```bash
kubectl get svc traefik -n traefik
```

### Test Internal Connectivity
```bash
kubectl run test-pod --image=curlimages/curl --rm -it -- curl http://traefik.traefik.svc.cluster.local:80
```

### Monitor Tunnel Metrics
```bash
kubectl port-forward deployment/cloudflared-deployment 2000:2000
curl http://localhost:2000/metrics
```

## Documentation References

### Cloudflare Tunnel Configuration
- **Official config.yaml syntax**: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/local-management/configuration-file/
- **Complete parameter reference**: Run `cloudflared tunnel help`
- **Tunnel run parameters**: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/configure-tunnels/cloudflared-parameters/run-parameters/

### Service DNS Breakdown
The `traefik.traefik.svc.cluster.local:80` service URL structure:
- **traefik** - service name
- **traefik** - namespace where Traefik is deployed  
- **svc.cluster.local** - Kubernetes DNS suffix for services
- **:80** - HTTP port (before TLS termination)

This points to your Traefik ingress controller service running in the `traefik` namespace. Traffic flow: Internet → Cloudflare → Tunnel → Traefik Service → Application Pods

### File System Management
The `/etc/cloudflared/config` directory is automatically created by Kubernetes when mounting the ConfigMap volume. No manual directory creation required:

1. Kubernetes creates ConfigMap `cloudflared-config` containing `config.yaml`
2. Pod deployment mounts ConfigMap as volume at `/etc/cloudflared/config`  
3. File appears at `/etc/cloudflared/config/config.yaml` inside container
4. Cloudflared reads configuration from mounted file path

## Conclusion

This solution provides a robust, scalable, and secure way to route all external traffic through Cloudflare Argo Tunnel to your Kubernetes cluster's Traefik ingress controller. The configuration is entirely managed through Kubernetes manifests, making it suitable for GitOps workflows and easy to maintain.

The wildcard routing approach eliminates the need to configure individual tunnel routes for each service, while still allowing Traefik to handle the granular routing based on hostnames.