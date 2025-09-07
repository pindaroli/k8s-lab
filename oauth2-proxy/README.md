# OAuth2-Proxy for Kubernetes

This directory contains the complete OAuth2-Proxy deployment for authenticating all services on `*.pindaroli.org` using Google OAuth2.

## Overview

OAuth2-Proxy provides Google OAuth2 authentication for all services in the Kubernetes cluster, integrated with Traefik as a ForwardAuth middleware. Only the user `o.pindaro@gmail.com` is allowed access.

## Architecture

```
User Request → Traefik → ForwardAuth (OAuth2-Proxy) → Service
                ↓ (if not authenticated)
              Google OAuth2 → Redirect back to original URL
```

## Quick Deployment

**Recommended approach** - Use the consolidated manifest:

```bash
# 1. Create secrets first (not in version control)
kubectl create secret generic oauth2-proxy \
  --from-literal=client-id="YOUR_GOOGLE_CLIENT_ID" \
  --from-literal=client-secret="YOUR_GOOGLE_CLIENT_SECRET" \
  --from-literal=cookie-secret="$(openssl rand -base64 32)" \
  -n oauth2-proxy

# 2. Deploy everything else
kubectl apply -f oauth2-proxy-complete.yaml
```

## Components in oauth2-proxy-complete.yaml

The consolidated manifest contains all resources except secrets:

### 1. Namespace
- Creates dedicated `oauth2-proxy` namespace

### 2. ConfigMap (allowed-emails)
- Email whitelist configuration
- Currently allows: `o.pindaro@gmail.com`

### 3. Deployment & Service
- OAuth2-Proxy v7.6.0 container
- Google provider configuration
- Cookie settings optimized for cross-browser compatibility
- ClusterIP service on port 4180
- Resource limits and health checks

### 4. IngressRoutes
- **HTTPS**: Exposes OAuth2-Proxy at `auth.pindaroli.org`
- **HTTP Redirect**: Automatic redirect to HTTPS
- Uses wildcard TLS certificate

### 5. Middlewares (Multi-namespace)
- **oauth2-proxy namespace**: Primary ForwardAuth middleware
- **default namespace**: For homepage and core services  
- **arr namespace**: For Servarr stack with error handling

## Alternative Deployment (Individual Files)

For advanced customization, individual manifests are available:

- `namespace.yaml` - Kubernetes namespace
- `secrets.yaml` - OAuth2 credentials ⚠️ **Contains sensitive data**
- `deployment.yaml` - OAuth2-Proxy deployment and service  
- `middleware.yaml` - ForwardAuth middleware (oauth2-proxy namespace)
- `middleware-default.yaml` - ForwardAuth middleware (other namespaces)
- `ingressroute.yaml` - External access routes

## Configuration Details

### OAuth2-Proxy Settings
- **Provider**: Google
- **Upstream**: Static response (202)
- **Cookie Domain**: `.pindaroli.org`
- **Cookie Security**: Secure, HttpOnly, SameSite=none
- **Reverse Proxy**: Enabled for proper header handling
- **Email Restriction**: Only `o.pindaro@gmail.com`

### Traefik Integration
- **ForwardAuth Address**: `http://oauth2-proxy:4180/`
- **Trust Forward Header**: Enabled
- **Auth Response Headers**: User, Email, Name, UID

## Legacy Deployment (Individual Files)

If using individual files instead of the consolidated manifest:

```bash
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml  # ⚠️ Contains sensitive OAuth2 credentials
kubectl apply -f deployment.yaml
kubectl apply -f middleware.yaml
kubectl apply -f middleware-default.yaml
kubectl apply -f ingressroute.yaml
```

## Usage in IngressRoutes

Add the OAuth2 middleware to any IngressRoute:

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: my-service
  namespace: my-namespace
spec:
  routes:
  - match: Host(`my-service.pindaroli.org`)
    kind: Rule
    services:
    - name: my-service
      port: 80
    middlewares:
    - name: oauth2-auth  # Use local namespace middleware
```

## Google Cloud Console Setup

1. Create OAuth2 credentials at [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Set authorized redirect URI: `https://auth.pindaroli.org/oauth2/callback`
3. Add authorized domain: `pindaroli.org`
4. Update `secrets.yaml` with client ID and secret

## Troubleshooting

### Check OAuth2-Proxy Status
```bash
kubectl get pods -n oauth2-proxy
kubectl logs -l app=oauth2-proxy -n oauth2-proxy
```

### Test Authentication
```bash
curl -I https://auth.pindaroli.org/oauth2/auth
```

### Browser Compatibility
- **Chrome/Firefox**: Works immediately
- **Safari**: May require initial authentication via `auth.pindaroli.org` first

### Common Issues

1. **401 Unauthorized**: Check that middleware uses endpoint `/` not `/oauth2/auth`
2. **Cookie Issues**: Verify `cookie-domain` is set to `.pindaroli.org`
3. **Redirect Loops**: Ensure `redirect-url` matches IngressRoute host

## Security Features

- ✅ Email restriction to single user
- ✅ Secure cookie settings
- ✅ HTTPS-only communication
- ✅ Cross-site request forgery protection
- ✅ Session timeout and refresh
- ✅ Integration with existing Cloudflare geoblocking

## Files Structure

```
oauth2-proxy/
├── README.md                    # This documentation
├── oauth2-proxy-complete.yaml   # 🌟 Consolidated deployment (recommended)
├── secrets.yaml                 # ⚠️ OAuth2 credentials (sensitive data)
├── namespace.yaml               # Individual: Kubernetes namespace
├── deployment.yaml              # Individual: OAuth2-Proxy deployment and service
├── middleware.yaml              # Individual: ForwardAuth middleware (oauth2-proxy ns)
├── middleware-default.yaml      # Individual: ForwardAuth middleware (other namespaces)
└── ingressroute.yaml           # Individual: External access route
```

**Recommended:** Use `oauth2-proxy-complete.yaml` for new deployments
**Legacy:** Individual files available for advanced customization

## Related Services

This OAuth2 setup protects:
- **Homepage**: `home.pindaroli.org`
- **Servarr Stack**: `jellyfin.pindaroli.org`, `sonarr.pindaroli.org`, etc.

All services automatically redirect unauthenticated users to Google OAuth2 login.