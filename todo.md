# 🚨 ACTIVE INCIDENTS (High Priority)

## [x] Ottimizzazione Diagnostica Avvio Tdarr Node (COMPLETED 2026-05-23)
> **Ref**: [[tdarr-startup-diagnostics-optimization]]
- [x] Modificare `start_node.sh` per aggiungere il controllo preventivo TCP verso il Tdarr Server (`tdarr-api.pindaroli.org:8266`). (COMPLETED 2026-05-23)
- [x] Verificare il comportamento in modalità fallimento (messaggi sintetici di retry, diagnostica estesa solo al blocco definitivo). (COMPLETED 2026-05-23)
- [x] Verificare il corretto avvio in modalità regolare. (COMPLETED 2026-05-23)

## [x] Ripresa Bonifica e Spostamento Mozart 225 (COMPLETED 2026-05-21)
> **Ref**: [[classical-music-taxonomy-optimization]]
- [x] **Rilevamento File (NFS Autofs)**: Identificato dataset ZFS figlio `/mnt/oliraid/arrdata/classical` non montato. Configurato automount nativo via `autofs` su macOS per `/Volumes/classical` e `/Volumes/media`, ripristinando l'accesso completo ai file fisici senza bisogno di rollback! (COMPLETED 2026-05-21)
- [x] **Rimozione & Consolidamento Perdita**: Accettata la perdita dei dati originali di Mozart 225. Eseguita la rimozione forzata dal database classico di Beets (3.323 tracce) e pulizia completa sul filesystem `/Volumes/classical` di tutti i symlink a staging e delle relative cartelle orfane di Mozart 225. (COMPLETED 2026-05-21)
*Vedi file di contesto dettagliato:* [/import_music/import_classical/context_resume_mozart225.md](file:///Users/olindo/prj/k8s-lab/import_music/import_classical/context_resume_mozart225.md)

---

## [x] Ripristino Connettività qBittorrent (Port Forwarding) (COMPLETED 2026-05-09)
> **Ref**: [[2026-05-08-qbittorrent-port-forward-outage]]
- [x] **Azione Manuale (OPNsense)**: Creare regola "Destination NAT" su `WAN` per porta `30661` (TCP/UDP) verso `10.10.20.60`.
- [x] **Verifica**: Controllare icona connettività (deve diventare verde) e velocità di download in qBittorrent WebUI.

---

# PostgreSQL Post-Recovery Tasks

## [x] qBittorrent NVMe Migration (COMPLETED 2026-05-24)
> Ref: [[qbittorrent-nvme-migration]]
- [x] **Ansible**: Creato playbook `truenas_nvme_setup.yml` per dataset `stripe/qb_temp` ed eseguito con successo con recordsize=1M e sync=disabled.
- [x] **K8s Storage**: Creato manifest `storage/incomplete-dw-pvc.yaml` (PV/PVC) con ottimizzazioni NFSv4.2 ed applicato con successo nel namespace `arr`.
- [x] **Helm**: Aggiornato `servarr/arr-values.yaml` con l'integrazione di `pvc-incomplete-dw` e tuning I/O avanzati di libtorrent (`DisableOSCache`), release aggiornata con successo alla REVISION 89.
- [x] **Patch Configurazione**: Riconfigurato a freddo `qBittorrent.conf` via SSH su TrueNAS con successo per abilitare `/data/incomplete`.
- [x] **Migrazione Fisica**: Spostati con successo 91.6 GB di file parziali a freddo via `rsync` su TrueNAS ad una velocità media di 367.2 MB/s.
- [x] **Verifica**: Convalidato il corretto funzionamento, il mount `/data/incomplete` di 4.9T su NVMe e lo stato Running di tutto il namespace `arr`.
- [x] **Backup**: Rinominata la vecchia directory HDD in `downloads/incomplete_backup` per sicurezza.

## Vaultwarden Deployment (PAUSED)

### [ ] Deployment Vaultwarden nel Cluster K8s
- [ ] **Prerequisito manuale (TrueNAS)**: Creare dataset ZFS `stripe/k8s-vaultwarden` + NFS export verso `10.10.10.0/24` e `10.10.20.0/24`.
- [ ] Aggiungere ruolo `vaultwarden` in `postgres/cluster.yaml` (sezione `managed.roles`) e creare `vaultwarden/vaultwarden-db.yaml`.
- [ ] Creare `vaultwarden/namespace.yaml` e `vaultwarden/vaultwarden-pvc.yaml` (StorageClass: `csi-nfs-stripe-arr-conf`, 10Gi).
- [ ] Generare `ADMIN_TOKEN` (bcrypt) e `DATABASE_URL`, cifrare con SOPS → `secrets-sops/vaultwarden-secrets.enc.yaml`.
- [ ] Creare `vaultwarden/vaultwarden-deployment.yaml` + `vaultwarden/vaultwarden-service.yaml`.
- [ ] Creare `vaultwarden/vaultwarden-ingressroute.yaml` (TLS wildcard `pindaroli-wildcard-tls`, no OAuth2).
- [ ] Aggiornare `rete.json`: aggiungere `vaultwarden` e `vaultwarden-internal` agli aliases di `traefik-lb` → sync DNS: `ansible-playbook ansible/playbooks/opnsense_sync_dns.yml`.
- [ ] Aggiornare `storage.json`: aggiungere entry `k8s_vaultwarden`.
- [ ] Verifica: curl HTTPS, login browser, browser extension, admin panel `/admin`.
- [ ] Aggiungere widget Vaultwarden in Homepage.

---

## Hardening Resilienza Bare-Metal (DeepSearch Insights)

### [ ] Tuning Timeout Talos (RTO < 30s)
- [ ] Modificare `talos-config/controlplane*.yaml` per ridurre i timeout di Kubernetes:
  - `node-monitor-grace-period: 16s`
  - `pod-eviction-timeout: 30s`
- [ ] Aumentare frequenza aggiornamento Kubelet (`node-status-update-frequency: 4s`).
- [ ] Applicare con `talosctl apply-config`.

### [ ] Networking L2 & Kube-VIP (Anti-Phantom VIP)
- [ ] Controllare e disabilitare `macfilter=0` sulle interfacce di rete (net0) delle VM Talos su Proxmox (PVE1, PVE3).
- [ ] Aggiungere env vars a kube-vip per persistenza ARP: `vip_preserve_on_leadership_loss=true`, `vip_arpRate=6000`.

### [ ] Ottimizzazione CNPG & Ingress
- [ ] Creare PodDisruptionBudget (PDB) per `postgres-main` con `maxUnavailable: 1`.
- [ ] Valutare impostazione `failoverDelay: 0` nella spec del Cluster CNPG per failover immediato.
- [ ] Implementare regole di "Retry" sull'Ingress Traefik per mascherare i drop TCP (5-10s) durante il failover L2 del VIP.

## Critical Actions

### 🎵 Music Rescue & Ingestion Pipeline (Modern & Classical)
- [ ] **Phase 1: Modern Music Rescue Pipeline** [[beets-music-rescue-pipeline]]
    - [x] Automatizzare il mount NFS di /Volumes/media e /Volumes/classical in modo centralizzato tramite autofs su macOS (Script setup_autofs.sh pronto). (COMPLETED 2026-05-21)
    - [x] Esecuzione Pilot Test su campione di 3 album. (COMPLETED)
    - [x] Migrazione massiva con gestione Hardlinks/Seeding. (COMPLETED)
    - [x] Case clash detection e unificazione (`Us3 vs US3`). (COMPLETED)
    - [ ] **Fase 3 (Post-Processing & Enrichment)**:
        - [x] Chroma Enrichment: Generazione AcoustID completata per tutte le 663 tracce anonime (`path::^_/`) + avviata risoluzione automatica via script custom `resolve_acoustids.py` in background. (COMPLETED 2026-05-19)
        - [x] MBSync Mirato: Recupero metadati ufficiali MusicBrainz via ID. (COMPLETED 2026-05-19)
        - [x] Mirror Clean: Bonifica speculare duplicati ad Anno 0 (DB + FS via `clean_all_zeros_duplicates.py`). (COMPLETED 2026-05-19)
        - [x] Orphan Clean: Rimozione massiva di 1845 file audio orfani/doppi lasciati da vecchi import, liberando 60.13 GB su TrueNAS via `clean_untracked_orphans.py`. (COMPLETED 2026-05-19)
        - [ ] Integrity Audit: Controllo file corrotti (`beet badfiles`) e tracce mancanti (`beet missing`).
        - [x] Allineamento Path Finale: Esecuzione di `beet update`/`move` pre-swap. (COMPLETED 2026-05-19)
    - [ ] Spostamento da `music_backup` alla Landing Zone definitiva `/Volumes/arrdata/media/music/pop_rock`.
    - [ ] Manual Import in `lidarr-pop` e ripristino Battiato (solo FLAC).
- [x] **Phase 2: Classical Music Segregation** [[classical-music-strategy]] (COMPLETED 2026-05-18)
    - [x] Creare dataset ZFS dedicato `/Volumes/classical` (staging & library) su TrueNAS (recordsize=1M).
    - [x] Eseguire `segregate_classical.py` per isolare i file classici dalle anomalie.
    - [x] Configurare `beets_classical_config.yaml` e avviare l'import nello staging (`./run_import.sh batch <N>`).
    - [x] Triage Picard per gli unmatched residui in `_Triage_Unmatched` (Completato via Beets con patch MusicBrainz).
    - [x] Valutare/Applicare la logica regex dinamica per il parsing del numero disco (`disc_and_track`) in `beets_classical_config.yaml` in caso di importazioni `asis` successive al reset.
- [x] **Phase 3: GitOps Homelab Integration (Dual-Pipeline Ingestion)** [[dual-pipeline-gitops-integration]] (COMPLETED 2026-05-18)
    - [x] Provisioning dataset ZFS TrueNAS con recordsize custom (1M).
    - [x] Sviluppo template Helm per `jellyfin-classic` e `lidarr-classic` in `pindaroli-arr-helm`.
    - [x] Aggiornare `oli-arr-values.yaml` in `pindaroli-arr-helm` con i blocchi di configurazione per i due nuovi servizi.
    - [x] Upgrade release Helm `oli-arr` con i nuovi servizi abilitati.
- [ ] **Phase 4: Non-Helm Infrastructure Provisioning (Classical Music)** [[dual-pipeline-gitops-integration]]
    - [x] Applicare manifest di storage PV/PVC per la classica: `kubectl apply -f storage/classical-media-pvc.yaml`.
    - [ ] Configurare qBittorrent (categoria `music-classical` su `/staging/classical`).
    - [ ] Configurare Prowlarr (tag `classical-indexers` per tracker dedicati).
    - [x] Configurare IngressRoutes di Traefik (Dual Route: esterno con OAuth2, interno senza OAuth2).
    - [x] Aggiornare `rete.json` con i record DNS per `jellyfin-classic` e `lidarr-classic`.
    - [x] Eseguire sync DNS Unbound su OPNsense con Ansible: `ansible-playbook ansible/playbooks/opnsense_sync_dns.yml`.
    - [ ] Disabilitare completed download handling in `lidarr-classic`.
    - [ ] Integrazione script di unmonitoring API (`segregate_classical.py` come Beets post-import hook).
    - [ ] Dichiarare Jellyfin options.xml ConfigMap per la classica.

- [ ] **Standardizzazione e Bonifica Libreria Classica** [[classical-music-standardization]]
    - [ ] **Esecuzione Standardizzazione**: Eseguire lo script `standardize_classical_track_filenames.py --run` per standardizzare i symlinks e allineare il database Beets classica (`classical_musiclibrary.db`).
    - [ ] **Bonifica Spazzatura macOS**: Purge massivo di tutti i 9.512 file di risorsa Apple Double `._*` nella libreria classica via `find /Volumes/classical/library -name "._*" -delete`.
    - [ ] **Vaccino macOS (Prevenzione permanente)**: Eseguire `defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true` su Mac Studio per disabilitare la scrittura di file `._*` e `.DS_Store` su share di rete (NFS/SMB) e riavviare Finder.

- [ ] **Ottimizzazione Tassonomia Classica: Integrazione Ibrida Beets + Jellyfin** [[classical-music-taxonomy-optimization]]
    - [x] **Preparazione Ambiente**: Installare `cyrtranslit`, `transliterate` e `unidecode` nel virtualenv di Beets.
    - [x] **Materializzazione Mapping**: Creare il file `artist_normalization.json` con i mapping canonicati.
    - [x] **Materializzazione Script**: Creare lo script `reorganize_recitals.py` per la normalizzazione linguistica ed allineamento dei recital.
    - [x] **Integrazione Configurazione**: Aggiornare `beets_classical_config.yaml` con i campi inline (`is_recital`, ecc.) e i tracciati dinamici condizionali.
    - [x] **Verifica Dry-Run**: Eseguire lo script in modalità dry-run e validare il comportamento delle espressioni Beets.
    - [x] **Esecuzione Reale**: Applicare la migrazione fisica dei symlinks dei recital e sincronizzare il database di Beets.
    - [ ] **Allineamento Jellyfin-Classic**: Ottimizzare Jellyfin-Classic con tag multivalore e plugin `jellyfin-musictags-plugin`.

### [ ] Security & Automation
- [x] **Integrazione Recyclarr (Anti-Spam)**: [[recyclarr-anti-spam-automation]]
    - [x] Sviluppo Helm-Native in `pindaroli-arr-helm` (**v1.2.3**).
    - [x] Pubblicazione Chart su GitHub Registry.
    - [x] Post-Rebranding: Creare record CNAME su Cloudflare: `charts` -> `pindaroli.github.io`
    - [x] Post-Rebranding: Assicurarsi che l'icona sia raggiungibile su `pindaroli.org/images/pindaroli.svg` (o caricarla nel repo)
    - [x] Deployment release `servarr` con `helm upgrade --version 1.2.3`.
    - [ ] **Verifica Sync**: Investigare il fallimento dell'ultimo sync (errore API/timeout) e validare i Custom Formats caricati in Radarr UI.
- [x] **Automazione Ansible Vault**: Configurato il file di password (es. `.vault_pass`) e mappare il percorso in `ansible.cfg` per permettere all'agente di gestire i segreti in autonomia senza richieste manuali.
- [x] **Ottimizzazione Secret Registry**: Definire un workflow (es. script di auditing) per alimentare e mantenere aggiornato il `wiki/entities/Secret_Registry.md` partendo dai dati reali di K8s e Ansible.

### [ ] Implementazione e Introduzione QMD in k8slab
- [ ] Studiare/definire architettura per l'integrazione di file `.qmd` (Quarto Markdown) nel progetto.
- [ ] Stabilire il workflow per rendering, pubblicazione o analisi dei dati.

### [ ] OPNsense Multi-Layered Ad-Blocking (Da Link Esterno)
- [ ] **Ottimizzazione DNS Filtering (Unbound DNSBL)**:
  - Passare alle blocklist **HaGeZi Multi Pro** (o Pro++) per bilanciare protezione e usabilità.
  - Configurare un **Cron Job** in OPNsense per aggiornare automaticamente le liste.
- [ ] **Integrazione AdGuard Home (AGH)**:
  - Installare plugin `os-adguardhome` dal repository `mimugmail`.
  - Configurare AGH in ascolto sulla porta **53** per i client.
  - Riconfigurare Unbound sulla porta **5353** come upstream per AGH.
  - Abilitare filtri specifici in AGH come "Search ads and self-promotion".
- [ ] **L7 Filtering con Zenarmor (DPI)**:
  - Deploy di Zenarmor per Deep Packet Inspection (DPI).
  - Bloccare la categoria **"Advertisements"** e creare regole esplicite per **"Google Ads"** e **"DoubleClick"**.
- [ ] **Nota Tecnica**: Gli ad "first-party" (es. Youtube) continueranno a richiedere uBlock Origin a livello browser.

### [x] DNS Stabilization & Split-Horizon (COMPLETED 2026-05-03)
- [x] Sincronizzato IP DNS Talos (`10.10.20.254`).
- [x] Configurate Access List Unbound per Pod Subnet (`10.244.0.0/16`).
- [x] Rimossi record 0.0.0.0 (Blackhole) da Cloudflare e Ansible.
- [x] Validata risoluzione interna ed esterna via Chrome/Curl.

### [x] Tdarr NFS & Node Connectivity (COMPLETED 2026-05-03)
- [x] Risolto `Permission denied` su TrueNAS (10.10.10.50).
- [x] Nodo Mac Studio (10.10.20.100) connesso e operativo.
- [x] Libreria `/Volumes/arrdata/media` montata correttamente.
- [x] **Automazione Mount**: Configurato `sudoers` su Mac Studio per mount passwordless.
- [x] Eliminato il file di configurazione duplicato e inutilizzato.
- [x] **Ottimizzazione Tdarr Server**:
    - [x] Disabilitare AutoUpdater.
    - [x] Ridurre `initialDelaySeconds` della Readiness Probe.

## 🖥️ Ripristino PVE2 (Hardware Pending)
- [ ] Riaggiungere IP `10.10.20.142` nel file `talos-config/talosconfig`.
- [ ] Verificare lo stato hardware e ricongiungere il nodo come nuovo membro (rimosso da etcd il 01/05 per stabilità).
- [ ] Applicare configurazione Talos: `talosctl apply-config -n 10.10.20.142 -f talos-config/controlplane.yaml` (impostando `bind-address=0.0.0.0`).
- [ ] Verificare lo stato del nodo con `talosctl get members` e salute quorum etcd.

## Future Integrations (n8n & Prefect)
### [ ] Transizione a Metodo B (Helm Secrets)
- [ ] Valutare il passaggio dal Metodo A (Apply manuale) al Metodo B (Integrazione atomica Helm + SOPS) per migliorare la coerenza GitOps.
- [ ] Richiede l'installazione plugin `helm-secrets` in tutti gli ambienti CI/CD.

## 🔄 Migrazione Database n8n su postgres-main
- **Stato Attuale**: `n8n` utilizza SQLite all'interno di `n8n-config-pvc`.
- [ ] **Preparazione**: Creare database `n8n` e utente dedicato nel cluster `postgres-main` (CNPG).
- [ ] **Configurazione**: Aggiornare il deployment di `n8n` per puntare a `postgres-main-rw.cnpg-system.svc.cluster.local`.
- [ ] **Verifica**: Verificare la migrazione dei dati e stabilità n8n.
- [ ] **Cleanup**: Eliminare il vecchio cluster PostgreSQL locale `n8n/postgres-n8n`.
- [ ] **Monitoring**: Attivare lo scraping metriche per n8n su `postgres-main`.

### [ ] Integrazione Tdarr & Prefect (Fase 4)
- [ ] **Storage**: Definire se usare storage locale veloce (Talos nodes) o share NFS per la Transcode Cache.
- [ ] **Risorse**: Limiti CPU/Memory per i pod Tdarr-Node per evitare saturazione cluster.
- [ ] **Prefect Workflow**: Integrazione per l'attivazione nodi "on-demand" e definizione degli eventi trigger.
- [ ] **Sicurezza**: Abilitazione middleware `google-auth` per accesso esterno a Tdarr UI.

## Network Architecture Optimization (Premium Approach)
- [x] **Punto A: Migrazione DNS Esterno (Cloudflare Dashboard)**
- [x] **Punto B: Rafforzamento Configurazione Tunnel (Cloudflared ConfigMap)**
- [x] **Documentazione Script Ansible (COMPLETED 2026-05-03)**
  - Rinominato `README.md` in `ansible-scripts-doc.md`.
  - [x] Descrizione completa degli script in `ansible/playbooks/`.
- [x] **Infrastructure Consistency**
  - [x] Trasformare il nome host fisico del nodo Proxmox principale da `pve` a `pve1` (Verificato).

## Network & Control Plane Stabilization (COMPLETED 2026-05-01)
- [x] **Risoluzione Asimmetria di Rete (ERR_CONNECTION_REFUSED)**
  - Migrato Traefik da Deployment a DaemonSet per distribuzione simmetrica.
  - Impostata `externalTrafficPolicy: Local` per eliminare inter-node SNAT.
  - Validata stabilità socket TCP con suite di test dedicata.
- [x] **Ripristino Service Discovery VictoriaMetrics**
  - Rimosso formalmente `talos-cp-02` da etcd per sbloccare KubePrism.
  - Verificato ripristino target in `vmagent` (32 target attivi).
- [x] **Documentazione Incidente**
  - Creato `traefik/INCIDENT_REPORT_20260501.md`.

## Maintenance & Monitoring

### [ ] Monitor Disk Usage on talos-cp-01
The disk `/var/mnt/postgres` was recently at 100%. Ensure the usage stays below 80%.
- Command: `talosctl -n 10.10.20.141 usage /var/mnt/postgres`

### [ ] Clean Up Emergency Scripts
- [ ] Delete `force-cleanup.yaml`
- [ ] Delete `force-cleanup-n8n` job (if not already deleted)

### [ ] Grafana Session Duration
Estendere la durata della sessione di login per evitare disconnessioni frequenti.
- Configurazione in `monitoring/vm-stack-values.yaml` (sezione `grafana.ini`).
- Parametri: `login_maximum_inactive_lifetime_duration` e `login_maximum_lifetime_duration`.

## Log Management (Future Phase)

### [ ] Centrale Log (VictoriaLogs)
Implementare un sistema di aggregazione log centralizzato nel cluster per:
- **Ollama**: Tailing di `/opt/homebrew/var/log/ollama.log` via Promtail.
- **Suite ARR**: Raccolta log dai pod Radarr, Lidarr, Prowlarr e qBittorrent.
- **Configurazione**: Aggiunta log source in Grafana.

## Ollama & Client Integration

### [ ] Installazione AIChat su Nodi Lab
Installare e configurare **AIChat** per interrogare Ollama (Mac Studio) direttamente dai terminali dei nodi senza `curl`.
- [ ] Installazione binario su `pve1`, `pve2`, `pve3`.
- [ ] Installazione binario su `truenas` (SCALE).
- [ ] Configurazione endpoint: `http://10.10.20.100:11434`.

### [ ] Multimedia Clients & Integration
- [ ] **Feishin Installation**: Configurare Feishin come player musicale desktop/mobile puntando alla libreria Navidrome/Lidarr.
    > **Ref**: [Gemini Share - Feishin Setup](https://gemini.google.com/share/8b7a061246b0)
- [ ] **Migrazione Jellyfin (jellyfin-srv) su Storage NFS (Stripe NVMe)** [[jellyfin-srv-storage-migration]]
    - [ ] Creare le directory `servarr-jellyfin-srv-config` e `servarr-jellyfin-srv-metadata` all'interno della share `/Volumes/k8s-arr-1/` (TrueNAS NVMe).
    - [ ] Impostare la corretta proprietà e permessi per UID `1000` (o l'utente jellyfin nel container).
    - [ ] Fermare a freddo il servizio Jellyfin nell'LXC `2200` (`systemctl stop jellyfin`).
    - [ ] Creare e committare su Git la pre-configurazione XML stabile in `servarr/jellyfin-srv/etc-jellyfin/`.
    - [ ] Eseguire il primo sync rsync speculare da Git e da LXC (metadati) a NFS.
    - [ ] Configurare i bind-mount `mp1` e `mp2` nel file `/etc/pve/lxc/2200.conf` del nodo `pve3` puntando a `/mnt/pve/k8s-arr/servarr-jellyfin-srv-*` e applicare l'ID Mapping custom (`lxc.idmap`).
    - [ ] Configurare l'override Systemd `XDG_CACHE_HOME=/var/cache/jellyfin` nell'LXC, riavviare il container e verificare stabilità e performance del database.

## 💿 Workload Futuro: Integrazione MakeMKV
- [ ] **⚠️ B. Il Task MakeMKV**: Configurare un pod per la conversione automatizzata ISO/DVD in MKV agganciato a Tdarr o come servizio standalone.

---

## 🛠️ Automazione Declarativa Storage (TrueNAS GitOps)
- [ ] **Configurazione Automatica TrueNAS**: Progettare ed implementare un meccanismo (es. playbook Ansible o script basato sulle API di TrueNAS SCALE) per allineare ed applicare dichiarativamente i dataset ZFS e le esportazioni NFS/SMB definiti nel file `storage.json` direttamente su TrueNAS.
