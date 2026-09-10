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
| **`setup_ups.yml`** | **Infrastructure**. Configures NUT on TrueNAS (Master, cavo USB collegato fisicamente, HOSTSYNC 120, soglia software 40%) and Proxmox Cluster PVE1, PVE2, PVE3 (Client/Slave paralleli) for graceful and deterministic lab shutdown. |
| **`proxmox_smart_audit.yml`** | **Hardware/Storage Audit**. Rileva i nodi del cluster Proxmox (con warning su nodi non censiti), esegue `smartctl -a` sui soli dischi fisici reali e genera report ed executive summary tabellare. |

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

### `setup_ups.yml` (UPS & NUT Distributed Orchestration)
Questo playbook configura ed allinea i servizi NUT su TrueNAS SCALE (Server/Master con cavo USB attestato fisicamente, `HOSTSYNC: 120`, soglia cautelativa software al 40%) e su tutti i nodi Proxmox PVE1, PVE2, PVE3 (Client/Slave in parallelo).

**Caratteristiche Principali:**
1. **Master TrueNAS**: Abilita `nutdrv_qx` con `ignorelb` e `override.battery.charge.low = 40` (evitando il collasso della soglia hardware a 10.40V) e `hostsync: 120`. Monitora la caduta delle sessioni TCP client per spegnersi in anticipo.
2. **Bonifica PVE1**: Disabilita e purga i demoni `nut-server` e `nut-driver` residui su PVE1, rimuovendo la vecchia regola udev non pertinente.
3. **Script Parallelo Deterministico**: Distribuisce `/etc/nut/shutdown_sequence.sh` su PVE1, PVE2 e PVE3 con ciclo attivo di polling `qm status` (timeout max 45s) che evita attese cieche.

**Quando è necessario eseguirlo:**
1. **Configurazione iniziale / Cambiamento hardware**: In caso di sostituzione o modifica dell'UPS (es. se cambiano VendorID o ProductID, o per testare nuovi parametri del driver su TrueNAS).
2. **Reinstallazione o Reset di TrueNAS SCALE**: Per riapplicare e forzare tramite API i parametri energetici e la modalità Master con broadcast di telemetria.
3. **Reinstallazione o Upgrade Major di Proxmox (PVE1, PVE2, PVE3)**: In caso di installazione pulita dell'OS su un nodo Proxmox, le configurazioni locali di NUT client (`upsmon`) e lo script `/etc/nut/shutdown_sequence.sh` vengono ripristinati istantaneamente.
4. **Modifiche alla Sequenza di Spegnimento**: Qualora cambiassero i VMID o l'ordine di shutdown del cluster.

**Esecuzione:**
```bash
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/setup_ups.yml --vault-password-file .ansible/vault_pass.txt
```

## Archived
Debugging playbooks from specific troubleshooting sessions are moved to `_OLD_ARCHIVE/`.
