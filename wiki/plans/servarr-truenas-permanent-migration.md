---
title: "Migrazione Definitiva Servarr: K8s -> Docker su TrueNAS"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-18
tags:
  - "#migration"
  - "#docker"
  - "#truenas"
  - "#servarr"
---

# Migrazione Definitiva Servarr: K8s -> Docker su TrueNAS

Questo piano definisce la transizione **definitiva** dei carichi di lavoro Jellyfin, qBittorrent, Prowlarr e Homepage dal cluster Kubernetes a un ambiente nativo Docker Compose su TrueNAS Scale bare-metal (`10.10.10.50`), per massimizzare il risparmio energetico e spegnere il cluster K8s on-demand.

> [!CAUTION]
> **PROTOCOLLO DI ESECUZIONE (STRICT PHASING)**
> L'esecuzione è suddivisa in fasi sequenziali. È severamente **VIETATO** procedere alla Fase successiva se il Checkpoint della fase corrente non è stato completamente verificato e confermato con esito positivo dall'utente.

---

## 🏗️ FASE 1: Preparazione Storage & Protezione Dati (TrueNAS)
In questa fase si preparano le fondamenta su ZFS senza interrompere ancora i servizi su Kubernetes.

### Azioni
1. **Creazione Dataset:** Creazione manuale dei dataset ZFS isolati per le configurazioni Docker sotto il pool NVMe:
   - `/mnt/stripe/truenas-docker/jellyfin`
   - `/mnt/stripe/truenas-docker/qbittorrent`
   - `/mnt/stripe/truenas-docker/prowlarr`
   - `/mnt/stripe/truenas-docker/homepage`
2. **Setup Permessi:** Impostazione degli owner/group corretti in modo che corrispondano al PUID/PGID (`olindo:k8s` o `1000:1000`) per garantire l'accesso ai media dataset esistenti.
3. **Data Protection:** Adeguamento dei Replication Tasks in *Data Protection > Replication Tasks* per includere ricorsivamente `/mnt/stripe/truenas-docker` nel backup verso `oliraid`.

### 🛑 CHECKPOINT FASE 1
- [x] Il dataset `truenas-docker` e le sue sottocartelle esistono ed hanno i permessi corretti.
- [x] Il task di Snapshot e il Replication Task verso `oliraid` sono configurati per includere i nuovi dataset.
- [x] *(Completato)* Fase 1 approvata e verificata.

---

## 🐳 FASE 2: Deploy Stack Docker e Migrazione Dati (TrueNAS)
Fase di attivazione del nuovo motore applicativo.

### Azioni
1. **Migrazione Configurazioni e Adattamento (NFS -> Dataset Isolato):**
   - Spostare i file di configurazione di qBittorrent dall'attuale PVC su `/mnt/stripe/k8s-arr/` verso il nuovo dataset `/mnt/stripe/truenas-docker/qbittorrent`.
   - Spostare la configurazione NFS di Jellyfin (incluso `encoding.xml`) e i metadati da `/mnt/stripe/k8s-arr/servarr-jellyfin-config` verso `/mnt/stripe/truenas-docker/jellyfin`.
   - **Cruciale (Adattamento GPU):** Modificare `encoding.xml` (o tramite UI al primo avvio) per adattare l'accelerazione hardware alla iGPU **AMD Radeon Vega 8** (Ryzen 5 PRO 5650G) di TrueNAS. A differenza della RDNA 3.5 su `pve3`, la Vega 8 **non supporta la decodifica AV1**. Disabilitare i codec non supportati per evitare crash di transcodifica.
2. **Migrazione Database Jellyfin (Locale -> TrueNAS):** Spegnimento del vecchio LXC 2200 e copia del database `jellyfin.db` dal rpool locale di PVE3 verso `/mnt/stripe/truenas-docker/jellyfin/data`.
3. **Prowlarr (Fresh Start):** Nessuna migrazione dati complessa da Postgres. Ripartenza pulita su SQLite locale nel dataset dedicato `/mnt/stripe/truenas-docker/prowlarr`.
4. **Deploy Docker Compose:** Stesura e avvio del file `docker-compose.yaml` in `/mnt/stripe/truenas-docker/` contenente:
   - `jellyfin` (Mappatura GPU `/dev/dri/renderD128`)
   - `qbittorrent`
   - `prowlarr`
   - `homepage` (in modalità standalone)
   - `webhook-normalizer` (Sidecar con immagine custom per filebot/songkong, porte e secrets iniettati).
5. **Configurazione qBittorrent:** Impostazione della webUI e aggiunta della stringa hook: `curl -X POST http://webhook-normalizer:9000/hooks/normalize -d "path=%F" -d "category=%L"`.

### 🛑 CHECKPOINT FASE 2
- [x] Stack Docker acceso e funzionante su TrueNAS.
- [x] **Test Transcoding:** Avviata la riproduzione in Jellyfin e confermato l'uso della GPU Vega hardware (`/dev/dri/renderD128` Vulkan DRM interop).
- [x] **Test Post-Elaborazione:** Webhook Normalizer container attivo con FileBot e SongKong.
- [x] Prowlarr naviga e aggiunge correttamente gli indexer (11 indexer importati e operativi).
- [x] *(Completato)* Fase 2 verificata con successo.

---

## ☸️ FASE 3: Riconfigurazione Kubernetes e Ingress (Pindaroli-Arr-Helm)
In questa fase si spengono definitivamente i workload sul cluster e si ri-orienta il traffico rimasto.

### Azioni
1. **Downscaling:** In `k8s-lab/servarr/arr-values.yaml`, impostare `enabled: false` per qBittorrent, Prowlarr e Jellyfin. Eliminazione delle risorse e Pod correlati.
2. **Cross-Communication:** Aggiornamento delle configurazioni di Sonarr, Radarr, e Lidarr in K8s affinché si colleghino a qBittorrent e Prowlarr usando l'IP diretto `10.10.10.50` anziché i nomi DNS interni al cluster.
3. **Routing Esterno (Traefik K8s):** Creazione di manifest `ExternalName` e `IngressRoute` in `charts/servarr/templates/external-services.yaml` per instradare le chiamate a `jellyfin.pindaroli.org`, `qbittorrent...` e `prowlarr...` verso TrueNAS quando il cluster è acceso.
4. **Aggiornamento DNS:** Aggiornamento degli Host Overrides in OPNsense per risolvere i domini migrati a `10.10.10.50`.

### 🛑 CHECKPOINT FASE 3
- [x] Sonarr e Radarr riescono a inviare torrent a qBittorrent su `10.10.10.50` (Test Radarr, Lidarr e Autobrr verificati HTTP 200 OK).
- [x] Navigando su `https://jellyfin.pindaroli.org` / `-internal` (a cluster K8s acceso) si raggiunge TrueNAS con certificato valido (Verificato HTTP/2 302 web/ Kestrel).
- [x] I Pod obsoleti di Jellyfin, Prowlarr e qBittorrent non esistono più nel cluster (terminati).
- [x] *(Completato)* Fase 3 approvata e verificata con successo.

---

## 🧹 FASE 4: Smantellamento e Hardening
Rimozione del codice morto e delle infrastrutture orfane.

### Azioni
1. [x] **Distruzione LXC:** Spegnimento definitivo, rimozione (`pct destroy 2200 --purge`) e distruzione del dataset associato `rpool/data/jellyfin-db` su PVE3 (recuperati 5 GB NVMe).
2. [x] **Modernizzazione Script Normalizzazione & Trigger Automatico qBittorrent:** Creato script CLI di trigger universale `scripts/servarr/trigger_normalization.sh` e server webhook `webhook_server.py` su TrueNAS (`10.10.10.50:9000`), aggiornata la skill `video-ingestor`. Dichiarato e montato lo script permanente `trigger-job.sh` nel `docker-compose.yaml` di qBittorrent (`/scripts/trigger-job.sh:ro`) con log su `/config/qBittorrent/logs/trigger.log`. Verificata con successo la normalizzazione automatica e manuale reale (*"The Neon Demon"* e *"La Grazia"* con hardlink ZFS, artwork completi e scan Jellyfin).
3. [x] **Pulizia e Ottimizzazione Ansible:** Creazione del playbook depurato `ansible/playbooks/infrastructure/shutdown_to_truenas_only.yml` e rimozione dei vecchi script di failover `migrate_to_truenas_only.yml` e `restore_from_truenas_only.yml`.

### 🛑 CHECKPOINT FINALE
- [x] Ambiente K8s, PVE e Homelab pulito.
- [ ] Spegnimento temporaneo del cluster K8s per verificare che la fruizione multimediale e i download continuino senza interruzioni dalla dashboard Homepage di TrueNAS (`http://10.10.10.50:3000`).

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 4 / Smantellamento e Hardening (Checkpoint Finale)
- **Ultima Azione Completata**: Ingestione di *"La Grazia (2025)"* completata con successo (hardlink ZFS, artwork, scan Jellyfin). Ripristinato e validato il trigger automatico permanente in qBittorrent Docker su TrueNAS tramite volume mount in `docker-compose.yaml` e versione Git dichiarativa in `scripts/servarr/trigger-job.sh`.
- **Prossimo Passo Operativo**: Esecuzione del test di spegnimento on-demand K8s/PVE con il comando:
  `ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/shutdown_to_truenas_only.yml`
  e verifica della completa indipendenza dei carichi multimediali da Homepage su TrueNAS (`http://10.10.10.50:3000`).
- **Blocchi/Decisioni Pendenti**: Nessuno. Pronto per la verifica finale di spegnimento a scelta dell'utente.
