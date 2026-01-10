# Kubernetes Homelab (Pindaroli Lab)

Infrastructure as Code repository for the Talos Linux Kubernetes cluster.

## Access Strategy Policy

### 1. External Access (Internet)
*   **Pattern**: `https://<service>.pindaroli.org`
*   **Path**: Cloudflare -> Tunnel -> Traefik.
*   **Auth**: **Mandatory OAuth2** (Google).
*   **Usage**: Secure remote access.

### 2. Internal Access (LAN)
*   **Pattern**: `https://<service>-internal.pindaroli.org`
*   **Path**: Local DNS (OPNsense) -> Traefik VIP.
*   **Auth**: **None** (Trusted Network) or Basic Auth.
*   **Usage**: Low-friction local access.

### 3. Quick Links (Shortnames)
*   **Pattern**: `https://home`, `https://nas`, `https://pve`.
*   **Path**: Local DNS mapping to Internal VIP.
*   **Requirement**: Service must accept the short host header (e.g., `HOMEPAGE_ALLOWED_HOSTS`).
