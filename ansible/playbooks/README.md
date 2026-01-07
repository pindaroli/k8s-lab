# Ansible Playbooks

This directory contains the core automation playbooks for the Kubernetes Homelab.

## Core Playbooks (Keep)

| Playbook | Description |
|---|---|
| **`opnsense_sync_dns.yml`** | **CRITICAL**. Syncs the `rete.json` network source of truth to OPNsense Unbound DNS. Uses `scripts/validate_rete_dns.py` to generate the authoritative record list. |
| **`cloudflare_sync.yml`** | **CRITICAL**. Syncs external DNS records (like VIPs) to Cloudflare. |
| **`dhcp_reservations.yml`** | **CRITICAL**. Manages DHCP static mappings for infrastructure nodes (Talos CP, etc.) on OPNsense. |
| **`cleanup_old_services.yml`** | **Maintenance**. Reusable logic to decommission old services from DNS (both Cloudflare and OPNsense). |
| **`restart_unbound.yml`** | **Utility**. Simple handler to restart the Unbound DNS service on OPNsense. |

## Archived
Debugging playbooks from specific troubleshooting sessions are moved to `_OLD_ARCHIVE/`.
