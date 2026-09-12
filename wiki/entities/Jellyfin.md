---
title: "Jellyfin Media Server"
last_updated: "2026-09-12"
confidence: "High"
tags:
  - "#jellyfin"
  - "#media"
  - "#gpu"
  - "#rdna35"
  - "#proxmox"
  - "#nfs"
provenance:
  - "wiki/plans/jellyfin-12-clean-slate-rdna35.md"
---

# Jellyfin Media Server

Jellyfin è la piattaforma di media streaming centrale dell'homelab. A partire da Settembre 2026, è migrato a **Jellyfin 12.0** su runtime **.NET 10** ed è ospitato su container LXC unprivileged su Proxmox VE (`pve3`), sfruttando l'accelerazione hardware della iGPU AMD Radeon 890M (RDNA 3.5).

---

## 1. Collocazione & Dimensionamento Risorse

- **Host Fisico**: Proxmox VE `pve3` (`10.10.10.31`).
- **Container LXC**: ID `2200` (`jellyfin-srv`).
- **Dimensionamento Compute**:
  - **RAM**: **8192 MB (8 GB)** (Allocazione minima stabile convalidata a fronte di incidenti OOM-killer con 2 GB durante scansioni massive con decine di migliaia di brani e film).
  - **Swap**: **2048 MB (2 GB)**.
  - **CPU Cores**: 2 core.
- **Indirizzo IP LAN**: `10.10.20.32/24` (VLAN 20 Client/App).
- **Porta Web & API**: `8096/TCP`.
- **Sistema Operativo**: Ubuntu 24.04 LTS (`noble`), kernel Linux 7.0.14-14-pve.
- **Repository Software**: Official Jellyfin APT deb822 (`/etc/apt/sources.list.d/jellyfin.sources`).
- **Stack Transcodifica**: `jellyfin-ffmpeg8` (v8.1.2-4-noble).

---

## 2. Accelerazione Hardware (AMD Radeon 890M / RDNA 3.5)

L'host `pve3` monta una APU AMD Strix Point con grafica integrata **Radeon 890M** (architettura `gfx1150` / RDNA 3.5). I nodi di rendering GPU sono passati all'LXC tramite configurazione Proxmox (`/etc/pve/lxc/2200.conf`):

- **Dispositivo**: `/dev/dri/renderD128` (gid 107 `render`, uid/gid mapping LXC).
- **Backend Driver**: VA-API con driver Mesa Gallium `radeonsi` (Mesa 26.0.8).
- **Profili Hardware Convalidati**:
  - **H.264 / AVC**: Decodifica e codifica hardware fino a 4K.
  - **HEVC / H.265**: Decodifica e codifica hardware 8-bit e 10-bit (Main 10) 4K 60fps.
  - **AV1**: Decodifica e codifica hardware nativa VA-API (`av1_vaapi`).
  - **VP9**: Decodifica hardware.
  - **Tonemapping HDR**: VPP Tonemapping hardware attivo.

---

## 3. Architettura Storage Ibrida & Policy Metadati

Per bilanciare prestazioni SQLite e scalabilità delle librerie multimediali, lo storage è strutturato su tre livelli:

| Percorso LXC | Tipo Mount | Storage Fisico | Descrizione |
| :--- | :--- | :--- | :--- |
| `/` (rootfs) | ZFS Subvolume | `rpool/data/subvol-2200-disk-0` (NVMe Crucial P3 Plus 1TB su PVE3) | Sistema operativo LXC |
| `/var/lib/jellyfin/data` | ZFS Dataset (`mp3`) | `rpool/data/jellyfin-db` (NVMe locale PVE3) | Database SQLite .NET 10 (`jellyfin.db`), journal WAL e task |
| `/etc/jellyfin` | NFSv4 (`mp1`) | TrueNAS Enterprise (`/mnt/stripe/k8s-arr/servarr-jellyfin-config`) | File XML di configurazione (`system.xml`, `encoding.xml`) |
| `/var/lib/jellyfin/metadata` | NFSv4 (`mp2`) | TrueNAS Enterprise (`/mnt/stripe/k8s-arr/servarr-jellyfin-config/metadata`) | Immagini, artwork e metadati estratti su pool NVMe |
| `/var/lib/jellyfin/metadata/trickplay` | Symlink locale | TrueNAS Enterprise (`/mnt/media/jellyfin-trickplay`) | File `.bif` anteprime scrubbing indirizzati al dataset ZFS dedicato |
| `/mnt/media` | NFSv4 (`mp0`) | TrueNAS Enterprise (`/mnt/oliraid/arrdata/media`) | Librerie multimediali pure (`movies`, `music`, ecc.) |

### Standard Operativo Metadati & Trickplay
- **Save artwork into media folders**: **DISABILITATO**. Tutte le copertine e le immagini devono essere archiviate centralmente sul pool NVMe TrueNAS (`mp2`) per evitare letture casuali lente sugli HDD rotanti e non sporcare le cartelle gestite da Radarr.
- **Metadata Savers (NFO)**: **DISABILITATO**. I metadati risiedono esclusivamente nel database SQLite NVMe.
- **Save trickplay images next to media**: **DISABILITATO**. I file `.bif` vengono instradati tramite symlink verso `/mnt/media/jellyfin-trickplay`, sfruttando il dataset dedicato ZFS con recordsize 1M e compressione zstd.

---

## 4. Integrazione Kubernetes & Stack Servarr

Nonostante Jellyfin risieda su un LXC esterno al cluster Talos K8s, è integrato nell'ecosistema di cluster tramite Traefik e CoreDNS:

### Routing Esterno & Interno (Traefik IngressRoute)
- **Dominio Pubblico**: `https://jellyfin.pindaroli.org` (terminato da Traefik con certificati Cloudflare e autenticazione).
- **Dominio Interno**: `https://jellyfin-internal.pindaroli.org` (LAN fidata, no OAuth).
- **Service K8s**: `jellyfin-external-svc` nel namespace `arr`, con Endpoint statico che punta a `10.10.20.32:8096`.

### Integrazione Radarr (Servarr Stack)
- Nel container Radarr (`servarr-radarr`), la notifica *Connect -> Jellyfin* è configurata verso l'host:
  `jellyfin-external-svc` (porta `8096`).
- Quando un nuovo film viene scaricato e importato, Radarr invia una notifica HTTP API a Jellyfin per aggiornare istantaneamente la libreria.

### Monitoraggio Homepage
- Il widget Jellyfin su Homepage (`https://homepage.pindaroli.org`) interroga l'endpoint:
  `http://jellyfin-external-svc.arr.svc.cluster.local:8096/health`
  e riporta lo stato in tempo reale.

---

## 5. Manutenzione & Procedure di Backup

- **Backup ZFS Atomico**: Prima di ogni aggiornamento applicativo, creare snapshot su `pve3`:
  ```bash
  zfs snapshot rpool/data/jellyfin-db@pre-upgrade-$(date +%F)
  zfs snapshot rpool/data/subvol-2200-disk-0@pre-upgrade-$(date +%F)
  ```
- **Backup Configurazioni NFS**: Creare tarball di sicurezza di `/etc/jellyfin`:
  ```bash
  tar -czvf /root/pre-upgrade-backup/etc-jellyfin-backup-$(date +%F).tar.gz -C /etc/jellyfin .
  ```
- **Ripristino Rapido Emergenza**: Procedura documentata nel piano [[jellyfin-12-clean-slate-rdna35]] (rollback ZFS in < 2 minuti).
