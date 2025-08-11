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

## Personal Information

- my email is o.pindaro@gmail.com