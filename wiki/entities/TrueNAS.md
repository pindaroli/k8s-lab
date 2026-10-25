---
title: "TrueNAS (Storage & Management)"
last_updated: "2026-10-13"
confidence: "High"
tags:
  - "#storage"
  - "#nas"
  - "#truenas"
provenance:
  - "rete.json"
---

# TrueNAS SCALE (Storage Engine)

TrueNAS è il fornitore centrale di storage per l'intera infrastruttura Lab.

## 1. Dettagli Hardware e Rete
- **Hostname**: `truenas.pindaroli.org`
- **Hardware**: Bare Metal dedicato (AMD Ryzen 5 PRO 5650G, ASRock X570M Pro4, 48GB ECC [2x16GB + 2x8GB DDR4 @ 2400 MT/s], Intel X710 Quad 10G).
- **IP Gestione**: `10.10.20.50/24` su `bond0` (LACP 802.3ad, hash L3+L4, rate slow), gateway `10.10.20.1`. Membri `enp1s0f0np0` e `enp1s0f1np1`. Sullo switch Extreme il LAG ha master la porta 4 e membro la porta 8: VLAN client untagged, VLAN server taggata. L'host non ha un indirizzo sulla VLAN 10. La VM PBS è attaccata a `vlan10` (tag 10, senza IP sull'host) e resta `10.10.10.100`.
- **IP OOB**: `192.168.100.50` (VLAN 99 OOB 2.5G, `enp8s0`)
- **OS**: TrueNAS SCALE 25.10.6 (Debian-based).
- **RAM & Gestione Memoria (ZFS ARC Tuning)**: Host dotato di 48 GB di RAM (senza swap). Per prevenire la saturazione della memoria da parte dell'ARC e proteggere i 17 container Docker e la VM PBS dall'OOM killer, il parametro `zfs_arc_max` è configurato in modo permanente tramite tunable TrueNAS (`midclt call tunable.create`) a **28 GiB** (`30064771072` bytes). Questo garantisce permanentemente 20 GB di RAM libera per Docker, PBS e processi host, eliminando l'allarme di low memory in [[Hermes_Agent]] (Rif: [[2026-10-25-truenas-zfs-arc-memory-starvation-hermes-warning]]).
- **UPS**: Master NUT. Il cavo USB dell'UPS Tecnoware Exa 1000 è attestato fisicamente su TrueNAS (Vendor ID `0665:5161`). Driver `nutdrv_qx`, soglia software 40% (`ignorelb`), `HOSTSYNC: 120`.

## 2. Pool e Dataset
- **oliraid**: Pool principale RAID-Z2 (5 HDD da 14-16TB) + Special VDEV Mirror (2 SSD da 960GB/2TB) per metadati/small blocks.
  - Path Media: `/mnt/oliraid/arrdata/media`
  - Path Classical: `/mnt/oliraid/arrdata/classical`
  - Path PBS Store: `/mnt/oliraid/pbs-store`
  - Path Time Machine: `/mnt/oliraid/Time-Machine`
- **stripe**: Pool ad alte prestazioni (NVMe) utilizzato per cache, database e storage temporaneo.
  - Path Cache: `/mnt/stripe/k8s-arr`
  - Path qB Temp: `/mnt/stripe/qb_temp` (Ottimizzato: Recordsize 16k, Sync: Disabled).

## 3. Servizi e Condivisioni
- **NFS**: Utilizzato per montare lo storage sul [[Talos_Cluster]] e sui nodi esterni come il Mac Studio.
- **SMB**: Utilizzato per l'accesso amministrativo da Windows/macOS.
- **S3 Object Storage (Garage)**: Container `garage` v2.3.0 in `docker-compose.yaml` (dataset `/mnt/oliraid/garage-data`), porte 3900 (S3 API), 3901 (RPC su VLAN 20), 3902 (Web), 3903 (Admin). Buckets: `postgres-wal`, `velero`, `ragflow-docs`.
- **Monitoraggio Dischi (Scrutiny)**: Container `scrutiny` v0.9.5-omnibus in `docker-compose.yaml` (dataset `/mnt/stripe/truenas-docker/scrutiny`), porte 31054 (WebUI/API) e 31055 (InfluxDB). Monitora tutti i dischi SATA e NVMe.
- **Docker Compose Stack (`/mnt/stripe/truenas-docker`)**: Stack Docker permanente unificato per tutti i container host (Media/Failover, Hermes/LiteLLM, Dozzle, Garage, Scrutiny, Homepage). Tutte le app del catalogo nativo TrueNAS (`ix-apps`) sono state completamente migrate e decommissionate.
- **NUT Server (UPS)**: Servizio UPS attivo in modalità Master (`10.10.20.50:3493`) per telemetria e broadcast di shutdown coordinato verso i nodi Proxmox. Monitoraggio sessioni TCP client con `HOSTSYNC 120` e soglia di sicurezza software al 40% di carica residua.

## 4. Integrazione Kubernetes
Lo storage è collegato al cluster tramite il driver NFS CSI. I pod richiedono spazio tramite Persistent Volume Claims (PVC).

## Relazioni
- Fornitore di storage per: [[Talos_Cluster]] e [[Tdarr]].
- Backup gestiti tramite: Velero e PBS.
- Master NUT per: [[NUT_UPS]], PVE1, PVE2, PVE3.

## Note Operative: Vdev `special` di `oliraid`
- **Configurazione attuale**: `special_small_blocks=64K` — ridotta da 1M a 64K per prevenire la saturazione futura.
- **Azione in corso**: [[oliraid-expansion-special-vdev-evacuation]] — espansione geometrica del pool a 5 dischi ed evacuazione attiva dello Special VDEV tramite riscrittura globale di `arrdata`.
- **Struttura vdev special**: mirror SSD da 888 GiB (`/dev/sdf` Intel D3-S4510 960GB + `/dev/sdh` Crucial MX500 2TB con partizione da 892 GiB).
