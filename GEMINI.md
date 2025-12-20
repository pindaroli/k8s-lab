## Kubernetes Cluster Setup

- Management system: macOS
- Local domain: local
- External domain: pindaroli.org (Cloudflare managed)
- Network gateway: 10.10.20.1 (Client) / 192.168.2.1 (Mgmt)
- kubectl access available
- Gemini has automatic permission for readonly kubectl commands (get, describe, logs, etc.)
- GitHub CLI (gh) available for repository operations

## SSH Access

- jellyfin-svr


## Load Balancing & Ingress

### MetalLB
- Namespace: metallb
- Configuration files: ./metallb/ directory
- Helm chart: metallb/metallb
- IP pool: to be defined (L2Advertisement)

### Traefik
- Ingress controller with SSL/TLS termination
- Configuration files: ./traefik/ directory
- Main ingress routes: traefik/all-arr-ingress-routes.yaml
- RBAC configuration: traefik/traefik-rbac.yaml
- Custom values: traefik/traefik-values.yaml

## Certificate Management

- cert-manager for automated Let's Encrypt certificates
- Cloudflare DNS challenge provider
- Wildcard certificate: pindaroli-wildcard-tls
- Configuration files: ./cert-manager/ directory
- Cluster issuer and certificate definitions included

## Authentication & Security

### OAuth2 Proxy
- Namespace: oauth2-proxy
- Google OAuth provider integration
- Authorized email: o.pindaro@gmail.com
- Cookie domain: .pindaroli.org
- Authentication URL: https://auth.pindaroli.org
- Configuration files: ./oauth2-proxy/ directory
- All external services protected via oauth2-auth middleware

## Homepage Dashboard

- Namespace: default
- Access URL: https://home.pindaroli.org
- Consolidated deployment: homepage/homepage.yaml
- Services configured: Traefik, Jellyfin, qBittorrent, all *arr services
- Widgets: Kubernetes cluster info, resource monitoring, search
- Note: Kubernetes Dashboard completely uninstalled

## Media Stack (Servarr)

### Deployment
- Namespace: arr
- Helm chart: ../helm/charts/servarr (local development)
- Configuration files: ./servarr/ directory
- Values file: servarr/arr-values.yaml
- CSI volumes: servarr/arr-volumes-csi.yaml
- Upgrade command: `helm upgrade servarr ../helm/charts/servarr -n arr -f servarr/arr-values.yaml`

### Resource Limits
- Jellyfin: 2Gi request, 4Gi limit (prevents OOM kills on k8s-control node)

### Services & External Access
All services protected by OAuth2 authentication:
- jellyfin.pindaroli.org - Media server
- qbittorrent.pindaroli.org - Torrent client
- sonarr.pindaroli.org - TV series management
- radarr.pindaroli.org - Movie management
- lidarr.pindaroli.org - Music management
- readarr.pindaroli.org - Book management
- prowlarr.pindaroli.org - Indexer management
- bazarr.pindaroli.org - Subtitle management
- jellyseerr.pindaroli.org - Request management
- flaresolverr.pindaroli.org - CloudFlare solver

### Special Configurations
- qBittorrent BitTorrent port LoadBalancer: servarr/qbittorrent-bittorrent-loadbalancer.yaml
- Port forwarding documentation: servarr/opnsense-port-forward-config.md

## Additional Services

### Calibre
- E-book management system
- Configuration files: ./calibre/ directory
- CSI volumes: calibre/calibre-volumes-csi.yaml
- Ingress route: calibre/calibre-web-ingress-route.yaml

### Cloudflare Tunnel
- Zero Trust network access
- Configuration files: ./cloudflare/ directory
- Deployment: cloudflare/cloudflared-deployment.yaml

### KasmWeb
- Web-based desktop environment
- Configuration files: ./kasmweb/ directory

## Storage

### TrueNAS SCALE
- **IMPORTANT**: TrueNAS SCALE uses Debian Linux (NOT FreeBSD)
- NFS server: to be defined (Storage VLAN Access)
- SSH user: olindo (not root)
- NFS exports configured in /etc/exports
- Uses standard Linux NFS commands (exportfs, etc.)
- NFS shares:
  - /mnt/oliraid/arrdata/media - Media storage
  - /mnt/stripe/k8s-arr - Kubernetes configuration storage

### NFS CSI Driver
- NFS CSI driver for dynamic provisioning
- CSI configuration files in ./CSI-driver/ directory
- Persistent volumes backed by NFS storage from TrueNAS
- Volume definitions throughout service configurations

## Development Tools & Utilities

### Scripts
- megasetup.sh - Comprehensive cluster setup
- terminating-k8s-objects.sh - Cleanup utility
- uninstall-csi-nfs.sh - NFS CSI removal
- download_plugins.sh/py - Plugin management
- pul.sh - Quick operations

### Documentation
- cert.md - Certificate management guide
- troubleshooting.md - Common issues and solutions
- README files in individual service directories

## Personal Information

- Email: o.pindaro@gmail.com
- Domain: pindaroli.org (Cloudflare managed)
- Upgrade command: `helm upgrade servarr ../helm/charts/servarr -n arr -f servarr/arr-values.yaml`
# Configurazione rete fisica
- Configurazione dettagliata: [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json) 