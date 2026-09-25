---
title: "TrueNAS e Docker sulla VLAN 20"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-09-25
completed_at: 2026-09-25
tags:
  - "#plan"
  - "#network"
  - "#extreme"
  - "#truenas"
---

# TrueNAS e Docker sulla VLAN 20, PBS sulla VLAN 10

> [!NOTE]
> **Eseguito il 2026-09-25.** `bond0` ha solo `10.10.20.50/24`, default `10.10.20.1`. `vlan10` è su `bond0`, tag 10, senza IPv4. Il LAG (porte 4 e 8) è untagged in `client` e tagged in `server`, LACP Collecting/Distributing. PBS è su `vlan10` e risponde su `10.10.10.100`. I consumatori vivi puntano a `10.10.20.50`.

TrueNAS e lo stack Docker passano sulla VLAN 20 con un solo indirizzo, `10.10.20.50/24`, gateway `10.10.20.1`. Il LAG LACP (master porta 4, membro porta 8) diventa trunk: VLAN `client` (20) untagged su `bond0`, VLAN `server` (10) taggata solo per la VM PBS. PBS resta `10.10.10.100/24`, gateway `10.10.10.1`.

L'interfaccia `vlan10` non ha un indirizzo. TrueNAS ha una sola rotta connessa, `10.10.20.0/24`. Il ritorno verso i Proxmox passa dalla SVI ed è simmetrico. Il dual-homing di [[dual-homing-vlan10-vlan20]] resta scartato.

Il taglio si fa dall'OOB `192.168.100.50`. Lo switch si modifica solo con `ansible/playbooks/exos_truenas_lacp_vlan20.yml`.

## Stato di partenza

- `bond0` LACP 802.3ad, hash L3+L4, `10.10.10.50/24`, default `10.10.10.1`. Membri `enp1s0f0np0` e `enp1s0f1np1`.
- LAG Extreme access untagged VLAN `server`. Porta 4 master, porta 8 membro, entrambi Collecting/Distributing.
- VM `pbs` accesa, NIC VirtIO su `bond0`, guest `10.10.10.100/24`.
- Docker in ascolto su `0.0.0.0`. MinimServer e Samba legati a `10.10.10.50`.
- `10.10.20.50` libero. Pool DHCP VLAN 20 da `.201`.

## Taglio

1. `vlan10` parent `bond0`, tag 10, nessun alias. Commit e checkin.
2. Arresto VM `pbs`. `nic_attach` da `bond0` a `vlan10`. Il MAC resta `00:a0:98:5c:29:ef`.
3. Playbook: porta 4 untagged in `client`, poi tagged in `server`, `save configuration primary`.
4. Alias `10.10.20.50/24` su `bond0`, gateway `10.10.20.1`, rimosso `10.10.10.50`. `vlan10` senza IPv4. Commit e checkin da OOB.
5. Riavvio MinimServer e Samba.
6. Avvio PBS. Il guest non cambia indirizzo.

## Collaudo

- Dal Mac, un hop verso `10.10.20.50`. UI, Jellyfin `:8096`, qBittorrent `:8080`.
- Da un Proxmox, `10.10.10.100` sullo stesso segmento. Verso `10.10.20.50` il primo hop è `10.10.10.1`.
- Su TrueNAS, `bond0` ha solo `10.10.20.50`. `vlan10` non ha un inet.
- NFS da un nodo Talos verso `10.10.20.50`. Gli export non cambiano.

## Consumatori

`10.10.10.50` diventa `10.10.20.50` nella configurazione viva: `rete.json`, inventory, NFS e Endpoints del repository, i PV e gli Endpoints già applicati, NUT sui tre Proxmox, la DNAT di qBittorrent, Unbound, `TRUENAS_SERVER_URL`. PBS in `rete.json` resta `10.10.10.100` sulla VLAN 10. I piani archiviati non si riscrivono.

## Rollback

Da OOB, prima di aggiornare i consumatori: `10.10.10.50/24` e gateway `10.10.10.1` su `bond0`, NIC di PBS di nuovo su `bond0`, rollback dello switch (commentato nel playbook), PBS avviato.
