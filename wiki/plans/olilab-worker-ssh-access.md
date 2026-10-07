---
title: "Accesso SSH Diretto a olilab-worker"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-10-07
archived_at: 2026-10-07
tags:
  - "#ssh"
  - "#proxmox"
  - "#opnsense"
  - "#cloudflare"
---
# Piano: Accesso SSH Diretto a olilab-worker.pindaroli.org (COMPLETATO)

## Obiettivo
Configurare l'infrastruttura per permettere l'accesso SSH puro e nativo (chiave pubblica, zero 2FA) al dominio `olilab-worker.pindaroli.org`, instradando il traffico verso una nuova VM Ubuntu Server ospitata sul nodo Proxmox più scarico (`pve2`).

---

## Architettura Finale Realizzata

1. **Host di Virtualizzazione & VM (PVE2)**:
   * **Node**: `pve2` (Proxmox VE 9.2).
   * **VM ID**: `2400` (`olilab-worker`).
   * **OS**: Ubuntu 24.04 LTS (Noble Numbat via Cloud-Init).
   * **Rete**: VLAN 20 (`vmbr20`), IP statico `10.10.20.70/24`, gateway `10.10.20.1` (Switch L3 Extreme SVI), MAC `bc:24:11:cd:3f:c0`.
   * **Hardening SSH**: Iniezione della chiave pubblica `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHfqmzsseaahUk4JlArzctgrXR7+Zt3cpJpOLQfA+PUA olindo@macbook`. `PasswordAuthentication no`, `PubkeyAuthentication yes`.

2. **DNS & Dynamic DNS (Cloudflare + OPNsense)**:
   * **Record CNAME**: `olilab-worker.pindaroli.org` ➔ `pindaroli.org` (DNS-Only / Nuvola Grigia).
   * **Risoluzione DDNS**: Ripristinato il servizio `os-ddclient` su OPNsense tramite roll del Cloudflare API Token (`Edit zone DNS`), aggiornando automaticamente `pindaroli.org` all'IP pubblico WAN corrente (`151.59.37.181`).

3. **Cloudflare Tunnel K8s Core Health**:
   * Aggiornato il deployment `cloudflared-deployment` nel cluster Kubernetes Talos da `2025.8.0` a `cloudflare/cloudflared:2026.10.0`.
   * Stato tunnel `olilab-tunnel` su Cloudflare Zero Trust: **Healthy (2/2 repliche connesse)**.

4. **Firewall & Routing Simmetrico (OPNsense)**:
   * **Destination NAT**: Inoltro porta WAN verso `10.10.20.70` porta 22 (SSH).
   * **Outbound NAT (SNAT)**: Configurato Source NAT sull'interfaccia di transito verso `10.10.20.70` per forzare la simmetria del flusso ed eliminare le cadute di stato TCP (`kex_exchange_identification`) causate dal downstream L3 switch.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano concluso e archiviato.
- **Ultima Azione Completata**: Test connettività e allineamento documentazione/rete.
- **Prossimo Passo Operativo**: Nessuno (workload operativo).
- **Blocchi/Decisioni Pendenti**: Nessuno.
