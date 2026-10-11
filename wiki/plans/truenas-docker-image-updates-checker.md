---
title: "Script di Controllo Aggiornamenti Immagini Docker su TrueNAS"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-07
tags:
  - "#truenas"
  - "#docker"
  - "#maintenance"
  - "#scripts"
---

# Script di Controllo Aggiornamenti Immagini Docker su TrueNAS

Questo piano definisce la progettazione, l'implementazione e la validazione test-driven dello script di monitoraggio e audit delle versioni delle immagini container in esecuzione sullo stack Docker di TrueNAS SCALE (`10.10.20.50`), offrendo un'esperienza d'uso e un output tabulare speculari a quanto già operativo per il cluster Kubernetes tramite `scripts/kubernetes/check_nova_updates.sh`.

---

## 🎯 Obiettivi & Perimetro

1. **Equivalenza Funzionale con Kubernetes (`check_nova_updates.sh`)**:
   - Fornire un comando shell eseguibile da workstation macOS (`./scripts/truenas/check_truenas_docker_updates.sh`) in grado di auditare rapidamente tutti i container Docker in esecuzione o dichiarati su TrueNAS.
   - Restituire una tabella ordinata e leggibile a colpo d'occhio:
     `CONTAINER / IMMAGINE | VERSIONE IN PRODUZIONE | VERSIONE STABILE NEI REGISTRI | STATO (⚠️ Aggiornamento disponibile)`.

2. **Sicurezza e Zero-Impatto Operativo (100% Read-Only)**:
   - Rispetto ferreo del **Mandato Autenticazione Passwordless SSH** (`ssh -o BatchMode=yes olindo@10.10.20.50`).
   - Nessuna modifica, pull distruttivo o riavvio dei carichi di produzione durante la fase di scansione.

3. **Copertura Multi-Registry e Multi-Formato**:
   - Supporto nativo per registri OCI standard (Docker Hub, GitHub Container Registry `ghcr.io`, LinuxServer `lscr.io`, Quay).
   - Gestione intelligente dei diversi schemi di tag:
     - Tag SemVer semantici standard (es. `v11.2.0`, `2.2`, `1.6.0`).
     - Tag complessi/ibridi LinuxServer (es. `12.0ubu2604-ls48`, `5.2.3_v2.0.13-ls468`).
     - Tag statici come `:latest` (verifica digest OCI remoto rispetto al digest locale presente sul daemon).
     - Riconoscimento trasparente delle immagini interne/locali (`local/*`) marchiate come `[Locale / Build interna]`.

4. **Architettura Leggera (Zero Dipendenze Esterne)**:
   - Motore di parsing in Python 3 standard library (`urllib.request`, `json`, `re`, `subprocess`, `ssl`): nessun requisito di installazione di pacchetti pip o binari aggiuntivi.

---

## 📋 FASI OPERATIVE & PROTOCOLLO TEST-DRIVEN

### 🔍 FASE 1: Analisi e Definizione Contratti Dati (TrueNAS Docker Stack)

#### Obiettivo
Mappare con precisione tutti i carichi Docker presenti su TrueNAS e definire le modalità di estrazione dei metadati di runtime (container attivi) e dichiarativi (file Docker Compose).

#### Azioni
1. Verificare l'estrazione non invasiva dei container attivi via SSH:
   `ssh -o BatchMode=yes olindo@10.10.20.50 "sudo -n docker ps --format '{{json .}}'"`
2. Identificare i percorsi dei file `docker-compose.yaml` su TrueNAS:
   - Media stack: `/mnt/stripe/truenas-docker/docker-compose.yaml`
   - MCP stack: `/mnt/stripe/truenas-docker/mcp/docker-compose.yaml`
3. Catalogare le famiglie di registry e repository utilizzati:
   - Docker Hub (`amir20/dozzle`, `dxflrs/garage`, `minimworld/minimserver`, `alpine`)
   - GHCR (`ghcr.io/gethomepage/homepage`, `ghcr.io/pindaroli/custom-normalizer`, `ghcr.io/containers/kubernetes-mcp-server`)
   - LinuxServer (`lscr.io/linuxserver/jellyfin`, `lscr.io/linuxserver/qbittorrent`, `lscr.io/linuxserver/prowlarr`)
   - Locali (`local/arrstack-mcp`, `local/ragflow-mcp`, `local/talos-mcp`, etc.)

#### 🛑 Checkpoint & Test di Verifica FASE 1
- [x] Connessione SSH passwordless a `10.10.20.50` con comando di test read-only con esito 0.
- [x] Raccolta completa del JSON array dei container attivi e verifica presenza di tutti i campi necessari (`Names`, `Image`, `ImageID`).

---

### 🐍 FASE 2: Implementazione Motore Core Python (`check_docker_registry_updates.py`) [COMPLETATA ✅]

#### Obiettivo
Sviluppare il modulo di interrogazione OCI Distribution V2 e formattazione tabulare in `scripts/truenas/utils/check_docker_registry_updates.py`.

#### Azioni
1. [x] Creare la directory di supporto `scripts/truenas/utils/`.
2. [x] Implementare la classe/modulo di interazione con le Registry OCI:
   - Negoziazione automatica del token Bearer tramite endpoint `Www-Authenticate`.
   - Recupero lista tag (`/v2/<repo>/tags/list`) per Docker Hub, GHCR e `lscr.io`.
   - Recupero manifest/digest (`HEAD /v2/<repo>/manifests/<tag>`) con accept header OCI/Docker (`application/vnd.docker.distribution.manifest.v2+json`, `application/vnd.oci.image.index.v1+json`).
3. [x] Implementare il motore di comparazione versioni:
   - Algoritmo di parsing e ordinamento SemVer che ignora tag di test (`pr-*`, `test-*`, `nightly`, `beta`, `rc`) ed estrae la versione stabile più alta.
   - Per tag `:latest`: comparazione tra il digest locale (da `docker inspect` o `docker ps`) e il digest remoto.
   - Per immagini `local/*`: marcatura immediata senza chiamate di rete.
4. [x] Implementare la formattazione tabulare uniforme a Nova:
   - Intestazioni allineate (`CONTAINER / IMMAGINE`, `VERSIONE IN PRODUZIONE`, `VERSIONE STABILE NEI REGISTRI`).
   - Evidenziazione aggiornamenti: `⚠️ (Aggiornamento disponibile)`.

#### 🛑 Checkpoint & Test di Verifica FASE 2
- [x] Test unitario locale su immagini campione (Docker Hub, GHCR, LinuxServer, `latest`, `local`).
- [x] Verifica del corretto parsing SemVer senza eccezioni o crash con input malformati o tag non standard.

---

### 🐚 FASE 3: Implementazione Wrapper Shell Bash (`check_truenas_docker_updates.sh`)

#### Obiettivo
Creare l'entry point utente `scripts/truenas/check_truenas_docker_updates.sh`.

#### Azioni
1. Implementare lo script bash con gestione delle opzioni CLI:
   - Default: interroga i container attualmente in esecuzione (`docker ps`).
   - Opzione `--compose`: interroga i file docker-compose presenti su TrueNAS.
   - Opzione `--all`: combina container attivi e dichiarati nei compose.
   - Opzione `--json`: delega a Python l'emissione JSON anziché tabella.
2. Integrare il controllo di raggiungibilità host `10.10.20.50` e verifica chiave SSH.
3. Rendere lo script eseguibile (`chmod +x scripts/truenas/check_truenas_docker_updates.sh`).

#### 🛑 Checkpoint & Test di Verifica FASE 3
- [ ] Esecuzione `scripts/truenas/check_truenas_docker_updates.sh --help` con visualizzazione guida e sintassi.
- [ ] Verifica gestione errori nel caso TrueNAS non sia raggiungibile o SSH fallisca.

---

### 🧪 FASE 4: Test Operativo e Validazione End-to-End su TrueNAS

#### Obiettivo
Collaudare lo script completo contro l'infrastruttura reale TrueNAS SCALE.

#### Azioni
1. Eseguire `./scripts/truenas/check_truenas_docker_updates.sh` da terminale macOS.
2. Validare la coerenza della tabella restituita:
   - Verifica delle versioni segnalate per Jellyfin, qBittorrent, Dozzle, Homepage, Scrutiny.
   - Verifica corretta classificazione dei server MCP locali (`local/*`).
3. Audit di non interferenza: assicurarsi che nessun container TrueNAS abbia subito riavvii o variazioni di stato (`docker ps` status inalterato).

#### 🛑 Checkpoint & Test di Verifica FASE 4
- [ ] Tabella stampata a schermo con successo e formattazione allineata al 100%.
- [ ] Timestamp di uptime di tutti i container su TrueNAS invariato (zero downtime/zero reload).

---

### 📚 FASE 5: Documentazione, Sync Todo e Rigenerazione Wiki Context

#### Obiettivo
Allineare l'inventario del repository, i file canonici e il contesto cognitivo degli agenti.

#### Azioni
1. Sincronizzare `todo.md` aggiornando lo stato dei task completati.
2. Registrare il nuovo tool in `GEMINI.md` nella mappa concettuale e nella cheatsheet operativa.
3. Eseguire gli script obbligatori di validazione e rigenerazione:
   `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py`

#### 🛑 Checkpoint & Test di Verifica FASE 5
- [ ] `validate_network.py` con esito positivo (nessun errore o incongruenza).
- [ ] `build_wiki_context.py` eseguito con successo e `wiki/wiki_context.md` aggiornato.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 3 (Implementazione Wrapper Shell Bash `check_truenas_docker_updates.sh`)
- **Ultima Azione Completata**: Fase 1 e Fase 2 completate con successo. Motore OCI V2 `scripts/truenas/utils/check_docker_registry_updates.py` implementato e validato con test unitario (rilevamento Dozzle v11.3, Homepage v2.4.0, gestione immagini locali e digest).
- **Prossimo Passo Operativo**: Creazione del wrapper eseguibile `scripts/truenas/check_truenas_docker_updates.sh` con gestione opzioni (`--all`, `--compose`, `--json`), `chmod +x` e validazione end-to-end con estrazione live da TrueNAS (`10.10.20.50`).
- **Blocchi/Decisioni Pendenti**: Nessuno. Riprendere con `/resume [[truenas-docker-image-updates-checker]]`.
