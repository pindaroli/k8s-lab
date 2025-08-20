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

## Components

### 1. Namespace (`namespace.yaml`)
- Creates dedicated `oauth2-proxy` namespace

### 2. Secrets (`secrets.yaml`)
- `client-id`: Google OAuth2 Client ID (base64 encoded)
- `client-secret`: Google OAuth2 Client Secret (base64 encoded)
- `cookie-secret`: Random secret for cookie encryption (base64 encoded)
- `allowed-emails`: ConfigMap with allowed email addresses

### 3. Deployment (`deployment.yaml`)
- OAuth2-Proxy v7.6.0 container
- Google provider configuration
- Cookie settings optimized for cross-browser compatibility
- Email restriction to `o.pindaro@gmail.com`

### 4. Middleware (`middleware.yaml`, `middleware-default.yaml`)
- Traefik ForwardAuth middleware in each namespace
- Points to OAuth2-Proxy service endpoint `/` (not `/oauth2/auth`)
- Cross-namespace middleware definitions for `default`, `arr`, and `wetty`

### 5. IngressRoute (`ingressroute.yaml`)
- Exposes OAuth2-Proxy at `auth.pindaroli.org`
- HTTPS with wildcard certificate
- HTTP to HTTPS redirect

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

## Deployment

Deploy in order:

```bash
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml
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
├── README.md                 # This documentation
├── namespace.yaml           # Kubernetes namespace
├── secrets.yaml             # OAuth2 credentials and config
├── deployment.yaml          # OAuth2-Proxy deployment and service
├── middleware.yaml          # ForwardAuth middleware (oauth2-proxy ns)
├── middleware-default.yaml  # ForwardAuth middleware (other namespaces)
└── ingressroute.yaml       # External access route
```

## Related Services

This OAuth2 setup protects:
- **Homepage**: `home.pindaroli.org`
- **Servarr Stack**: `jellyfin.pindaroli.org`, `sonarr.pindaroli.org`, etc.
- **Wetty Terminals**: `k8s-control.pindaroli.org`, `truenas.pindaroli.org`, etc.

All services automatically redirect unauthenticated users to Google OAuth2 login.