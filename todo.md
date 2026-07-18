# 🚨 ACTIVE INCIDENTS (High Priority)

## 🚀 [x] ✅ RISOLTO: Bonifica e Rotazione API Key OPNsense (Leakage Mitigation)
- [x] Generare una nuova coppia di API Key su OPNsense per l'utente `root`.
- [x] Sostituire le chiavi in `ansible/vars/opnsense_secrets.yml` e cifrare il file con Ansible Vault.
- [x] Sostituire le chiavi nel file locale `ansible/OPNsense.internal_root_apikey.txt` (escluso da Git).
- [x] Verificare il funzionamento delle nuove chiavi con lo script `scripts/check_opnsense_plugins.py`.
- [x] **Leakage Risolto**: Le chiavi esposte sono state rimosse dal firewall e quelle nuove sono protette tramite cifratura con Ansible Vault.

## 🚀 [ ] Talos & Kubernetes Upgrade Plan [[talos-1.13.5-upgrade]]
### [x] FASE 1: Upgrade Talos OS (v1.12.0 -> v1.13.5)
- [x] Aggiornare client macOS (`brew upgrade siderolabs/tap/talosctl` e `kubernetes-cli`).
- [x] Rigenerare installer image con estensione `qemu-guest-agent`.
- [x] Eseguire pre-flight checks (salute etcd, CNPG, workload).
- [x] Rolling upgrade nodo 1 (`talos-cp-01` - `10.10.20.141`) e validazione post-reboot.
- [x] Rolling upgrade nodo 2 (`talos-cp-02` - `10.10.20.142`) e validazione post-reboot.
- [x] Rolling upgrade nodo 3 (`talos-cp-03` - `10.10.20.143`) e validazione globale.

### [x] FASE 2: Upgrade Kubernetes (v1.34.1 -> v1.36.2) [[kubernetes-upgrade-1.34-1.36]]
- [x] Verificare compatibilità CNI, operatori (CNPG) e manifest inline.
- [x] Eseguire transizione intermedia (`talosctl upgrade-k8s --to 1.35.x`).
- [x] Eseguire transizione finale alla versione stabile (`talosctl upgrade-k8s --to 1.36.2`).
## [x] ✅ FATTO: Implementazione CoreDNS Hard Anti-Affinity [[coredns-hard-anti-affinity]]
- [x] Analisi architetturale completata (Scelta strategia Disable & Replace).
- [x] Materializzazione piano nel Wiki.
- [x] Aggiornamento guardia procedurale per upgrade Talos nel wiki.
- [x] Modifica manifesti `talos-config/controlplane-cp-0*.yaml`.
- [x] Validazione ed esecuzione apply-config.

## [x] 🟢 COMPLETATO: Espansione Geometrica oliraid ed Evacuazione Special VDEV [[oliraid-expansion-special-vdev-evacuation]]
- [x] **Fase Preliminare: Isolamento Totale del Sistema e Messa in Sicurezza**
  - [x] Accedere alla WebUI di TrueNAS, disattivare l'avvio automatico e arrestare i servizi SMB, NFS e iSCSI.
  - [x] Arrestare lo stack dei container: `systemctl stop docker`
  - [x] Verificare che nessun processo acceda al pool: `lsof /mnt/oliraid` (deve essere vuoto).
- [x] **Sotto-piano A: Espansione del RAID-Z2 da 4 a 5 Dischi**
  - [x] Verificare lo stato del pool `zpool status oliraid` (deve essere ONLINE, no resilver/scan attivo, CKSUM a 0).
  - [x] Preparare `/dev/sdi` (wipefs, parted mklabel gpt, parted mkpart).
  - [x] Verificare allineamento `parted /dev/sdi align-check optimal 1` (deve restituire `1 aligned`).
  - [x] Ottenere il `NEW_PARTUUID` con blkid.
  - [x] Avviare l'espansione: `zpool attach oliraid raidz2-0 /dev/disk/by-partuuid/${NEW_PARTUUID}`.
  - [x] Monitorare in tmux: `watch -n 10 "zpool status oliraid | grep -A 8 -i 'expand'"` fino al completamento.
  - [x] Verificare aumento capacità `zpool list -v oliraid`.
- [x] **Sotto-piano B: Evacuazione dello Special VDEV e Ribilanciamento Parità**
  - [x] Applicare policy 64K: `zfs set special_small_blocks=64K oliraid/arrdata`.
  - [x] Verificare l'ereditarietà: `zfs get -r special_small_blocks oliraid/arrdata`.
  - [x] Eliminare ricorsivamente tutte le snapshot: `zfs destroy -r oliraid/arrdata@%`.
  - [x] Verificare assenza snapshot: `zfs list -t snapshot -r oliraid/arrdata` (deve restituire `no datasets available`).
  - [x] Avviare la riscrittura ricorsiva in tmux: `zfs rewrite -rvx /mnt/oliraid/arrdata`.
  - [x] Monitorare lo spostamento fisico dei blocchi e la liberazione dello Special VDEV `watch -n 10 "zpool list -v oliraid"`.
  - [x] Eseguire scrub completo: `zpool scrub oliraid` e verificarlo.
  - [x] Riattivare lo stack applicativo: `systemctl start docker`.
  - [x] Riattivare SMB, NFS e iSCSI da WebUI.


## [x] 🟢 COMPLETATO: Allineamento Coerenza Rete (Symmetric Routing) (COMPLETED 2026-06-30)
- [x] **Sorgente di Verità & Configurazione Logica**:
  - [x] Aggiornare `rete.json` con `management_ip` di OPNsense a `192.168.100.1` (OOB) e impostare gli IP delle interfacce logiche `gw-vlan10` e `gw-vlan20` su `"None"`.
  - [x] Aggiungere `"dns_server": "192.168.2.254"` sotto `switch10g` in `rete.json`.
- [x] **Aggiornamento Cluster Kubernetes (Talos)**:
  - [x] Modificare i file manifest `controlplane*.yaml` e `controlplane.yaml` in `talos-config/` per puntare il DNS a `192.168.2.254`.
  - [x] Applicare la configurazione a `talos-cp-01` (`10.10.20.141`):
    `talosctl apply-config -n 10.10.20.141 -f talos-config/controlplane-cp-01.yaml`
  - [x] Verificare la corretta applicazione e risoluzione DNS su `talos-cp-01` (es. `talosctl read /etc/resolv.conf -n 10.10.20.141`).
  - [x] Applicare la configurazione a `talos-cp-02` (`10.10.20.142`):
    `talosctl apply-config -n 10.10.20.142 -f talos-config/controlplane-cp-02.yaml`
  - [x] Verificare la risoluzione DNS su `talos-cp-02`.
  - [x] Applicare la configurazione a `talos-cp-03` (`10.10.20.143`):
    `talosctl apply-config -n 10.10.20.143 -f talos-config/controlplane-cp-03.yaml`
  - [x] Verificare la risoluzione DNS su `talos-cp-03`.
- [x] **Aggiornamento Endpoint e Servizi Kubernetes**:
  - [x] Modificare `homepage/homepage.yaml` allineando l'EndpointSlice `opnsense-external-1` all'IP OOB `192.168.100.1`.
  - [x] Applicare il manifest aggiornato al cluster:
    `kubectl apply -f homepage/homepage.yaml`
  - [x] Verificare che il pod Homepage si riavvii con successo.
  - [x] Testare l'accesso Web da esterno a `https://firewall.pindaroli.org` per verificare il corretto instradamento tramite Traefik.
- [x] **Allineamento Script e Playbook**:
  - [x] Aggiornare `scripts/check_lab.py`, `scripts/test_dhcp.sh`, `scripts/test_dns.sh`, `scripts/test_internet.sh`.
  - [x] Aggiornare playbook Ansible `opnsense_sync_dhcp.yml`, `opnsense_sync_dns.yml`, `opnsense_adblock_automation.yml` e script `diag_opnsense_api.py`.
- [x] **Allineamento Wiki Entities**:
  - [x] Aggiornare `Network_Registry.md`, `OPNsense.md`, `Talos_Cluster.md` con i nuovi IP e ruoli.

## [x] 🟢 COMPLETATO: Chiarificazione Configurazione TrueNAS in `rete.json` (COMPLETED 2026-06-30)
> **Contesto**: Verificato e convalidato che l'IP legacy `10.10.10.254` di OPNsense su VLAN 10 non è attivo per via del Symmetric Routing. Di conseguenza, la configurazione di TrueNAS su `192.168.2.254` in `rete.json` è corretta e l'unica funzionante.
- [x] Verificare DNS su TrueNAS in produzione.
- [x] Allineare documentazione nel Wiki e confermare l'esattezza di `rete.json`. VLAN 10 = `10.10.10.254`).



## [x] OPNsense Recovery & Post-Restore GUI Alignment Tasks [[opnsense-recovery-and-temporary-routing]] (COMPLETED 2026-06-20)
- [x] **Ripristinare OPNsense** tramite chiavetta USB e caricamento del backup `config-OPNsense.internal-prima-di-migrazione 20260318235902.xml` (dopo l'installazione del nuovo SSD). Allineato a versione `26.1.6.2`.
- [x] **Riapplicare configurazioni mancanti via GUI**:
  - [x] **ACL Unbound per Kubernetes**:
    - Andare in `Services -> Unbound DNS -> Access Control`.
    - Modificare l'ACL `VLANs_Allow` (o crearne una nuova) ed aggiungere la subnet dei Pod `10.244.0.0/16` nei network consentiti (con azione `Allow`).
    - *Nota*: Questo è fondamentale per la risoluzione DNS interna dei Pod del cluster Talos (Rif: [[2026-05-03-dns-split-horizon-conflict]]).
  - [x] **Alternate Hostnames**:
    - Andare in `System -> Settings -> Administration`.
    - Inserire `firewall-direct.pindaroli.org` nel campo `Alternate Hostnames` (in aggiunta a `opnsense.pindaroli.org` e `pippo.pindaroli.org`).
    - *Nota*: Evita errori di DNS Rebinding accedendo all'interfaccia di amministrazione via FQDN.
- [x] **Verifiche Post-Recovery**:
  - Eseguire ping test dal Mac Studio verso gli IP di OPNsense (`192.168.100.1` OOB e `192.168.2.254` Transit).
  - Eseguire `ansible-playbook ansible/playbooks/opnsense_sync_dns.yml` per risincronizzare gli host override.

## [x] Ripristino della Rete Originale (DA FARE dopo il ripristino di OPNsense) [[opnsense-recovery-and-temporary-routing]] (COMPLETED 2026-06-20)
- [x] **Ripristinare i Collegamenti Fisici** (Eseguito):
  - Scollegare il cavo WAN dal Cudy AP11000 e ricollegarlo alla porta `igc0` di OPNsense.
  - Collegare la porta LAN/Trunk di OPNsense a `igc1`.
  - Collegare la porta OOB di OPNsense a `igc3`.
  - Sullo switch **GoodTop**, ricollegare la porta 4 alla porta LAN normale del Cudy.
- [x] **Riconfigurazione Logica**:
  - Accedere all'AP11000 (`http://10.10.20.103`) e ripristinare la modalità **Access Point** (o caricare la config AP dal backup).
  - Ripristinare la porta 4 dello switch **ONTi** (rimuovere VLAN 30 Access).
  - Ripristinare la porta 4 dello switch **GoodTop** (rimuovere VLAN 30 Access, impostarla nuovamente come Trunk Native 20, Tagged 1, 99).
- [x] **Accensione Infrastruttura & Mac Studio**:
  - Riattivare la rete cablata del Mac Studio e verificarne la navigazione regolare via cavo.
  - Procedere con l'avvio ordinato dei nodi Proxmox e TrueNAS (Vedi [[Power_Sequence]]).

## [ ] Post-Incident: Flannel DNS Cascading Failure (2026-06-03)
> **Ref**: [[2026-06-03-flannel-restart-dns-cascading-failure]]

### [x] 5.1 Post-Maintenance Checklist (Procedura Operativa)
- [x] Aggiungere alla procedura di manutenzione standard il controllo obbligatorio post-riavvio:
  ```bash
  kubectl get pods -A | grep -v -E "Running|Completed"
  ```
  Documentare nel workflow [[Node_Maintenance]] la regola: se ci sono pod in `CrashLoopBackOff` e il problema sottostante è risolto, effettuare `kubectl rollout restart` / `kubectl delete pod` immediatamente.

### [x] 5.2 Alert CrashLoopBackOff > 15m (VictoriaMetrics)
- [x] Aggiungere una `PrometheusRule` (VMRule) nel namespace `monitoring` che faccia scattare un alert se un pod è in `CrashLoopBackOff` per più di 15 minuti.

### [x] 5.3 Tdarr Server Image Hardening
- [x] Investigare il problema strutturale: `tdarr-server` scarica `jellyfin-ffmpeg` da GitHub ad ogni avvio del pod (nel container entrypoint). Risolto implementando un `initContainer` con controllo di rete e DNS su busybox.

---

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
- [x] Backup: Rinominata la vecchia directory HDD in `downloads/incomplete_backup` per sicurezza.

## [ ] Rivedere User e Pass PostgreSQL dei DB vari
- [ ] Mappare tutti i DB su `postgres-main` (es. autobrr, n8n, ecc.).
- [ ] Verificare ed eventualmente modificare la sicurezza delle credenziali (molte password coincidono con l'username/db_name).
- [ ] Assicurarsi che i nuovi secret siano cifrati via SOPS.

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

## Radarr Upgrade

### [ ] Upgrade Radarr a v6.3.0.10514 [[radarr-upgrade-6.3.0]]
- [x] **Fase 1: Backup Preventivo**
  - [x] Eseguire backup Velero: `velero backup create backup-pre-radarr-upgrade-6.3.0-$(date +%F) --include-namespaces arr --wait`
- [x] **Fase 2: Modifica Configurazione**
  - [x] Aggiornare `servarr/arr-values.yaml`
- [ ] **Fase 3: Deploy & Verifiche**
  - [ ] Eseguire dry-run e deploy
  - [ ] Validare pod e log
  - [ ] Controllare migrazioni database PostgreSQL

### [x] ✅ COMPLETATO: Upgrade Radarr a v6.2.1.10461 [[radarr-upgrade-6.2.1]]
- [x] **Fase 1: Backup Preventivo**
  - [x] Eseguire backup Velero: `velero backup create backup-pre-radarr-upgrade-$(date +%F) --include-namespaces arr --wait`
- [x] **Fase 2: Modifica Configurazione**
  - [x] Aggiornare `servarr/arr-values.yaml`
- [x] **Fase 3: Deploy & Verifiche**
  - [x] Eseguire dry-run e deploy
  - [x] Validare pod e log
  - [x] Controllare migrazioni database PostgreSQL

## qBittorrent Categories Provisioning & jellyfin-classic Removal

### [x] ✅ COMPLETATO: Provisioning Categorie qBittorrent & Rimozione jellyfin-classic [[qbittorrent-category-provisioning]]
- [x] **Fase 1: Implementazione Helm (`pindaroli-arr-helm`)**
  - [x] Eliminare directory `templates/jellyfin-classic`
  - [x] Rimuovere `jellyfin-classic` da `values.yaml`
  - [x] Creare `templates/qbittorrent/post-deploy-job.yaml`
- [x] **Fase 2: Configurazione Cluster (`k8s-lab`)**
  - [x] Rimuovere `jellyfin-classic` e aggiungere le categorie in `servarr/arr-values.yaml`
- [x] **Fase 3: Deploy & Verifiche**
  - [x] Eseguire dry-run e validazione localmente
  - [x] Eseguire deploy e validare l'esecuzione del Job di setup categorie

## MinimServer Deployment

### [ ] Deployment di MinimServer nel Cluster K8s [[minimserver-deployment]]
> **Stato**: In sospeso su richiesta dell'utente (Fase 1 approvata in data 2026-07-05).
- [x] **Fase 1: Approvazione Piano**
  - [x] Ottenere via libera su [[minimserver-deployment]].
- [ ] **Fase 2: Sviluppo Helm (in pindaroli-arr-helm)**
  - [ ] Creare i template in `charts/servarr/templates/minimserver/`.
  - [ ] Aggiungere i default in `charts/servarr/values.yaml`.
  - [ ] Validare localmente (`helm lint` e `helm template`).
- [ ] **Fase 3: Configurazione K8s-Lab**
  - [ ] Configurare l'override attivo in `servarr/arr-values.yaml`.
  - [ ] Registrare DNS in `rete.json` ed eseguire sync DNS con Ansible.
- [ ] **Fase 4: Deploy & Validazione**
  - [ ] Eseguire `helm upgrade --install` di `oli-arr`.
  - [ ] Validare pod, log, mount e discovery DLNA.
  - [ ] Aggiungere widget MinimServer in Homepage.

---

## Hardening Resilienza Bare-Metal (DeepSearch Insights)

### [ ] Tuning Timeout Talos (RTO < 30s) [IN ATTESA DI UPGRADE A TALOS 1.14]
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



### [ ] Security & Automation
- [ ] **Automazione Drain Talos su Hypervisor Shutdown**: Creare uno script/workflow automatico per effettuare il cordon e il drain del nodo Talos corrispondente prima dello spegnimento ordinato (o forzato da UPS/NUT) di un nodo hypervisor Proxmox (PVE1, PVE2, PVE3).
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

## 🖥️ Connettività OOB e Migrazione 10G PVE3
- [x] **Fase 1: Configurazione Canale di Servizio Fisico (OOB)** [[plan-out-of-band-service-access]] (COMPLETED 2026-05-31)
    - [x] Creare VLAN 99 sui tre switch e taggarla sui link di Uplink (COMPLETED 2026-05-30)
    - [x] Configurare le porte OOB dei nodi Proxmox e della scheda 10G del Mac Studio (Trunk Native 20 / Tagged 99) (COMPLETED 2026-05-31)
    - [x] Configurare lo split-routing fisso sulla VLAN virtuale `vlan0` del Mac Studio (`192.168.100.99`, no gateway) (COMPLETED 2026-05-31)
    - [x] Configurare l'interfaccia VLAN virtuale `vlan1` (VLAN 1) sul Mac Studio (`192.168.2.99`, no gateway) per la gestione diretta degli switch managed (COMPLETED 2026-06-09)
    - [x] Investigare e risolvere l'irraggiungibilità della porta di servizio OOB di PVE1 (192.168.100.11 non risponde al ping dal Mac Studio, ARP incompleto) (COMPLETED 2026-05-31 - Risolto con allineamento database globale VLAN degli switch Realtek)
    - [x] Validare la connettività OOB ed isolamento IP degli switch (No-SVI su VLAN 99) (COMPLETED 2026-05-31)
- [x] **Fase 2: Test Isolato a Freddo di PVE2** [[plan-out-of-band-service-access]] (COMPLETED 2026-06-06)
    - [x] Collegare la porta di servizio di PVE2 al switch camera ed accenderlo
    - [x] Eseguire il ping a `192.168.100.21` ed entrare nella GUI Proxmox per convalidare l'hardware
    - [x] **Riallineamento IP OOB PVE2**: Cambiare l'IP di servizio OOB di PVE2 da `192.168.100.200` a `192.168.100.21` (in `/etc/network/interfaces` e `rete.json`) per allinearlo al pattern di PVE1 (`100.11`) e PVE3 (`100.31`). (COMPLETED 2026-06-02)
    - [x] Spegnere PVE2 e riposizionarlo nel rack definitivo in sala server

- [x] **Fase 3: Upgrade PVE3 a Proxmox VE 9.2 e Re-join Cluster (PRIORITY 0)** [[pve3-reinstallation-ve9.2]] (COMPLETED 2026-06-02)
    - [x] Predisporre i backup e le configurazioni necessarie. (COMPLETED 2026-06-02)
    - [x] Eseguire l'upgrade o reinstallazione pulita di PVE3 a VE 9.2. (COMPLETED 2026-06-02)
    - [x] Configurare rete 10G appena allestita e reinserire il nodo nel cluster con PVE1. (COMPLETED 2026-06-02)

- [x] **Fase 3.5: Upgrade PVE1 a Proxmox VE 9.2** [[pve1-upgrade-ve9.2]] (COMPLETED 2026-06-22)
    - [x] Spegnimento ordinato delle VM/LXC su PVE1 (talos-cp-01, TrueNAS, PBS)
    - [x] Esecuzione upgrade `apt update && apt dist-upgrade`
    - [x] Reboot di PVE1 e verifica dell'avvio su systemd-boot
    - [/] Ripristino VM/LXC in sequenza (TrueNAS e PBS attivi, Talos CP1 fermo per ripristino K8s)
    - [x] Verifica del quorum corosync (`pvecm status`)

- [x] **Fase 3.5a: Upgrade PVE2 a Proxmox VE 9.2** (COMPLETED 2026-06-28)
    - Da fare prima del ripristino del cluster PVE e del rename del nodo `pve` in `pve1`.
    - [x] Disarmo HA manager (`pve-ha-lrm`, `pve-ha-crm`) su PVE2 in stato isolato.
    - [x] Spegnimento VM Talos (2300) per evitare fencing/reboot forzati.
    - [x] Backup locale configurazioni `/etc/` in `/root/`.
    - [x] Aggiornamento pacchetti (`apt-get dist-upgrade`) e riavvio host.
- [x] **Fase 3.5b: Upgrade PVE3 a Proxmox VE 9.2** (COMPLETED 2026-06-28)
    - Da fare prima del ripristino del cluster PVE e del rename del nodo `pve` in `pve1`.


- [x] **Fase 3.7: Rinomina Hostname Nodo PVE1 (`pve` → `pve1`)** [[pve1-hostname-rename]] (COMPLETED 2026-06-29)
    - [x] Verifica prerequisito: `pvecm status` → 3 nodi, Quorate: Yes
    - [x] FASE 0: Backup `/etc/hostname`, `/etc/hosts`, `corosync.conf`, `storage.cfg`
    - [x] FASE 1: Spegnimento ordinato VM critiche (1300 talos-cp-01, 1100 truenas, 1400 pbs)
    - [x] FASE 2: Stop cluster services → `pmxcfs -l` → modifica `corosync.conf` (`name: pve1`, `config_version: 13`) → rinomina `/etc/pve/nodes/pve/` → `/etc/pve/nodes/pve1/` → restart servizi
    - [x] FASE 3: Aggiornamento `storage.cfg` (`nodes pve` → `nodes pve1`)
    - [x] FASE 4: Aggiornamento `rete.json` (`host_node: pve` → `pve1`) + `ansible-playbook opnsense_sync_dns.yml`
    - [x] FASE 5: Riavvio VM in sequenza e verifica finale (`pvecm nodes`, `kubectl get nodes`, GUI Proxmox)

- [x] **Fase 3.6: Upgrade TrueNAS SCALE a 25.10.4** [[truenas-scale-upgrade-25.10.4]] (COMPLETED 2026-06-21)
    - [x] Backup della configurazione di TrueNAS SCALE ed esportazione chiavi ZFS
    - [x] Spegnimento controllato del cluster Kubernetes Talos (drenaggio e shutdown worker + VM 1300 talos-cp-01)
    - [x] Backup della VM 1100 (TrueNAS) su PBS in modalità Stop
    - [x] Configurazione PCI Passthrough (`rombar=0`) su PVE1 per i tre controller LSI
    - [x] Iniezione preventiva del parametro kernel `modules_load=virtio-scsi` su TrueNAS
    - [x] Esecuzione aggiornamento TrueNAS a 25.10.4 via Web GUI
    - [x] Validazione post-upgrade (pool ZFS, ens18/ens19, servizi SMB/NFS)
    - [ ] Avvio ordinato di Talos VM 1300 e nodi worker (Deferito a piano specifico Talos)


- [x] **Fase 4A: Reinstallazione PVE2 e Migrazione Dati** [[pve2-reinstallation-migration]] (COMPLETED 2026-06-06)
    - [x] Fase 0: Dump configurazioni e backup forzato PBS da oldPVE2 (con PVE2 acceso)
    - [x] Fase 1: Installazione Proxmox VE 9.2 su newPVE2 (nvme0n1 Intel 512GB) da USB
    - [x] Fase 2: Configurazione rete, hosts, repo su newPVE2
    - [x] Fase 3: Re-join al cluster Proxmox (pvecm add)
    - [x] Fase 4: Ripristino VM/LXC da PBS (incluso VM 2300 talos-cp-02, stopped)
    - [x] Fase 6: Aggiornamento rete.json e istruzioni/interfaces_pve2.txt (OOB IP → .21)
- [x] **Fase 3B: Migrazione Fisica 10G PVE3 e DR del Cluster** [[pve3-10g-migration-recovery]] (COMPLETED 2026-06-06)
    - [x] Forzare i backup manuali su Proxmox Backup Server (PBS) ed eseguire lo shutdown ordinato del rack
    - [x] Configurare Trunk VLAN 10/20 su ONTi e migrare rete PVE3 a 10G via OOB
    - [x] Rilevare la scheda 10G ed aggiornare e testare `/etc/network/interfaces` in OOB
    - [x] Riavviare l'Homelab in sequenza ordinata (PVE1/TrueNAS prima, satelliti poi) ed allineare hosts e Corosync
- [x] **Fase 3C: Ripristino Cluster Kubernetes Talos (ULTIMO STEP)** [[talos-k8s-cluster-restoration]] (COMPLETED 2026-06-30)
    - [x] Verificare Proxmox 3 nodi in quorum stabile
    - [x] Avviare talos-cp-02 (VM 2300) su PVE2 e verificare boot Talos
    - [x] Re-apply `controlplane-cp-02.yaml` se necessario per reintegrazione etcd
    - [x] Verificare 3 nodi K8s Ready e 3 membri etcd Healthy
    - [x] Rimuovere fencing e verificare ripristino automatico `postgres-main` (3/3 repliche)
    - [x] Verificare tutti i servizi applicativi (n8n, Prefect, Lidarr, etc.)



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

### [ ] Studio e Risoluzione Dipendenza Incrociata NFS (TrueNAS ↔ PBS/PVE1)
  > **Contesto**: Durante lo shutdown del rack del 29/06/2026, lo spegnimento di TrueNAS (`VM 1100`) prima di PBS (`LXC 1400`) ha causato lo stato `Ds` (`rpc_wait_bit_killable`) dei processi legati a NFS (come `lxc-start` per il container 1400 e client dell'host PVE1). Questo ha reso impossibile l'arresto di PBS, mandando in timeout infinito `pct stop` per l'impossibilità del kernel di contattare il server NFS spento (con interfaccia di rete virtuale veth del container già disattivata).
  > **Risoluzione temporanea necessaria**:
  > 1. Avvio forzato di TrueNAS (`qm start 1100`) per rendere nuovamente disponibile il server NFS.
  > 2. Unmount lazy (`umount -f -l`) di tutte le share NFS su PVE1 (`backup-proxmox`, `games`, `truenas-media`).
  > 3. Sblocco automatico dei processi del kernel e completamento di `pct stop 1400`.
  > **Obiettivo**: Studiare e implementare una soluzione strutturale per disattivare/smontare automaticamente e in modo pulito le share NFS (es. tramite script di pre-shutdown Proxmox, autofs con timeout aggressivi, o systemd mount units robuste) prima che TrueNAS venga arrestato, prevenendo hang di sistema e dipendenze bloccanti in cascata.



### [ ] Generalizzazione setup_postgres_dbs.sh per integrazione in MCP Server
  > **Contesto**: Lo script `scripts/infrastructure/setup_postgres_dbs.sh` gestisce in modo procedurale e locale la creazione dei database e degli utenti PostgreSQL eseguendo comandi SQL via kubectl. Per permettere agli agenti AI di gestire in autonomia il provisioning dei database senza dipendere da script shell complessi, questo processo dovrebbe essere integrato in un tool di un MCP Server (es. estendendo l'MCP server postgres o kubernetes).
  > **Obiettivo**: Riscrivere o incapsulare la logica di creazione db/utente di `setup_postgres_dbs.sh` per renderla invocabile in modo dichiarativo e parametrizzato come tool MCP.



### [ ] Configurazione Globale Ansible (ansible.cfg root)
  > **Contesto**: L'esecuzione dei playbook Ansible dalla root del progetto fallisce se non si specificano manualmente l'inventory e il file di password del vault.
  > **Risoluzione da applicare**: Aggiornare `ansible.cfg` nella root per mappare i percorsi di default:
  > ```ini
  > [defaults]
  > inventory = ansible/inventory.ini
  > vault_password_file = .ansible/vault_pass.txt
  > ```

### [ ] Ripristino Globale Cluster Kubernetes Talos (Post-Manutenzione PVE)
- [ ] Avviare VM 2300 (`talos-cp-02`) su PVE2.
- [ ] Verificare stato del boot di Talos ed integrazione in etcd.
- [ ] Sincronizzare e stabilizzare l'intero cluster Talos (nodi CP1, CP2, CP3 e Worker).

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

### [ ] Analizzare e ottimizzare lo stato di HA (High Availability) su Proxmox VE
- [x] ~~Analizzare il comportamento del cluster HA in caso di nodo offline e configurare al meglio le politiche di fencing/watchdog per evitare che le risorse (VM 2300, etc.) rimangano bloccate in stato 'error'.~~ **Risolto architetturalmente**: disabilitato HA su Proxmox per Talos. Resilienza demandata a K8s.





## Log Management (Future Phase)

### [ ] Centrale Log (VictoriaLogs)
Implementare un sistema di aggregazione log centralizzato nel cluster per:
- **Suite ARR**: Raccolta log dai pod Radarr, Lidarr, Prowlarr e qBittorrent.
- **Configurazione**: Aggiunta log source in Grafana.

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

## [x] 🟢 COMPLETATO: Integrazione Google Antigravity & MCP [[truenas-master-mcp-integration]]
- [x] **Fase 1: Installazione Prerequisiti (Rust toolchain)**: Installare `rust` via Homebrew (`brew install rust`) e verificare cargo.
- [x] **Fase 2: Compilazione truenas-master-mcp**: Eseguire `cargo install truenas-master-mcp` e verificare il binario.
- [x] **Fase 3: Patch Energetica Electron**: (SALTATA) Evitata per preservare l'integrità della firma digitale dell'app.
- [x] **Fase 4: Configurazione MCP**: Creare `plugin.json` e aggiornare `mcp_config.json` con la configurazione di TrueNAS Master.
- [x] **Fase 5: Validazione**: Verificata con successo la connettività di rete e la chiave API tramite chiamata curl diretta.

---

## 🛠️ Automazione Declarativa Storage (TrueNAS GitOps)
- [ ] **Configurazione Automatica TrueNAS**: Progettare ed implementare un meccanismo (es. playbook Ansible o script basato sulle API di TrueNAS SCALE) per allineare ed applicare dichiarativamente i dataset ZFS e le esportazioni NFS/SMB definiti nel file `storage.json` direttamente su TrueNAS.
- [ ] **Re-ingegnerizzazione Sincronizzazione via Ansible**: Re-ingegnerizzare le procedure di sincronizzazione dello storage (attualmente basate su `sync_storage.py` ed expect script) all'interno di playbook Ansible per garantire idempotenza ed una gestione unificata e dichiarativa degli share NFS e dei mountpoint Proxmox/K8s.

## 🔧 Manutenzione Hardware & Hypervisor
- [ ] **PVE3: Migrazione da PCIe Passthrough a USB Device Passthrough**: Sostituire il passthrough intero del controller USB (PCI Device) con il passthrough di singole porte/dispositivi (USB Device) per le VM su PVE3. Questo permette a Proxmox di mantenere il controllo del controller madre, mantenendo attiva la tastiera locale ed evitando freeze in console locale durante l'autostart delle macchine virtuali.
- [ ] **PVE2: Configurazione VM da Gioco (Bazzite-NVIDIA)** [[pve2-gaming-vm-configuration]]
  - [ ] Applicare parametri kernel e caricare moduli VFIO su PVE2 host.
  - [ ] Identificare ID PCI della RTX 4060 Ti ed effettuare binding.
  - [ ] Creare VM 2500 con CPU pinning (CCD isolation) e ballooning disattivato.
  - [ ] Installare Bazzite (immagine `bazzite-nvidia`) via KVM over IP.
  - [ ] Aggiornare `rete.json` con la VM gaming e l'indirizzo IP del KVM.
  - [ ] Sincronizzare il DNS su OPNsense.
