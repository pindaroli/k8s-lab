---
title: "TrueNAS (Storage & Management)"
last_updated: "2026-05-11"
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
- **IP Gestione**: `10.10.10.50`
- **OS**: TrueNAS SCALE (Debian-based).

## 2. Pool e Dataset
- **oliraid**: Pool principale per media e dati bulk.
  - Path Media: `/mnt/oliraid/arrdata/media`
- **stripe**: Pool ad alte prestazioni (NVMe) utilizzato per cache, database e storage temporaneo.
  - Path Cache: `/mnt/stripe/k8s-arr`
  - Path qB Temp: `/mnt/stripe/qb_temp` (Ottimizzato: Recordsize 16k, Sync: Disabled).

## 3. Servizi e Condivisioni
- **NFS**: Utilizzato per montare lo storage sul [[Talos_Cluster]] e sui nodi esterni come il Mac Studio.
- **SMB**: Utilizzato per l'accesso amministrativo da Windows/macOS.
- **S3 (MinIO)**: Utilizzato per i backup offsite.

## 4. Integrazione Kubernetes
Lo storage è collegato al cluster tramite il driver NFS CSI. I pod richiedono spazio tramite Persistent Volume Claims (PVC).

## Relazioni
- Fornitore di storage per: [[Talos_Cluster]] e [[Tdarr]].
- Backup gestiti tramite: Velero e PBS.

## Note Operative: Vdev `special` di `oliraid`
- **Configurazione attuale**: `special_small_blocks=64K` — ridotta da 1M a 64K per prevenire la saturazione futura.
- **Azione in corso**: [[oliraid-expansion-special-vdev-evacuation]] — espansione geometrica del pool a 5 dischi ed evacuazione attiva dello Special VDEV tramite riscrittura globale di `arrdata`.
- **Struttura vdev special**: mirror SSD da 888 GiB (`/dev/sdf` Intel D3-S4510 960GB + `/dev/sdh` Crucial MX500 2TB con partizione da 892 GiB).
