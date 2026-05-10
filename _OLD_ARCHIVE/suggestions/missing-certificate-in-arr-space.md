# Missing Certificate in arr Namespace

## Problem
Chrome returned `ERR_ADDRESS_UNREACHABLE` when accessing `https://jellyfin.pindaroli.org`.

## Root Cause Analysis
1. **Jellyfin IngressRoute Configuration**: ✅ Properly configured in `arr` namespace
   - IngressRoute: `jellyfin-external`
   - Host: `jellyfin.pindaroli.org`
   - Service: `servarr-jellyfin:8096`
   - TLS secret reference: `pindaroli-wildcard-tls`

2. **Traefik Status**: ✅ Running normally
   - Pod: `traefik-6ccf7b649d-kq6cz` in `traefik` namespace
   - LoadBalancer service: `192.168.1.3:80,443`
   - Access logs showing successful requests to Jellyfin

3. **DNS Resolution**: ✅ Working correctly
   - `jellyfin.pindaroli.org` → `192.168.1.3` (MetalLB IP)

4. **Certificate Issue**: ❌ **Root Cause Found**
   - Traefik logs showed: `"secret arr/pindaroli-wildcard-tls does not exist"`
   - Certificate existed in `traefik` namespace but not in `arr` namespace
   - IngressRoutes in `arr` namespace couldn't access the certificate

## Solution
Copied the TLS certificate from `traefik` namespace to `arr` namespace:

```bash
kubectl get secret pindaroli-wildcard-tls -n traefik -o yaml | sed 's/namespace: traefik/namespace: arr/' | kubectl apply -f -
```

## Verification
- Certificate now exists in both namespaces
- Traefik errors should stop appearing in logs
- HTTPS access to `jellyfin.pindaroli.org` should work

## Prevention
Consider one of these approaches for future deployments:
1. **Cross-namespace certificate references** (if supported by your setup)
2. **Automated certificate replication** using tools like Reflector
3. **Centralized certificate management** in a dedicated namespace with RBAC
