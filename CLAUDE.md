## Kubernetes Cluster Setup

- I use microk8s to implement my 2 node cluster
- my control-plane is k8s-control
- k8s-control is a proxmox vm with id 1500
- my runner is k8s-runner-1
- prompt running system is macOs
- jellyfin-ingressroute.yaml is the traefik ingressRoute for jellyfin
- in my subnet local domain is "local"
- my external internet domain provided by cloudflare provider is "pindaroli.org"
- gh is installed and you cas use it if needed
- servar helmcart code is in ../helm/servarr us for analysis
- for helm installation of servarr use kubitodev/servarr repository
- router address proxmox.local
- net gateway 192.168.1.1
- MetalLB is configured in metallb namespace for LoadBalancer services
- MetalLB configuration files are in ./metallb/ directory
- MetalLB uses Helm chart: metallb/metallb installed in metallb namespace
- MetalLB IP pool configured for 192.168.1.3-192.168.1.13 range with L2Advertisement
- to access cluster can use kubectl
- Claude has automatic permission to run readonly kubectl commands (get, describe, logs, etc.) without asking

## SSH Access

- To ssh access k8s-control use root@k8s-control

## Homepage Dashboard

- Homepage deployed in default namespace with complete Kubernetes manifests
- Access URL: https://home.pindaroli.org
- Consolidated deployment file: homepage/homepage.yaml contains all resources
- Services configured: Traefik, Jellyfin, qBittorrent, and all *arr services
- Widgets enabled: Kubernetes cluster info, resource monitoring, search functionality
- Note: Kubernetes Dashboard has been completely uninstalled

## Servarr Services

- All servarr services deployed in arr namespace via Helm (kubitodev/servarr)
- External access configured via Traefik IngressRoutes in all-arr-ingress-routes.yaml
- Services with external URLs:
  - jellyfin.pindaroli.org (media server)
  - qbittorrent.pindaroli.org (torrent client)
  - sonarr.pindaroli.org (TV series management)
  - radarr.pindaroli.org (movie management)
  - lidarr.pindaroli.org (music management)
  - readarr.pindaroli.org (book management)
  - prowlarr.pindaroli.org (indexer management)
  - bazarr.pindaroli.org (subtitle management)
  - jellyseerr.pindaroli.org (request management)
  - flaresolverr.pindaroli.org (CloudFlare solver)

## Personal Information

- my email is o.pindaro@gmail.com