# Ansible Playbooks

This directory contains the core automation playbooks for the Kubernetes Homelab.

## Core Playbooks (Keep)

| Playbook | Description |
|---|---|
| **`opnsense_sync_dns.yml`** | **CRITICAL**. Syncs the `rete.json` network source of truth to OPNsense Unbound DNS. Uses `scripts/validate_rete_dns.py` to generate the authoritative record list. |
| **`cloudflare_sync.yml`** | **CRITICAL**. Syncs external DNS records from `rete.json` aliases to Cloudflare. Implements an **Explicit Mapping** strategy to avoid wildcard pollution. |
| **`dhcp_reservations.yml`** | **CRITICAL**. Manages DHCP static mappings for infrastructure nodes (Talos CP, etc.) on OPNsense. |
| **`cleanup_old_services.yml`** | **Maintenance**. Reusable logic to decommission old services from DNS (both Cloudflare and OPNsense). |
| **`restart_unbound.yml`** | **Utility**. Simple handler to restart the Unbound DNS service on OPNsense. |

## DNS Synchronization Logic

### `cloudflare_sync.yml` (External)
This playbook implements a **"Split-Horizon/Blackhole"** strategy for external DNS:
1. **Public Services**: For every alias in `rete.json` (e.g., `radarr`), it creates a CNAME pointing to the root domain (`pindaroli.org`). This allows Cloudflare Tunnel to route the traffic.
2. **Internal Privacy**: Internal services (`-internal`) are **NOT** created on Cloudflare. They are managed exclusively by the internal OPNsense/Unbound DNS to prevent external leakage and browser caching issues.
   - *Why*: This explicitly overrides the wildcard `*` at the DNS provider level, ensuring that internal-only services are **never** resolvable from the public internet, even by accident.
3. **Prerequisites**: Requires `cloudflare_email` and `cloudflare_api_key` (sourced from `ansible/vars/secrets.yml`).

### `opnsense_sync_dns.yml` (Internal)
The source of truth remains `rete.json`. The playbook uses a Python generator to ensure that:
- All `id` and `aliases` become local A records.
- Records are cleaned up (pruned) if they no longer exist in the JSON.
- **Goal**: Transitioning away from internal wildcards to prevent "Black Hole Routing" issues inside Kubernetes (ndots search path interference).

## Archived
Debugging playbooks from specific troubleshooting sessions are moved to `_OLD_ARCHIVE/`.
