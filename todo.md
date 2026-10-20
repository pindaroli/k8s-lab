# 🚨 ACTIVE INCIDENTS (High Priority)

## 🚀 [x] ✅ COMPLETATO: Riorganizzazione Tassonomica della Directory docker/mcp per Pattern di Packaging [[docker-mcp-taxonomy-refactoring]]
- [x] Fase 1: Creazione della Struttura di Directory Tassonomica (`registry-package`, `upstream-tracking`, `in-house`) ✅
- [x] Fase 2: Migrazione Selettiva delle 10 directory con `git mv` (Preservazione Cronologia Git) ✅
- [x] Fase 3: Riallineamento Pipeline CI/CD GitHub Actions (`.github/workflows/docker-*.yml`) ✅
- [x] Fase 4: Riallineamento Skill Onboarding, Template e Pattern di Governance (`k8s-mcp-server-onboarding`, `mcp-*-pattern`) ✅
- [x] Fase 5: Validazione Test-Driven Sintassi YAML, Integrità Path & Wiki Sync ✅

## 🚀 In Corso: Bonifica Script Obsoleti e Riallineamento Diagnostica all'Architettura Homelab Corrente [[scripts-architecture-realignment]]
- [x] Fase 1: Rimozione Script Obsoleti e One-Off (Sezioni 1 & 2 - 21 file rimossi e verificati) ✅
- [ ] Fase 2: Riallineamento `scripts/infrastructure/check_lab.py` (TrueNAS Bare-Metal `10.10.20.50`, PBS KVM `10.10.10.100`, LXC su `pve3`, rimozione `VM 1100`/`LXC 1400`)
- [ ] Fase 3: Riallineamento `scripts/kubernetes/check_k8s.py` (Rimozione namespace `"arr"` da `CRITICAL_NAMESPACES`, aggiunta `"monitoring"` e `"homepage"`)
- [ ] Fase 4: Correzione fallback `RETE_JSON` in `scripts/infrastructure/test_internet.sh` e rimozione `TRUENAS_PASS` in `scripts/storage/sync_storage.py`
- [ ] Fase 5: Rifinitura `scripts/go.py` (deduplicazione symlink `lab_mode_echo.sh`, pulizia `exclude_dirs`), header script PVE3 e riscrittura `scripts/README.md`

## 🚀 [x] ✅ COMPLETATO: Script Idempotenti di Convergenza Stato Homelab (`lab_mode_full`, `lab_mode_eco`, `lab_mode_off`) [[homelab-idempotent-mode-scripts]]
- [x] Fase 1: Creazione dei 4 Playbook Atomici Ansible (`ensure_storage_on.yml`, `ensure_storage_off.yml`, `ensure_compute_on.yml`, `ensure_compute_off.yml`) e verifica sintassi ✅
- [x] Fase 2: Creazione dei 3 Script Dichiarativi (`lab_mode_full.sh`, `lab_mode_eco.sh`, `lab_mode_off.sh`), alias `lab_mode_echo.sh` e permessi `chmod +x` ✅
- [x] Fase 3: Allineamento Script Legacy & Launcher `scripts/go.py` ✅
- [x] Fase 4: Validazione Test-Driven End-to-End, Aggiornamento `Power_Sequence.md`, `in_use_by` nei Pattern e Sync Wiki Context (`build_wiki_context.py`) ✅

## 🚀 [x] ✅ COMPLETATO: Deduplicazione Alert nelle Procedure di Automazione Gerarchiche [[automation-alerting-deduplication]]
- [x] Fase 1: Estensione del Modulo `procedure_scope.sh` con token/marker atomico di errore (`mark_error_reported`, `has_error_been_reported`, `clean_error_marker`) ✅
- [x] Fase 2: Aggiornamento della funzione `on_error()` nei 4 script shell (`startup_all_lab.sh`, `startup_from_truenas_only.sh`, `shutdown_all_lab.sh`, `shutdown_to_truenas_only.sh`) ✅
- [x] Fase 3: Validazione Test-Driven con simulazione errore gerarchico (100% superata sia annidata sia standalone) e allineamento pattern [[hierarchical-automation-alerting-pattern]] ✅

## 🚀 Pianificato: Triangolo Schede 10G SFP+ (PVE1, TrueNAS, OPNsense) & Bond LACP 802.3ad sui 3 Nodi Proxmox [[nic-10g-triangle-swap-and-proxmox-lacp-bond]]
- [ ] Fase 1: Attivazione LACP 802.3ad (`bond0` 20 Gbps con `bond0.10` -> `vmbr10` e `bond0.20` -> `vmbr20`) sui 3 nodi Proxmox (`pve1`, `pve2`, `pve3`) via OOB e Playbook Switch Extreme (`ansible/playbooks/exos_proxmox_lacp_bonds.yml`, LAG 1 `1,5`, LAG 2 `2,6`, LAG 3 `3,7`)
- [ ] Fase 2: Pre-Configurazione Software "Zero-Console" per lo scambio schede (`50-pmx-nic1/2.link` con MAC Emulex + `update-initramfs` su `pve1`; conversione `/conf/config.xml` da `oce0` a `ixl0` su `opnsense`)
- [ ] Fase 3: Spegnimento ordinato (`shutdown_all_lab.sh` + `opnsense`), scambio fisico delle 3 schede PCIe (`X710-DA4` -> `truenas`, `X710-DA2` -> `opnsense`, `Emulex OneConnect` -> `pve1`) e riaccensione (`startup_all_lab.sh`)
- [ ] Fase 4: Validazione Test-Driven End-to-End (LACP 4 gruppi `1..4` su Extreme, `ixl0` su OPNsense, 4 porte su TrueNAS, `be2net` su PVE1) e riallineamento `rete.json` / Wiki

## 🚀 [x] ✅ COMPLETATO: Migrazione Macchina OPNsense su i3-12100 con NVMe, ZFS e Emulex 10G [[opnsense-i3-12100-nvme-migration]]
- [x] Fase 1: Installazione OPNsense 26.1 (ZFS su NVMe), `if_oce_load="YES"`, VLAN 99 (`oce0_vlan99` con IP OOB di staging `192.168.100.2/24`) e attivazione SSH `root` ✅
- [x] Fase 2: Configurazione Porta 9 SFP+ di `switch-25g-server` (`192.168.2.3`) in Trunk (`BP_21` VLAN 99 `Bridge ID 1`) e collegamento cavo DAC 10G (`oce0`) agganciato a 10Gbps ✅
- [x] Fase 3: Migrazione Automatizzata dall'AI via SSH (`root@192.168.100.2`): accesso passwordless BatchMode verificato, setup gateway temp verso 192.168.100.1, installazione plugin (`os-ddclient`, `os-gdrive-backup`, `os-upnp`, `os-realtek-re`), tuning ZFS/HWP/ARC e conversione automatica di `config.xml` (`re0` WAN + `oce0` Trunk con `TRANSIT` VLAN 1 e `oce0_vlan10/20/30/99`) ✅
- [x] Fase 4: Cutover Fisico Finale (< 60s: attivazione config definitiva `192.168.100.1`/`192.168.2.254`, spostamento cavo WAN su `re0` e spegnimento vecchio Mini PC) & Validazione Test-Driven (`test_internet.sh`, `test_dns.sh`, `test_dhcp.sh`, sync `rete.json`) ✅


## 🚀 [x] ✅ COMPLETATO: Mitigazione Bitmagnet DHT Crawler, Scaling Factor & State Limiter OPNsense [[bitmagnet-dht-crawler-mitigation-and-state-limiter]]
- [x] Fase 1: Snapshot Preventivo di Sicurezza su TrueNAS SCALE (`stripe/truenas-docker@pre-bitmagnet-mitigation-2026-10-17`) ✅
- [x] Fase 2: Configurazione e Tuning Docker su TrueNAS (`DHT_CRAWLER_SCALING_FACTOR=1`, restart container `bitmagnet`) ✅
- [x] Fase 3: Creazione Regola State Limiter su OPNsense (`TRANSIT`, max 300 / max-src 300, quick, sopra Allow All Transit) ✅
- [x] Fase 4: Validazione Test-Driven End-to-End (Risoluzione DNS Unbound istantanea, WebUI Bitmagnet 200 OK, qBittorrent 30661/8080 OK, Jellyfin 8096 OK) ✅

## 🚀 [x] ✅ COMPLETATO: Controllo e Ripristino Disco mSATA / ZFS zroot di OPNsense [[opnsense-msata-zroot-disk-recovery]]
- [x] Fase 1: Backup Preventivo di Sicurezza (`config.xml` scaricato e verificato nel repository: `opnsense_backup_pre_zfs_recovery_20261016.xml`) ✅
- [x] Fase 2: Bonifica File Corrotti & Reinizializzazione RRD (rimozione `system-states.rrd`/`hosts.db`, `zpool clear zroot`, `updaterrd.php`) ✅
- [x] Fase 3: Hardening Anti-Usura SSD (Svuotamento 9.8 GB `/var/log/filter` -> 8.5K, ZFS compression LZ4 & atime off) ✅
- [x] Fase 4: Scrub ZFS Completo & Diagnostica Hardware SMART (`zpool scrub zroot` completato con 0 errori, SMART Short superato 100%, SMART Long avviato) ✅
- [x] Fase 5: Matrice di Decisione Strategica (Scenario A confermato: disco integro, nessun guasto hardware, usura fermata) ✅

## 🚀 [x] ✅ COMPLETATO: Estensione REST API arrstack-mcp per Prowlarr e qBittorrent [[arrstack-mcp-prowlarr-qbittorrent-rest-extension]]
- [x] Fase 1: Aggiornamento Codice Locale (`server.py` esteso con 4 tool Prowlarr e 9 tool qBittorrent) ✅
- [x] Fase 2: Versionamento SemVer `1.1.0` e Sincronizzazione Sorgente su TrueNAS (`10.10.20.50`) ✅
- [x] Fase 3: Rebuild Immagine Docker (`local/arrstack-mcp:1.1.0`) & Riavvio Container su TrueNAS (`mcp-arrstack`) ✅
- [x] Fase 4: Validazione Test-Driven End-to-End (Test live verificati 100% su Prowlarr e qBittorrent) ✅
- [x] Fase 5: Consolidamento Documentale & Chiusura Piano ✅

## 🚀 [x] ✅ COMPLETATO: Tool CLI Interattivo per Pulizia Selettiva Torrent su qBittorrent [[qbittorrent-selective-cleanup-tool]]
- [x] Fase 1: Creazione del Motore Core Python (`scripts/servarr/cleanup_torrents.py`) ✅
- [x] Fase 2: Creazione del Wrapper Shell Eseguibile (`scripts/servarr/cleanup_torrents.sh`) ✅
- [x] Fase 3: Validazione Test-Driven End-to-End (Unit tests helpers, CLI args, discovery `go.py`) ✅
- [x] Fase 4: Integrazione Launcher `scripts/go.py` e Consolidamento Documentale Wiki / Todo ✅

## 🚀 Pianificato: Migrazione Flotta MCP TrueNAS su CI/CD GitOps e Sanificazione Tag Immagini [[truenas-mcp-fleet-gitops-and-image-tag-sanitization]]
- [ ] Fase 1: Standardizzazione Dockerfile Streamable HTTP nel Repository (`docker/<app>/Dockerfile` & repos standalone)
- [ ] Fase 2: Configurazione e Aggiornamento Pipeline GitHub Actions (`.github/workflows/docker-*.yml`)
- [ ] Fase 3: Esecuzione CI/CD & Pubblicazione Immagini OCI su GHCR con Version Pinning SemVer
- [ ] Fase 4: Refactoring Dichiarativo del `docker-compose.yaml` di TrueNAS ed Eliminazione `build-images.sh`
- [ ] Fase 5: Rollout Dichiarativo & Test-Driven su TrueNAS SCALE (`pull && up -d`)
- [ ] Fase 6: Validazione Funzionale & Bonifica Ambientale (Prune vecchi tag `local/*`)
- [ ] Fase 7: Consolidamento Documentale, Aggiornamento Pattern e Wiki Context

## 🚀 [x] ✅ COMPLETATO: Migrazione Flotta TrueNAS Docker MCP su Standard Streamable HTTP [[truenas-mcp-fleet-streamable-http-migration]]
- [x] Fase 1: Aggiornamento Dichiarativo Immagini Docker (`docker/mcp/build-images.sh` e `docker-compose.yaml` con `--streamableHttpPath /mcp`) ✅
- [x] Fase 2: Rebuild Immagini & Sincronizzazione su TrueNAS (`10.10.20.50`) ✅
- [x] Fase 3: Rollout e Restart Atomico Stack Docker su TrueNAS (12/12 container healthy) ✅
- [x] Fase 4: Allineamento Client Antigravity (`~/.gemini/antigravity/mcp_config.json` con `serverUrl`) ✅
- [x] Fase 5: Validazione Test-Driven End-to-End (Handshake POST 200 OK & tool live call su TrueNAS, Talos, KEF, Arrstack, RAGFlow) ✅
- [x] Fase 6: Consolidamento Documentale & Knowledge Base ([[MCP_Platform]], sync wiki context) ✅

## 🚀 [x] ✅ COMPLETATO: Integrazione Bitmagnet nello Stack Docker su TrueNAS SCALE [[bitmagnet-truenas-docker-integration]]
- [x] Fase 1: Pianificazione, Scelta Parametri & Cifratura Segreto SOPS TMDb (`secrets-sops/tmdb-credentials.enc.yaml`) ✅
- [x] Fase 2: Aggiornamento Dichiarativo Repository (`servarr/truenas-docker/docker-compose.yaml` e `.env.example`) ✅
- [x] Fase 3: Preparazione Storage & Rollout su TrueNAS (`10.10.20.50`, `/mnt/stripe/truenas-docker/bitmagnet/`) ✅
- [x] Fase 4: Validazione Test-Driven (Healthcheck DB, Dozzle log audit, WebUI :3333 e Torznab caps) ✅
- [x] Fase 5: Integrazioni Finali (Indexer Torznab Prowlarr ID 15 & Card Dashboard Homepage K8s/TrueNAS) ✅


## 🚀 [x] ✅ COMPLETATO: Sviluppo Skill Classical Music Curator per Ricerca Critica e Download Assistito [[classical-music-curator-skill]]
- [x] Fase 1: Creazione Skill `.agents/skills/classical-music-curator/SKILL.md` (Gate di stop, 7 criteri e tracker opzionale) ✅
- [x] Fase 2: Registrazione Regole di Progetto in `.agents/AGENTS.md` e `GEMINI.md` ✅
- [x] Fase 3: Validazione Test-Driven End-to-End (Dry-Run su Caso d'Uso Reale senza download) ✅
- [x] Fase 4: Consolidamento Documentale & Rigenerazione Wiki Context (`build_wiki_context.py`) ✅

## 🚀 [x] ✅ COMPLETATO: Integrazione Headlamp Kubernetes Web UI via Helm [[headlamp-kubernetes-integration]]
- [x] Fase 1: Scaffolding e Configurazione Dichiarativa (`headlamp/headlamp-values.yaml`) ✅
- [x] Fase 2: Registrazione di Rete e DNS (`rete.json` & OPNsense Unbound) ✅
- [x] Fase 3: Deployment Helm della Release (`headlamp/headlamp` nel namespace `headlamp`) ✅
- [x] Fase 4: Validazione Test-Driven & Configurazione RBAC / Access Token ✅
- [x] Fase 5: Integrazione Dashboard Homepage (`homepage.yaml` e `homepage-local.yaml`) & Consolidamento Knowledge Base ✅

## 🚀 [x] ✅ COMPLETATO: Decluttering & Clusterizzazione Tassonomica Segnalibri Chrome [[chrome-bookmarks-decluttering-and-clustering]]
- [x] Fase 1: Progettazione Tassonomia, Mappatura 208 URL Unici e Approvazione Utente (Layout con Homepage/homepage-truenas + 7 cartelle) ✅
- [x] Fase 2: Creazione Nuove Cartelle Strutturali via MCP `chrome-bookmarks-mcp` (7 radice su barra + 1 su archivio + 15 sottocartelle) ✅
- [x] Fase 3: Spostamento & Ricollocazione dei 207 Segnalibri nelle Cartelle Tematiche via MCP `bookmarks_move` ✅
- [x] Fase 4: Posizionamento dei Primi 2 Elementi Diretti (`Homepage` [0], `homepage-truenas` [1]) seguiti dalle 7 cartelle (2..8) ✅
- [x] Fase 5: Bonifica Cartelle Duplicate & Nodi Ridondanti (`Imported`, `Imported (1)`, cartelle legacy svuotate `ai`, `home`, `devops`, ecc.) ✅
- [x] Fase 6: Validazione Test-Driven, Backup Post-Ristrutturazione & Rigenerazione Indice Cronologico Finale (209 segnalibri confermati) ✅

## 🚀 [x] ✅ COMPLETATO: Upgrade Risoluzione 1080p e Bonifica Libreria Blackout (1997) {tmdb-25690} [[blackout-1997-1080p-upgrade-remux]]
- [x] Fase 1: Grab Release 1080p & Download su qBittorrent (Categoria `video-filebot`) ✅
- [x] Fase 2: Ingestion & Sanificazione Multi-Versione in `/media/movies/` (FileBot AMC) ✅
- [x] Fase 3: Analisi Fonetica Tracce Audio (Whisper): accertata natura ENG/ESP dell'AVI legacy ✅
- [x] Fase 4: Bonifica Opzione 1: rimozione file SD e conservazione esclusiva release 1080p WEB-DL ✅
- [x] Fase 5: Validazione Test-Driven & Rescan Jellyfin ✅

## 🚀 [x] ✅ COMPLETATO: Tool CLI Interattivo per Pulizia Selettiva Conversazioni Antigravity [[antigravity-conversations-cleanup-tool]]
- [x] Fase 1: Creazione Directory `scripts/antigravity/` e Motore Python (`clean_conversations.py`) ✅
- [x] Fase 2: Creazione Wrapper Shell (`clean_conversations.sh`) e Integrazione Launcher `go.py` ✅
- [x] Fase 3: Validazione Test-Driven con Modalità `--dry-run` ed Eccezioni ✅
- [x] Fase 4: Consolidamento Documentale Wiki e Chiusura Piano ✅

## 🚀 In Corso: Risoluzione Timeout Startup Talos & Riallineamento Rete TrueNAS VLAN 20 [[talos-startup-and-truenas-vlan20-realign]]
- [x] Fase 1: Bonifica Hookscript Proxmox VE (`wait-for-truenas.sh` aggiornato con `10.10.20.50` su `pve1`, `pve2`, `pve3`)
- [x] Fase 2: Esecuzione Playbook Startup (`startup_from_truenas_only.yml` superato con uncordon nodi Talos)
- [x] Fase 3: Riallineamento CNPG S3 Endpoint (`postgres/cluster.yaml` applicato, WAL archiver verso TrueNAS :3900)
- [ ] Fase 4: Diagnostica e Ripristino Connettività VLAN 20 / K8s VIP `10.10.20.55:6443` (Rimandata)
- [ ] Fase 5: Consolidamento Documentale, Verifica Salute Finale CNPG e Chiusura Piano
## ✅ Completato: Migrazione FlareSolverr su TrueNAS Docker & Riconciliazione Dichiarativa K8s/Prowlarr [[flaresolverr-truenas-migration-and-declarative-sync]]
- [x] Fase 1: Installazione FlareSolverr nello Stack Docker TrueNAS (`docker-compose.yaml` su `10.10.20.50:8191`) ✅
- [x] Fase 2: Configurazione Dichiarativa di Prowlarr verso FlareSolverr (Tag `flaresolverr`, Proxy `http://flaresolverr:8191`, Indexer `FileMood`) ✅
- [x] Fase 3: Reindirizzamento K8s via Helm Chart (`charts/servarr` `external-services.yaml` e `arr-values.yaml`) ✅
- [x] Fase 4: Validazione Test-Driven End-to-End (Bypass Challenge FileMood, test DNS K8s) ✅
- [x] Fase 5: Consolidamento Documentale & Knowledge Base (Wiki, `Servarr.md`, sync context) ✅



## 🚀 In Corso / Validazione: Automazione Full Power Homelab (WoL Idempotente, Checkpoint e Alerting) [[homelab-full-power-automation]]
- [x] Fase 1: Materializzazione Piano nel Wiki (`wiki/plans/homelab-full-power-automation.md`) e Sync `todo.md`
- [x] Fase 2: Estensione `scripts/infrastructure/utils.sh` per supporto allegati log MIME ed email/telegram universale
- [x] Fase 3: Aggiornamento WoL idempotente e notifiche Telegram su `ansible/playbooks/infrastructure/startup_from_truenas_only.yml` e wrapper `.sh`
- [x] Fase 4: Creazione `ansible/playbooks/infrastructure/startup_all_lab.yml` e wrapper `scripts/infrastructure/startup_all_lab.sh`
- [x] Fase 5: Creazione `ansible/playbooks/infrastructure/shutdown_all_lab.yml` e wrapper `scripts/infrastructure/shutdown_all_lab.sh`
- [x] Fase 6: Validazione Test-Driven End-to-End, Allineamento `Power_Sequence.md` e Sync Wiki Context
- [x] Fase 7: Creazione Pattern [[hierarchical-automation-alerting-pattern]], rimozione mail di start e orchestrazione gerarchica delle notifiche
- [ ] Validazione: Ritestare `shutdown_to_truenas_only.sh` e `shutdown_all_lab.sh` (verifica alerting gerarchico e zero allarmi a video)

## 🚀 [x] ✅ COMPLETATO: Script Shell Interattivo per Benchmark OCR con Promptfoo [[promptfoo-ocr-benchmark-script]]
- [x] Fase 1: Progettazione Architettura e Scaffolding dello Script (`scripts/benchmarks/run_promptfoo_ocr.sh`) con Naming Standard ([[guidellm-report-naming-pattern]])
- [x] Fase 2: Discovery Dinamica Modelli OCR ed Endpoint da `rete.json` (`llama-server` Vulkan porta 8081 vs `ollama` porta 11434)
- [x] Fase 3: Supporto Modalità Interattiva, CLI Flags, Fixture Picker e Dry-Run
- [x] Fase 4: Validazione Test-Driven End-to-End ed Esportazione Report Multi-Formato JSON/HTML in `reports/` (100% PASS in 6s)
- [x] Fase 5: Consolidamento Documentale, Allineamento Wiki e Sincronizzazione Contesto

## 🚀 [x] ✅ COMPLETATO: Automazione e Validazione Wake-on-LAN (WoL) Homelab [[wake-on-lan-homelab-automation]]
- [x] Fase 1: Sviluppo utilità centrale zero-dipendenze [`scripts/network/wake_node.py`](file:///Users/olindo/prj/k8s-lab/scripts/network/wake_node.py) con supporto multi-subnet/VLAN 99
- [x] Fase 2: Attivazione e instradamento interfaccia L2 diretta `vlan0` (VLAN 99 OOB `192.168.100.99`) su Mac Studio (0.5 ms RTT)
- [x] Fase 3: Censimento dichiarativo del blocco `wol` in `rete.json` per tutti i nodi fisici
- [x] Fase 4: Validazione live spegnimento e accensione da freddo (S5) al 100% su `pve1`, `pve2`, `pve3` e `truenas`
- [x] Fase 5: Allineamento documentale nel piano [[wake-on-lan-homelab-automation]] e nel workflow [[Power_Sequence]]

## 🚀 [x] ✅ COMPLETATO: Installazione e Configurazione Promptfoo per Benchmark OCR, Layout e JSON su Mac [[promptfoo-ocr-benchmark-evaluation]]
- [x] Fase 1: Verifica Prerequisiti e Installazione Promptfoo su Mac (`brew install promptfoo` v0.123.1)
- [x] Fase 2: Creazione Scaffolding e Predisposizione Fixture di Test (`benchmarks/promptfoo-ocr/fixtures/`)
- [x] Fase 3: Stesura Configurazione Dichiarativa (`promptfooconfig.yaml`, `prompts/image_prompt.json`)
- [x] Fase 4: Validazione Connettività e Configurazione Vision Multimodale Nativa (Ollama Locale / Remoto)
- [x] Fase 5: Esecuzione Benchmark di Prova ed Esportazione Report in `reports/` (100% PASS in 8s)
- [x] Fase 6: Avvio Dashboard Web Interattiva (`promptfoo view`) e Allineamento Wiki

## 🚀 [x] ✅ COMPLETATO: Integrazione Sidecar llama-server Vulkan (Qwen2.5-VL-7B OCR) su LXC Ollama [[lxc-ollama-llama-ocr-qwen25-sidecar]]
- [x] Fase 1: Verifica Prerequisiti Vulkan e Preparazione Directory su CT 300
- [x] Fase 2: Installazione Binari Ufficiali Precompilati Vulkan (`llama-server`, `llama-cli`)
- [x] Fase 3: Download Modelli GGUF su TrueNAS NFS (`Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`, `mmproj-f16`)
- [x] Fase 4: Configurazione Servizio systemd (`llama-ocr.service` su porta 8081 con `/etc/default/llama-ocr`)
- [x] Fase 5: Validazione End-to-End, Test Vision OpenAI API e Coesistenza con Ollama
- [x] Fase 6: Allineamento Registri (`rete.json`) e Rigenerazione Wiki Context

## 🚀 Pianificato: Automazione Wake-on-LAN (WoL) e Accensione Remota dell'Homelab [[wake-on-lan-homelab-automation]]
- [ ] Fase 1: Scaffolding dello Script Canonico `scripts/network/wake_node.py` (Broadcast Magic Packet UDP)
- [ ] Fase 2: Censimento Dichiarativo delle Interfacce e MAC WoL in `rete.json`
- [ ] Fase 3: Aggiornamento Template Documentali (`istruzioni/interfaces_pve*.txt`)
- [ ] Fase 4: Integrazione nel Workflow di Startup del Rack nel Wiki ([[Power_Sequence]])
- [ ] Fase 5: Validazione Test-Driven & Prerequisiti BIOS/UEFI

## 🚀 Pianificato: Creazione Record DNS per Indirizzi OOB (VLAN 99)
- [ ] Fase 1: Censimento e standardizzazione degli FQDN OOB in `rete.json` (`opnsense-oob`, `pve1-oob`, `pve2-oob`, `pve3-oob`, `mac-oob` su subnet `192.168.100.0/24`)
- [ ] Fase 2: Estensione del generatore DNS `ansible/playbooks/scripts/opnsense/validate_rete_dns.py` per il parsing e l'estrazione automatica delle porte di servizio OOB
- [ ] Fase 3: Esecuzione playbook Ansible `ansible/playbooks/opnsense/opnsense_sync_dns.yml` per l'applicazione degli Host Override su Unbound DNS di OPNsense
- [ ] Fase 4: Validazione test-driven della risoluzione DNS (`dig`/`ping` verso `*-oob.pindaroli.org`) e allineamento `Network_Registry.md`

## 🚀 In Corso: Test Locale, Pipeline CI/CD GHCR, Docker TrueNAS & Widget Homepage Meross MCP [[meross-mcp-docker-validation]]
- [x] Fase 1: Test Server Meross in Locale & Validazione Credenziali (MQTT/TLS connesso con successo, scoperta presa fisica `ups` MSS310) ✅
- [x] Fase 2: Implementazione Pipeline CI/CD GitHub Actions & Release OCI `v0.1.0` su GHCR ✅
- [x] Fase 3: Configurazione Dichiarativa TrueNAS Docker (Pinning semantico `ghcr.io/pindaroli/meross-mcp:0.1.2`, divieto `:latest`, SOPS) ✅
- [x] Fase 4: Deployment e Validazione End-to-End su TrueNAS (Completato: fix telemetria `async_get_instant_metrics`, lifespan ASGI FastMCP, rilascio `v0.1.2`, test Streamable HTTP 200 OK e configurazione `serverUrl` in `mcp_config.json`) ✅
- [ ] Fase 5: Integrazione Widget Consumi su Dashboard Homepage (K8s & TrueNAS)

## 🚀 [x] ✅ COMPLETATO: Ottimizzazione e Dimensionamento al Limite Fisico di LXC Ollama su PVE3 [[lxc-ollama-hardware-limit-optimization]]
- [x] Fase 1: Ispezione e Baseline Benchmark GuideLLM su `lxc-ollama`
- [x] Fase 2: Configurazione Parametri Kernel AMDGPU su Host PVE3 (`gttsize: -1` dinamico)
- [x] Fase 3: Riconfigurazione Parametri Dimensionali di Allocazione (54 GB RAM, 20 vCPU pinned 0-19)
- [x] Fase 4: Applicazione Ottimizzazioni di Runtime Ollama (Flash Attention, KV Cache Q8, Keep Alive)
- [x] Fase 5: Validazione Empirica con GuideLLM Benchmark Post-Tuning e Ripristino GPU Eco
- [x] Fase 6: Allineamento Registri di Rete (`rete.json`) e Documentazione Wiki

## 🚀 [x] ✅ COMPLETATO: Registrazione Canonica dei Servizi Ollama in rete.json e Discovery Dinamica nei Benchmark [[ollama-rete-registry-integration]]
- [x] Fase 1: Aggiornamento Dichiarativo di `rete.json` (`services` in `nodi` e `applicazioni`)
- [x] Fase 2: Validazione Parsing Dinamico da CLI (`jq` / python)
- [x] Fase 3: Refactoring di `scripts/benchmarks/run_guidellm_benchmark.sh` (Lettura dinamica da `rete.json`)
- [x] Fase 4: Validazione Test-Driven End-to-End (Batch e Interattivo)
- [x] Fase 5: Consolidamento Documentale e Sync Wiki Context

## 🚀 [x] ✅ COMPLETATO: Script Shell Interattivo per Benchmark GuideLLM con Naming Pattern Standard [[guidellm-benchmark-script]]
- [x] Fase 1: Creazione Struttura Directory e Script Shell (`scripts/benchmarks/run_guidellm_benchmark.sh`)
- [x] Fase 2: Validazione della Modalità Dry-Run e Risoluzione Naming ([[guidellm-report-naming-pattern]])
- [x] Fase 3: Validazione Connettività e Test Interattivo
- [x] Fase 4: Esecuzione di Benchmark Reale di Prova
- [x] Fase 5: Consolidamento Documentale e Allineamento Pattern

## 🚀 [x] ✅ COMPLETATO: Automazione Startup SFP+ Porta 10 su Extreme EXOS [[exos-port10-sfp-boot-recovery]]
- [x] Fase 1: Creazione Script Locali nel Repository (`bounce_port10.py` e `autoexec.xsf`)
- [x] Fase 2: Implementazione ed Esecuzione Playbook Ansible Permanente (`exos_port10_boot_recovery.yml`)
- [x] Fase 3: Validazione Test-Driven Flash e Interprete Python su EXOS (Verificato con successo)
- [x] Fase 4: Consolidamento Documentale ([[Network_Registry]], [[2026-10-11-exos-sfp-port10-link-startup-failure]], sync wiki context)

## 🚀 [x] ✅ COMPLETATO: Creazione Progetto Git e Sviluppo MCP Server per Prese Meross [[meross-mcp-server-project]]
- [x] Fase 1: Creazione Scaffolding Progetto Git (`/Users/olindo/prj/meross-mcp/`) e Toolchain
- [x] Fase 2: Implementazione Core Client Asincrono Meross (`config.py`, `client.py`, `devices.py`)
- [x] Fase 3: Implementazione Server MCP & Tools (`server.py`) con supporto Stdio e SSE
- [x] Fase 4: Test Suite & Validazione Funzionale (Mocking pytest + smoke test)
- [x] Fase 5: Packaging Container OCI & Dockerfile
- [x] Fase 6: Integrazione in Antigravity (`~/.gemini/antigravity/mcp_config.json`) e Deployment
- [x] Fase 7: Consolidamento Documentale & Knowledge Base Wiki

## 🚀 [x] ✅ COMPLETATO: Storage NFS per Modelli Ollama su TrueNAS Stripe per LXC Ollama su PVE3 [[pve3-lxc-ollama-nfs-stripe-storage]]
- [x] Fase 1: Creazione Dataset ZFS (`stripe/ollama`) ed Export NFS su TrueNAS SCALE (`10.10.20.50`)
- [x] Fase 2: Configurazione Storage NFS (`truenas-ollama`) su Proxmox VE PVE3 (`10.10.10.31`)
- [x] Fase 3: Migrazione Dati Modelli (40 GB) e Configurazione Mount Point in `300.conf`
- [x] Fase 4: Avvio e Validazione End-to-End (`ollama list`, inferenza e recupero spazio 40 GB)
- [x] Fase 5: Consolidamento Documentale (`storage.json`, `todo.md`, sync wiki)

## 🚀 [x] ✅ COMPLETATO: Startup Homelab e Sincronizzazione Uncordon Nodi Talos [[talos-startup-sync-uncordon]]
- [x] Fase 1: Creazione Playbook Ansible di Startup Sincronizzato (`ansible/playbooks/infrastructure/startup_from_truenas_only.yml`)
- [x] Fase 2: Creazione Script Wrapper di Esecuzione (`scripts/infrastructure/startup_from_truenas_only.sh`)
- [x] Fase 3: Riallineamento a Caldo `talos-cp-03` (Uncordon con preservazione taint Control Plane Puro)
- [x] Fase 4: Validazione e Test-Driven Execution (Playbook testato al 100% con esito positivo)
- [x] Fase 5: Consolidamento Documentale & Knowledge Base ([[Power_Sequence]], `todo.md`, `GEMINI.md`)


## 🚀 In Corso: Script Controllo Aggiornamenti Immagini Docker su TrueNAS [[truenas-docker-image-updates-checker]]
- [x] Fase 1: Analisi e Definizione Contratti Dati (TrueNAS Docker Stack)
- [x] Fase 2: Implementazione Motore Core Python (`check_docker_registry_updates.py`)
- [ ] Fase 3: Implementazione Wrapper Shell Bash (`check_truenas_docker_updates.sh`)
- [ ] Fase 4: Test Operativo e Validazione End-to-End su TrueNAS
- [ ] Fase 5: Documentazione, Sync Todo e Rigenerazione Wiki Context

## 🚀 [x] ✅ COMPLETATO: Integrazione MCP Server Cloudflare (SaaS Ufficiale) [[cloudflare-mcp-integration]]
- [x] Fase 1: Generazione & Validazione Token API Cloudflare (`cfut_...` con `user:read`, `account:read`, `zone:read`, `dns:edit`).
- [x] Fase 2: Archiviazione Sicura Secret via SOPS (`secrets-sops/cloudflare-mcp-credentials.enc.yaml`).
- [x] Fase 3: Configurazione Centralizzata MCP Client (`~/.gemini/antigravity/mcp_config.json`).
- [x] Fase 4: Validazione Test-Driven End-to-End (`initialize`, `tools/list`, `whoami`, query DNS `pindaroli.org`).
- [x] Fase 5: Consolidamento Documentale & Knowledge Base ([[MCP_Platform]], `todo.md`, `GEMINI.md`).

## 🚀 [x] ✅ COMPLETATO: Pulsante di Controllo LXC Steam su Tutte le Istanze Homepage [[homepage-steam-lxc-control-button]]
- [x] Fase 1: Creazione utente `steam-ui@pve`, ruolo `SteamOperator` e token API dedicato `steam-ui@pve!btn` su PVE3 con ACL circoscritta su `/vms/301`.
- [x] Fase 2: Configurazione Service/EndpointSlice `proxmox-pve3` e middleware Traefik (`steam-api-rewrite`, `steam-api-headers`) su K8s con header injection e CORS.
- [x] Fase 3: Riprogettazione UI in pillola glassmorphism (in basso a destra, selettore `.service-card`, azione diretta Spegni verde / Avvia rosso) su `homepage.yaml`, `homepage-local.yaml` e TrueNAS bare-metal.
- [x] Fase 4: Rollout dei deployment Homepage, sincronizzazione SCP e collaudo visivo/funzionale end-to-end.
- [x] Fase 5: Consolidamento documentale ([[Homepage]], [[homepage-steam-lxc-control-button]], `GEMINI.md`).

## 🚀 [x] ✅ COMPLETATO: Integrazione Codec PyroWave su LXC Steam e Streaming su Client macOS [[steam-pyrowave-remote-play-mac]]
- [x] Fase 1: Passthrough hardware PVE3 (`card0`, `renderD128`, `/dev/snd`) in `/etc/pve/lxc/301.conf`.
- [x] Fase 2: Configurazione headless compositor `labwc` accelerato GPU a risoluzione 2K QHD (2560x1440 @ 60Hz).
- [x] Fase 3: noVNC browser console (porta 6080) e integrazione link Homepage K8s e TrueNAS.
- [x] Fase 4: Adozione Client Ufficiale Steam Desktop macOS (Beta Update) su VLAN 20 10G, streaming 2K QHD 60 FPS (latenza input < 1.4 ms).
- [x] Fase 5: Stabilizzazione runtime: server audio PulseAudio su `lxc-steam` (`auto_null.monitor`), bypass launcher 2D Bethesda (`Fallout4.exe`) ed espansione rootfs NVMe a 564 GB.

## 🚀 [x] ✅ COMPLETATO: Integrazione Dozzle nello Stack Docker su TrueNAS SCALE [[dozzle-truenas-docker-integration]]
- [x] Fase 1: Aggiornamento dichiarativo `servarr/truenas-docker/docker-compose.yaml` (immagine `v11.1.3`, porta 8888, socket :ro).
- [x] Fase 2: Sincronizzazione e rollout su TrueNAS (`10.10.20.50`), pull immagine e avvio `docker compose up -d dozzle`.
- [x] Fase 3: Validazione test-driven (porta 8888, healthcheck, ispezione live).
- [x] Fase 4: Integrazione nella dashboard Homepage e consolidamento documentale.

## 🚀 In Corso: Riprogettazione Reportistica ed Email Normalizzatori (Audio & Video) [[normalizer-reporting-and-email-redesign]]
- [x] Fase 1: Riprogettazione `utils.sh` & Supporto Email HTML nativo (`apprise -i html`).
- [x] Fase 2: Riprogettazione `normalize.sh` (Audio): esclusione `webhelp/`, cattura vero report SongKong `FixSongs*.html` ed estrazione metriche.
- [x] Fase 3: Riprogettazione `normalize-video.sh` (Video): cattura log FileBot AMC, generazione report HTML dedicato con TMDb ID/artwork/hardlink.
- [x] Fase 4: Validazione a caldo su TrueNAS, collaudo ricezione email Gmail e verifica allegati.
- [ ] Fase 5: Tag release `custom-normalizer:1.6.0` su GHCR e consolidamento documentale.

## 🚀 [x] ✅ COMPLETATO: Migrazione e Dockerizzazione arrstack-mcp su TrueNAS SCALE [[arrstack-mcp-truenas-docker-migration]]
- [x] Fase 1: Creazione Packaging Container Monorepo (`docker/arrstack-mcp/Dockerfile`, `requirements.txt`, sync src).
- [x] Fase 2: Secret Projection SOPS da `servarr-api-keys.enc.yaml` & Estensione `.env` su TrueNAS (`10.10.20.50`).
- [x] Fase 3: Aggiornamento Stack `docker/mcp/docker-compose.yaml` (porta host 8110) e script `build-images.sh`.
- [x] Fase 4: Deployment su TrueNAS SCALE bare-metal (`/mnt/stripe/truenas-docker/mcp/`) e avvio container `mcp-arrstack`.
- [x] Fase 5: Validazione Test-Driven LAN (porta 8110) e aggiornamento configurazione client `~/.gemini/antigravity/mcp_config.json`.
- [x] Fase 6: Consolidamento documentale [[MCP_Platform]], aggiornamento tracking e sync contesto.


## 🚀 [x] ✅ COMPLETATO: Migrazione Server MCP su Docker TrueNAS SCALE [[mcp-servers-truenas-docker-migration]]
- [x] Fase 1: Creazione directory `/mnt/stripe/truenas-docker/mcp/{talos,kubernetes}`, secret projection SOPS in `.env` e copia read-only config Talos/Kube (`chmod 644`).
- [x] Fase 2: Preparazione e build immagini OCI AMD64 con wrapper di rete supergateway (`truenas`, `opnsense`, `talos`, `nowaikit`, `ollama`, `github`), SSE FastMCP (`gemini-deepsearch`), Streamable HTTP Uvicorn (`kef`) e Streamable HTTP (`kubernetes`).
- [x] Fase 3: Deployment Docker Compose dello stack di 9 container in `/mnt/stripe/truenas-docker/mcp/docker-compose.yaml` su TrueNAS (`10.10.20.50`).
- [x] Fase 4: Collaudo LAN HTTP porte 8101-8109 (100% responsive) e aggiornamento configurazione client `~/.gemini/antigravity/mcp_config.json`.
- [x] Fase 5: Disabilitazione dichiarativa e non distruttiva dei pod in K8s `mcp-gateway-values.yaml` (`replicas: 0`, `enabled: false`) e consolidamento [[MCP_Platform]].

## 🚀 [x] ✅ COMPLETATO: Integrazione MCP Server per le Due Homepage (K8s & TrueNAS) [[homepage-mcp-servers-integration]]
- [x] Fase 1: Creazione bridge eseguibile `scripts/homepage-mcp/bridge.py` e collaudo test-driven JSON-RPC `initialize` e `tools/list` su entrambe le istanze.
- [x] Fase 2: Registrazione centralizzata di `homepage-k8s` e `homepage-truenas` in `~/.gemini/antigravity/mcp_config.json` con token protetto.
- [x] Fase 3: Validazione sintassi JSON e verifica caricamento tool.
- [x] Fase 4: Aggiornamento documentale [[MCP_Platform]], aggiornamento `todo.md` e sync contesto.

## 🚀 [x] ✅ COMPLETATO: Aggiornamento Homepage v2.4.0, Rimozione Git Backup & MCP Hardened [[homepage-upgrade-v2.4.0]]
- [x] Fase 0: Rimozione fisica e git dell'implementazione di failover obsoleta `servarr/compose/`.
- [x] Fase 1: Creazione Secret `homepage-mcp-secret`, upgrade manifest `homepage.yaml` (v2.4.0, MCP false) e `homepage-local.yaml` (v2.4.0, MCP true + token), rollout restart K8s e collaudo HTTP (200 OK internal, 302 external, probe MCP 200 con 7 tool).
- [x] Fase 2: Upgrade `servarr/truenas-docker/docker-compose.yaml` a `v2.4.0` con MCP enabled, pull immagine su TrueNAS, sync compose e restart container, collaudo HTTP :3000 e probe MCP 200.
- [x] Fase 3: Consolidamento documentale Wiki [[Homepage]], chiusura tracking e sync contesto.

## 🚀 [x] ✅ COMPLETATO: TrueNAS e Docker sulla VLAN 20, PBS sulla VLAN 10 [[truenas-vlan20]]
- [x] Fase 1: Piano, link e playbook `ansible/playbooks/exos_truenas_lacp_vlan20.yml`.
- [x] Fase 2: Da OOB, `vlan10` senza IP, PBS su `vlan10`, trunk sullo switch, `bond0` a `10.10.20.50`.
- [x] Fase 3: Collaudo L2 verso TrueNAS dalla VLAN 20 e verso PBS dalla VLAN 10.
- [x] Fase 4: Consumatori da `10.10.10.50` a `10.10.20.50`. PBS resta `10.10.10.100`.

## 🚀 [x] ✅ COMPLETATO: TrueNAS: LACP dei due NIC sulla VLAN 10 [[truenas-lacp-vlan10]]
- [x] Fase 1: `enp1s0f1np1` in link. FDB: porta 4 (`…f5:92`) e porta 8 (`…f5:93`).
- [x] Fase 2: Playbook `ansible/playbooks/exos_truenas_lacp_vlan10.yml`. LAG LACP porte 4+8, `primary.cfg` salvato.
- [x] Fase 3: `bond0` con `10.10.10.50`. PBS su `bond0`, raggiungibile su `10.10.10.100`.
- [x] Fase 4: Allineati `rete.json`, [[TrueNAS]] e [[Network_Registry]].

## 🚀 [x] ✅ COMPLETATO: Architettura Homelab Ibrida: Ottimizzazione Control Plane K8s & Convergenza Bare-Metal LXC su PVE3 [[pve3-hybrid-controlplane-lxc-convergence]]
- [x] Fase 0: Documentazione Wiki-first e allineamento tracking.
- [x] Fase 1: Protezione piano di rete Ingress (CoreDNS, Cloudflared, MetalLB, Traefik).
- [x] Fase 2: Evacuazione volumi stateful (VictoriaMetrics, Grafana, Ragflow-Redis) verso TrueNAS NFS csi-nfs-stripe-arr-conf.
- [x] Fase 3: Migrazione a caldo della replica PostgreSQL CNPG su talos-cp-02 (PVE2) e verifica lag a 0.
- [x] Fase 4: Evacuazione controllata dei microservizi rimanenti e flotta MCP da talos-cp-03 via drain.
- [x] Fase 5: Riconfigurazione hardware VM 3200 (talos-cp-03): downscale 2 vCPU, 4 GB RAM fissa, distacco /dev/sdb.
- [x] Fase 6: Verifica e riallineamento etcd quorum e uncordon talos-cp-03 con taint permanente Control Plane Puro.
- [x] Fase 7: Provisioning CT 300 (Ollama) su PVE3 con pinning CPU Zen 5c (8-19) e pass-through iGPU Radeon 890M.
- [x] Fase 8: Provisioning CT 301 (Gaming Direct-HDMI) su PVE3 con pinning CPU Zen 5 (0-7), Gamescope/Steam e KVM IP Streamer HDMI (VLAN 40).
- [x] Fase 9: Validazione end-to-end e consolidamento documentale su wiki/entities/Talos_Cluster.md.

## 🚀 [ ] Migrazione Definitiva Servarr: K8s -> Docker su TrueNAS [[servarr-truenas-permanent-migration]]
- [x] Fase 1: Creazione dataset e verifica ZFS Replication Tasks.
- [x] Fase 2: Configurazione Jellyfin (GPU Vega 8), qBittorrent, Prowlarr (SQLite) e Webhook Sidecar su TrueNAS Docker Compose.
- [x] Fase 3: Riconfigurazione K8s (Traefik IngressRoute per TrueNAS) e spegnimento vecchi Pod.
- [x] Fase 4: Smantellamento vecchio LXC 2200, pulizia codice/Ansible e automazione trigger qBittorrent Docker.

## 🚀 [x] ✅ COMPLETATO: Jellyfin 12.0 Clean Slate su Proxmox VE (RDNA 3.5 & NFS) [[jellyfin-12-clean-slate-rdna35]]
- [x] Fase 1: Backup di sicurezza, arresto del servizio su LXC 2200 e snapshot ZFS atomici su pve3.
- [x] Fase 2: Aggiornamento repository APT deb822 noble e installazione Jellyfin 12.0 + jellyfin-ffmpeg8.
- [x] Fase 3: Primo avvio pulito e validazione transcodifica hardware AMD Radeon 890M (VA-API HEVC 10-bit / AV1).
- [x] Fase 4: Configurazione wizard WebUI, generazione API Key e allineamento notifica Connect in Radarr.
- [x] Fase 5: Verifica healthcheck su Homepage e routing Traefik Ingress.

## 🚀 [x] ✅ RISOLTO: Bonifica e Rotazione API Key OPNsense (Leakage Mitigation)
- [x] Generare una nuova coppia di API Key su OPNsense per l'utente `root`.
- [x] Sostituire le chiavi in `ansible/vars/opnsense_secrets.yml` e cifrare il file con Ansible Vault.
- [x] Sostituire le chiavi nel file locale `ansible/OPNsense.internal_root_apikey.txt` (escluso da Git).
- [x] Verificare il funzionamento delle nuove chiavi con lo script `scripts/check_opnsense_plugins.py`.
- [x] **Leakage Risolto**: Le chiavi esposte sono state rimosse dal firewall e quelle nuove sono protette tramite cifratura con Ansible Vault.

## 🚀 [x] ✅ COMPLETATO: Migrazione Kubernetes di TrueNAS Master MCP [[truenas-master-mcp-kubernetes-migration]]
- [x] Fase 1: Fork GitHub `hongkongkiwi/truenas-master-mcp` -> `pindaroli/truenas-master-mcp` e riallineamento remotes.
- [x] Fase 2: Containerizzazione Docker, commit dei fix homelab e CI/CD GitHub Actions su GHCR.
- [x] Fase 3: Provisioning secret SOPS `truenas-mcp-credentials` in `mcp-system`.
- [x] Fase 4: Integrazione nella Project Chart Helm `mcp-gateway` via ToolHive Operator.
- [x] Fase 5: Routing Traefik IngressRoute e registrazione DNS Unbound `truenas-mcp-internal.pindaroli.org`.
- [x] Fase 6: Aggiornamento endpoint `serverUrl` in `mcp_config.json`.
- [x] Fase 7: Validazione funzionale end-to-end e consolidamento Wiki.

## 🚀 [x] ✅ COMPLETATO: Migrazione Kubernetes di OPNsense MCP Server [[opnsense-mcp-kubernetes-migration]]
- [x] Fase 1: Creazione Dockerfile monorepo `docker/opnsense-mcp/` e workflow CI per container `ghcr.io/pindaroli/opnsense-mcp:latest`.
- [x] Fase 2: Provisioning secret SOPS `secrets-sops/opnsense-mcp-credentials.enc.yaml` in `mcp-system`.
- [x] Fase 3: Integrazione server `opnsense` nella Project Chart Helm `mcp-gateway` (ToolHive stdio -> HTTP/SSE bridge :8080).
- [x] Fase 4: Configurazione routing Traefik IngressRoute e alias DNS Unbound `opnsense-mcp-internal.pindaroli.org`.
- [x] Fase 5: Aggiornamento endpoint remoto in `~/.gemini/antigravity/mcp_config.json`.
- [x] Fase 6: Validazione Test-Driven end-to-end e aggiornamento `MCP_Platform.md`.

## 🚀 [x] ✅ COMPLETATO: Migrazione a Nosmoht Talos MCP Server (Go) [[talos-mcp-go-migration]]
- [x] Fase 1: Docker Container Packaging (`docker/talos-mcp/Dockerfile` con Go binario v2.5.1, eliminazione wrapper Python).
- [x] Fase 2: Configurazione Kubernetes & Helm (`mcp-gateway` v0.2.12 con `ghcr.io/pindaroli/talos-mcp:2.5.1`).
- [x] Fase 3: Audit Client e Allineamento Nomi Tool (matrice mapping).
- [x] Fase 4: Validazione Test-Driven end-to-end (probe `server/discover`, handshake `initialize`, `talos_version`).

## 🚀 [x] ✅ ARCHIVIATO: Migrazione Kubernetes di Talos MCP Server (Python Legacy) [[talos-mcp-kubernetes-migration]]
- [x] Fase 1: Creazione Dockerfile monorepo `docker/talos-mcp/`, wrapper `talos_mcp_wrapper.py` e workflow CI per container `ghcr.io/pindaroli/talos-mcp:latest`.
- [x] Fase 2: Provisioning secret SOPS `secrets-sops/talos-mcp-credentials.enc.yaml` in `mcp-system`.
- [x] Fase 3: Integrazione server `talos` nella Project Chart Helm `mcp-gateway` (ToolHive stdio -> HTTP/SSE bridge :8080 con Archetipo 2 Kubelet volume secret projection).
- [x] Fase 4: Configurazione routing Traefik IngressRoute e alias DNS Unbound `talos-mcp-internal.pindaroli.org`.
- [x] Fase 5: Aggiornamento endpoint remoto in `~/.gemini/antigravity/mcp_config.json`.
- [x] Fase 6: Validazione Test-Driven end-to-end e aggiornamento `MCP_Platform.md`.

## 🚀 [x] ✅ COMPLETATO: Migrazione Kubernetes di Gemini DeepSearch MCP [[gemini-deepsearch-mcp-kubernetes-migration]]
- [x] Fase 1: Consolidamento codice & Dockerfile Monorepo `docker/gemini-deepsearch-mcp/` (fix inline return answer/sources) e workflow CI.
- [x] Fase 2: Provisioning secret SOPS `secrets-sops/gemini-deepsearch-credentials.enc.yaml` (`GEMINI_API_KEY`) in `mcp-system`.
- [x] Fase 3: Integrazione server `gemini-deepsearch` nella Project Chart Helm `mcp-gateway` (ToolHive stdio -> HTTP/SSE bridge :8080 con Archetipo 1).
- [x] Fase 4: Configurazione routing Traefik IngressRoute e alias DNS Unbound `deepsearch-mcp-internal.pindaroli.org`.
- [x] Fase 5: Aggiornamento endpoint remoto in `~/.gemini/antigravity/mcp_config.json`.
- [x] Fase 6: Validazione Test-Driven end-to-end e aggiornamento `MCP_Platform.md`.

## 🚀 [x] ✅ COMPLETATO: Migrazione Kubernetes di Kubernetes MCP Server [[kubernetes-mcp-server-kubernetes-migration]]
- [x] Fase 1: Creazione template Helm dichiarativo RBAC (`rbac.yaml`) e binding `kubernetes-mcp-sa` $\rightarrow$ `cluster-admin`.
- [x] Fase 2: Integrazione server `kubernetes` nella Project Chart Helm `mcp-gateway` (chart v0.2.7, ToolHive stdio -> HTTP/SSE bridge :8080).
- [x] Fase 3: Configurazione routing Traefik IngressRoute e censimento DNS Unbound `kubernetes-mcp-internal.pindaroli.org`.
- [x] Fase 4: Aggiornamento endpoint remoto `serverUrl` in `~/.gemini/antigravity/mcp_config.json`.
- [x] Fase 5: Validazione Test-Driven end-to-end e non-regressione su tutta la flotta MCP.
- [x] Fase 6: Aggiornamento `MCP_Platform.md` e consolidamento Wiki.

## 🚀 [x] ✅ COMPLETATO: Migrazione Kubernetes di Ollama MCP Server [[ollama-mcp-kubernetes-migration]]
- [x] Fase 1: Creazione packaging Monorepo (`docker/ollama-mcp/Dockerfile`) e workflow CI/CD GitHub Actions.
- [x] Fase 2: Configurazione ascolto di rete del demone Ollama su Mac Studio (VLAN 20: `0.0.0.0:11434`).
- [x] Fase 3: Integrazione server `ollama` nella Project Chart Helm `mcp-gateway` (bump `Chart.yaml` v0.2.8 e valori).
- [x] Fase 4: Routing Traefik IngressRoute, censimento in `rete.json` e registrazione DNS Unbound OPNsense.
- [x] Fase 5: Aggiornamento endpoint remoto `serverUrl` in `~/.gemini/antigravity/mcp_config.json`.
- [x] Fase 6: Validazione Test-Driven end-to-end e consolidamento Wiki (`MCP_Platform.md`).
## 🚀 [x] ✅ COMPLETATO: Architettura UPS NUT Distribuita (TrueNAS Master & Proxmox PVE1/2/3 Client) [[nut-distributed-ups-orchestration]]
- [x] Fase 1: Bonifica totale di PVE1 (stop nut-server/driver, rimozione udev rule, eliminazione file server, purge nut-server).
- [x] Fase 2: Configurazione e attivazione TrueNAS Master (API midclt ups.update, extrausers pvemon, rmonitor: true, HOSTSYNC 120, ignorelb con soglia software 40%).
- [x] Fase 3: Rollout distribuito client su PVE1, PVE2, PVE3 (installazione nut-client, upsmon.conf parallelo, script atomico con polling attivo qm status max 45s).
- [x] Fase 4: Validazione test-driven end-to-end (upsc da PVE1/2/3 verso TrueNAS, verifica live 100% ok).



## 🚀 [ ] Automazione Rilevazione Dati SMART via Ansible [[ansible-smart-telemetry-integration]]
- [ ] Fase 1: Sviluppo playbook `ansible/playbooks/monitoring/collect_smart_data.yml` con scansione dinamica dischi (`smartctl --scan-open`).
- [ ] Fase 2: Estrazione e parsing JSON metriche S.M.A.R.T. per drive SATA (HDD/SSD) e NVMe su TrueNAS e nodi Proxmox.
- [ ] Fase 3: Logica di valutazione soglie critiche (settori riallocati, pending, temperatura, usura NVMe) e generazione report unificato.
- [ ] Fase 4: Integrazione opzionale per inoltro telemetrie verso Scrutiny (InfluxDB) o esecuzione via Semaphore (`ansible-engine`).

## 🚀 [x] ✅ COMPLETATO: Estrazione e Normalizzazione Documentazione OPNsense 26.1 per RAGFlow [[opnsense-documentation-extraction-and-ragflow]]
- [x] Fase 1: Sviluppo script `scripts/ragflow/extract_opnsense_docs.py` con motore di risoluzione link semantici (`:doc:`, `:ref:`) e convertitore reST -> Markdown.
- [x] Fase 2: Esecuzione test-driven su campioni complessi (`firewall.rst`, `aliases.rst`, `how-tos/wireguard-client.rst`).
- [x] Fase 3: Estrazione completa del corpus OPNsense 26.1 (421 documenti Markdown) e generazione `SUMMARY.md`.
- [x] Fase 4: Standardizzazione Text-First RAGFlow (zero rumore OCR, allineato a TrueNAS) e aggiornamento `wiki/entities/OPNsense.md`.

## 🚀 [ ] Out-of-Band Automation Engine: LXC su TrueNAS NFS (`oliraid`) + Semaphore + MCP Gateway [[out-of-band-automation-engine]]
### [ ] PARTE 1: PIANO PRINCIPALE (Parent Plan)
- [ ] Fase 1: Creazione dataset TrueNAS `oliraid/pve-shared-lxc` (ZFS Special VDEV 64K, recordsize 64K, atime=off, xattr=sa, lz4), export NFS e registrazione `truenas-nfs` su Proxmox VE.
- [ ] Fase 2: Provisioning LXC 200 (`ansible-engine`) unprivileged con nesting su storage `truenas-nfs`, IP `10.10.10.60/24`, registrazione su Proxmox HA Manager.
- [ ] Fase 3: Hardening LXC, creazione utente `semaphore`, virtualenv `/opt/ansible-runtime/venv`, collezioni Ansible e chiavi SSH passwordless.
- [ ] Fase 4: Installazione binario Semaphore, configurazione BoltDB `/opt/semaphore/database.bolt`, systemd service e primo avvio.
- [ ] Fase 5: Collaudo, acceptance test (verifica I/O Special VDEV SSD, test migrazione HA `pct migrate 200 pve2 --restart`), aggiornamento `rete.json` e `storage.json`.

### [ ] PARTE 2: SOTTOPIANO SPECIFICO (K8s MCP Gateway — Modello 3 Agile)
- [ ] Sottofase 1: Implementazione FastMCP in `scripts/semaphore-mcp/server.py`.
- [ ] Sottofase 2: Provisioning secret SOPS `semaphore-mcp-credentials` in `mcp-system`.
- [ ] Sottofase 3: Estensione `helm-charts/mcp-gateway` (ConfigMap mount `server.py`, bump versione semantica `Chart.yaml`, deploy `helm upgrade`).
- [ ] Sottofase 4: Esposizione Traefik IngressRoute `https://semaphore-mcp-internal.pindaroli.org/mcp` e configurazione client `mcp_config.json`.
- [ ] Sottofase 5: Validazione end-to-end e test del workflow agile (modifica codice -> reload in 2s).

## 🚀 [ ] Sincronizzazione & Allineamento TrueNAS NFS con storage.json [[truenas-storage-json-sync]]
- [x] Analizzare discrepanze e duplicazioni tra TrueNAS e `storage.json`.
- [ ] Riconciliare e snellire `storage.json` come Source of Truth per rimuovere duplicazioni e disallineamenti.
- [ ] Sviluppare Playbook Ansible per allineare ed applicare dichiarativamente le share NFS su TrueNAS da `storage.json` via REST API v2 (`/api/v2.0/sharing/nfs`).
- [ ] Verificare conformità permessi e maproot (`chmod 777`, `olindo:k8s`, `maproot_user="root"`, `maproot_group="wheel"`).

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

## 🚀 [x] ✅ COMPLETATO: RAGFlow Enterprise Deployment Plan [[ragflow-enterprise-deployment]]
### [x] FASE 1: Storage & Credenziali Garage S3 (TrueNAS)
- [x] Creazione bucket `ragflow-docs` via Garage CLI su TrueNAS.
- [x] Generazione chiave API `ragflow-key` e assegnazione permessi Read/Write.
- [x] Verifica raggiungibilità porta 3900 e config `addressing_style: path`.

### [x] FASE 2: Segreti SOPS & Namespace K8s
- [x] Creazione namespace `ragflow-system`.
- [x] Creazione template e cifratura `secrets-sops/ragflow-secrets.enc.yaml` e `secrets-sops/ragflow-db-secrets.enc.yaml`.
- [x] Sincronizzazione secret `ragflow-secrets` e `garage-creds` in `ragflow-system`.

### [x] FASE 3: Cluster PostgreSQL HA via CloudNativePG (Consolidato su postgres-main)
- [x] Ripristino e consolidamento su `postgres-main` (2 repliche sincronizzate su NVMe locale `local-postgres`).
- [x] Managed role `ragflow` riconciliato con secret SOPS e database `rag_flow` creato e inizializzato.
- [x] Validazione salute cluster (Healthy state, 2/2 ready, test endpoint RW).

### [x] FASE 4: Helm Chart & Core RAGFlow
- [x] Creazione file di override `ragflow/values-hybrid.yaml` (sanitizzato per GitOps).
- [x] Integrazione CNPG `postgres-main`, Garage S3, Infinity vector engine e Redis.
- [x] Installazione release Helm `ragflow` (v0.27.1) nel namespace `ragflow-system`.
- [x] Validazione stato Pod (1/1 Running per `ragflow`, `ragflow-infinity-0`, `ragflow-redis-0`).

### [x] FASE 5: Routing Ingress Traefik Split-Horizon & Dashboard
- [x] Creazione manifest `traefik/ragflow-ingress-routes.yaml` (Port 80 backend).
- [x] Configurazione route esterna (`ragflow.pindaroli.org` con OAuth2) e interna (`ragflow-internal.pindaroli.org`).
- [x] Aggiornamento `rete.json` con alias DNS.
- [x] Integrazione in `homepage/homepage.yaml` e rollout restart eseguito.

### [x] FASE 6: Test-Driven Verification & Database Tables
- [x] Test connettività HTTP (Nginx 200 OK).
- [x] Inizializzazione tabelle ORM Peewee completata con successo su `postgres-main` (database `rag_flow`).
- [x] Verifica assenza plaintext secrets su Git e archiviazione piano nel Wiki.

## 🚀 [x] ✅ COMPLETATO: Integrazione RAGFlow MCP Server per Antigravity [[ragflow-antigravity-mcp-integration]]
### [x] FASE 1: Generazione Credenziali & Endpoint RAGFlow
- [x] Generazione API Key utente su RAGFlow (`ragflow-internal.pindaroli.org`).
- [x] Archiviazione sicura dell'API Key in SOPS (`secrets-sops/ragflow-mcp-secrets.enc.yaml`).
- [x] Validazione raggiungibilità endpoint REST API (`/api/v1/datasets`, `/api/v1/retrieval`).

### [x] FASE 2: Sviluppo del Server MCP (`scripts/mcp/ragflow_mcp_server.py`)
- [x] Implementazione server FastMCP (tools: `ragflow_list_datasets`, `ragflow_search`, `ragflow_ask_assistant`, `ragflow_get_document_chunks`).

### [x] FASE 3: Registrazione & Configurazione MCP in Antigravity
- [x] Registrazione entry in `mcpServers` e definizione schema tool (`ragflow-local`).
- [x] Validazione caricamento MCP Server.

### [x] FASE 4: Test-Driven Verification & Test RAG
- [x] Test recupero semantico dal dataset RAGFlow e validazione citazioni.

## 🚀 [x] ⏹️ ARCHIVIATO / OBSOLETO: Integrazione Suite Server MCP Standard [[mcp-servers-suite-integration]]
- [x] **Dichiarato Obsoleto (2026-09-10)**: 
  - GitHub MCP è già operativo in K8s via ToolHive (`github-mcp-internal.pindaroli.org`).
  - Filesystem e Fetch sono nativi in Antigravity (`view_file`, `read_url_content`).
  - Brave Search è superato da `gemini-deepsearch` su K8s con grounding Google Gemini.
  - PostgreSQL e altri server futuri seguono lo standard in-cluster [[k8s-mcp-server-onboarding]].
- [x] ~~Fase 1: MCP Server Filesystem~~ (Annullato: nativo in Antigravity).
- [x] ~~Fase 2: MCP Server Git~~ (Annullato: gestito via shell/tool nativi).
- [x] ~~Fase 3: MCP Server Fetch~~ (Annullato: nativo in Antigravity).
- [x] ~~Fase 4: MCP Server Puppeteer~~ (Annullato: non prioritario).
- [x] ~~Fase 5: MCP Server Brave Search~~ (Annullato: sostituito da Gemini DeepSearch K8s).
- [x] ~~Fase 6: MCP Server SQLite~~ (Annullato: nessun target DB specifico attivo).
- [x] ~~Fase 7: MCP Server PostgreSQL~~ (Annullato: demandato a onboard K8s dedicato).
- [x] Fase 8: MCP Server GitHub (Completato: attivo su K8s via ToolHive).

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


## [x] 🟢 COMPLETATO: Sostituzione Switch Core ONTi 10G con Extreme Networks X620-X10 [[plan-switch-onti-to-extreme-migration]] (COMPLETED 2026-08-06)
- [x] Configurazione EXOS CLI via SSH su switch Extreme (`192.168.2.1`): VLAN 10, 20, 30, 99, IP SVIs (`192.168.2.1`, `10.10.10.1`, `10.10.20.1`), Default Route (`192.168.2.254`), Bootprelay e DNS Client.
- [x] Impostazione Porta 7 (Access VLAN 10 Server) e Porta 8 (Access VLAN 20 Client).
- [x] Aggiornamento `rete.json` con `extreme` attivo (`192.168.2.1`) e `switch10g` dismesso.
- [x] Sincronizzazione script repository (`common.py`, `test_internet.sh`, `test_dns.sh`, `test_network_configs.py`).
- [x] Validazione automatica superata (`validate_network.py` 100% OK) e aggiornamento contesto Wiki (`build_wiki_context.py`).

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

## [ ] Bonifica Database & Ruolo orfano lidarr_classic su postgres-main
- [ ] Identificare il pod primario di `postgres-main` nel namespace `cnpg-system`.
- [ ] Verificare l'assenza di dati/tabelle: `\c lidarr_classic` -> `\dt`.
- [ ] Eseguire l'eliminazione controllata: `DROP DATABASE IF EXISTS lidarr_classic;` e `DROP ROLE IF EXISTS lidarr_classic;`.
- [ ] Validare con `\l` e `\du` che non vi siano residui orfani.

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

### [x] ✅ COMPLETATO: Upgrade Radarr a v6.3.0.10514 [[radarr-upgrade-6.3.0]]
- [x] **Fase 1: Backup Preventivo**
  - [x] Eseguire backup Velero: `velero backup create backup-pre-radarr-upgrade-6.3.0-$(date +%F) --include-namespaces arr --wait`
- [x] **Fase 2: Modifica Configurazione**
  - [x] Aggiornare `servarr/arr-values.yaml`
- [x] **Fase 3: Deploy & Verifiche**
  - [x] Eseguire dry-run e deploy
  - [x] Validare pod e log (Pod `servarr-radarr` 2/2 Running con `ghcr.io/hotio/radarr:release-6.3.0.10514`)
  - [x] Controllare migrazioni database PostgreSQL

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

## qBittorrent Exporter Sidecar & Monitoring

### [ ] Integrazione Sidecar qBittorrent Exporter & Scraping VictoriaMetrics [[qbittorrent-exporter-sidecar-integration]]
- [ ] **Fase 1: Analisi e Selezione Immagine Exporter (Risoluzione Bug Auth 204)**
  - [ ] Verificare il fallimento del login di `ghcr.io/martabal/qbittorrent-exporter:v1.12.1` dovuto al codice `HTTP 204 No Content` di qBittorrent 5.2.x.
  - [ ] Individuare o compilare una versione aggiornata/fork dell'exporter (o container custom) che supporti HTTP 204 e il cookie `QBT_SID_<PORT>`.
- [ ] **Fase 2: Standardizzazione nel Chart Helm (`pindaroli-arr-helm`)**
  - [ ] Verificare o estendere il template `charts/servarr/templates/qbittorrent/` con il supporto sidecar o parametrizzazione dedicata per l'exporter delle metriche.
  - [ ] Verificare l'esposizione della porta `metrics` (8090) nel Service `servarr-qbittorrent-web` e la risorsa `VMServiceScrape` (`monitoring.yaml`).
  - [ ] Incrementare la versione del chart (`Chart.yaml`) secondo SemVer.
- [ ] **Fase 3: Configurazione Cluster & GitOps (`k8s-lab`)**
  - [ ] Aggiornare `servarr/arr-values.yaml` con l'immagine corretta, secret credentials (`servarr-api-keys`), porte e configurazioni.
  - [ ] Verificare la Custom Resource `VMServiceScrape` `servarr-qbittorrent-metrics` nel namespace `arr`.
- [ ] **Fase 4: Deploy & Validazione Test-Driven**
  - [ ] Eseguire il deploy via Helm: `helm upgrade --install servarr charts/servarr -f ../k8s-lab/servarr/arr-values.yaml -n arr`.
  - [ ] Verificare che il container sidecar sia in stato Running senza errori nei log.
  - [ ] Eseguire test di scraping dell'endpoint `/metrics` da Pod interno.
  - [ ] Verificare la rilevazione del target in VictoriaMetrics (`vmagent`) e la visualizzazione su Grafana.

## MinimServer su TrueNAS

### [x] Spostamento di MinimServer da Kubernetes a Docker Compose su TrueNAS [[minimserver-truenas-migration]]
- [x] Copia della config in `/mnt/stripe/truenas-docker/minimserver` e avvio con `network_mode: host`.
- [x] Traefik verso `10.10.10.50:9790`, homepage Kubernetes e homepage TrueNAS.
- [x] `minimserver.enabled: false` e Helm upgrade della release `servarr` (revisione 178).

---

## Hardening Resilienza Bare-Metal (DeepSearch Insights)

### [ ] Networking L2 & Kube-VIP (Anti-Phantom VIP)
- [ ] Controllare e disabilitare `macfilter=0` sulle interfacce di rete (net0) delle VM Talos su Proxmox (PVE1, PVE3).
- [ ] Aggiungere env vars a kube-vip per persistenza ARP: `vip_preserve_on_leadership_loss=true`, `vip_arpRate=6000`.

### [ ] Ottimizzazione CNPG & Ingress
- [ ] Creare PodDisruptionBudget (PDB) per `postgres-main` con `maxUnavailable: 1`.
- [ ] Valutare impostazione `failoverDelay: 0` nella spec del Cluster CNPG per failover immediato.
- [ ] Implementare regole di "Retry" sull'Ingress Traefik per mascherare i drop TCP (5-10s) durante il failover L2 del VIP.

## Critical Actions



### [x] ✅ COMPLETATO: Proxmox Talos Intelligent Watchdog (Ansible OOB Self-Healing) [[proxmox-talos-watchdog]]
- [x] Sviluppato ruolo Ansible `proxmox_talos_watchdog` per il deploy dello script in `/usr/local/bin/talos-watchdog.sh`.
- [x] Configurato cronjob in `/etc/cron.d/talos-watchdog` (in esecuzione ogni 3 minuti) su `pve1`, `pve2` e `pve3`.
- [x] Implementata la logica di verifica a 3 livelli (check VM status -> check ping Talos -> check ping Gateway L3 10.10.20.1) per prevenire boot loop durante disconnessioni dello switch.
- [x] Eseguito il deploy con successo su tutti e 3 gli ipervisori Proxmox.

### [ ] Security & Automation
- [x] **Attivazione Licenza SongKong Premium (Normalizzatore Audio)**: [[songkong-normalizer-integration]] (Secret `songkong-license` montato nel namespace `arr`, notifiche Apprise e immagine 1.2.0 in produzione).
- [x] **Disaccoppiamento Radarr / FileBot e Normalizzatore Video 1.3.0**: [[radarr-video-normalizer-decoupling]] (Rimozione trigger automatico Radarr, introduzione categoria `video-filebot`, fix runtime Java/licenza non-root e immagine `custom-normalizer:1.3.0`).
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

### [ ] Migrazione Dataset di Sistema TrueNAS (ix-apps e .ix-virt) su oliraid
  > **Contesto**: Attualmente le cartelle di sistema di TrueNAS (`ix-apps` e `.ix-virt`) risiedono sul pool NVMe `stripe`. Questo "sporca" il pool ad alte prestazioni con file temporanei (cataloghi App, Docker images) che complicano inutilmente le procedure di backup e restore ricorsivo ZFS, mischiandole ai dischi essenziali (come la VM Talos). Inoltre, si verifica la **"stranezza ZFS"** dove le policy di snapshot desincronizzano le cartelle padre (es. `k8s-runner-1` ferma a Marzo) dalle cartelle figlio (es. `k8s-runner-1.block` aggiornata a Luglio), rendendo di fatto impossibili i ripristini ricorsivi completi con `-R`.
  > **Obiettivo 1**: Spostare l'App Pool e l'ambiente Virtualization di default su `oliraid`. In questo modo `stripe` rimarrà dedicato al 100% solo ed esclusivamente ai dataset ad alte prestazioni (`k8s-arr`, `qb_temp`) e ai dischi Zvol delle VM, rendendo i backup chirurgici ed esenti da errori ricorsivi.
  > **Obiettivo 2**: Investigare la retention policy degli snapshot automatici su TrueNAS per forzare l'allineamento degli snapshot gerarchici (Padre-Figlio) in modo da garantire che il flag `-R` funzioni sempre senza trovare "buchi" temporali nei dataset annidati.



### [x] 🗑️ OBSOLETO: Generalizzazione setup_postgres_dbs.sh (Dismesso a favore di CloudNativePG dichiarativo)
  > **Stato (2026-09-26)**: Lo script imperativo `setup_postgres_dbs.sh` è stato formalmente dismesso e rimosso. La gestione dei database e dei ruoli avviene esclusivamente in modo dichiarativo tramite `cluster.yaml` (`spec.managed.roles`) e secret protetti da SOPS.



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

## 🚀 [ ] Integrazione Gestione Scaling App su Homepage Local via OliveTin (Iframe) [[homepage-app-scaling-buttons]]
- [ ] Fase 1: Deployment OliveTin e configurazione Webhook n8n.
- [ ] Fase 2: Aggiunta dell'Iframe OliveTin nella dashboard di Homepage.
