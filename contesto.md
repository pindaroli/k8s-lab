# Quadro Contestuale e Vincoli Specifici per il Consulto

## 1. Scheda del Piano in Esame
- **Titolo**: Convergenza Strutturale SQLite journal_mode DELETE e Hardening Endpoint Health Homepage per Hermes Agent
- **File**: `wiki/plans/hermes-sqlite-journal-mode-and-homepage-health-hardening.md`
- **Tipo**: Piano Operativo & Architetturale (`type: plan`)
- **Stato**: `active` (`certified_for_ai: true`)
- **Stack Tecnologico Coinvolto**:
  - **Hermes Agent**: Nous Research `v0.22.5` (container Docker s6-overlay supervised, Python 3.14/FastAPI).
  - **SQLite Database Storage**: SQLite 3 con journal mode WAL vs DELETE; checkpointing `wal_checkpoint(TRUNCATE)` prima del cambio modalità; memoria condivisa `.db-shm` e `mmap`.
  - **Storage & Sync Filesystem**: APFS macOS (host Mac Studio), `virtiofs` (OrbStack VM mount), ZFS NVMe pool `stripe` (TrueNAS SCALE bare metal).
  - **Orchestration & Synchronization**: `scripts/infrastructure/orbstack_failover.sh` (`rsync -az`, esclusioni e chown).
  - **Dashboard Monitoring**: Homepage `v2.4.0` (flotta 3 istanze simmetriche: `homepage-mac`, `homepage-k8s`, `homepage-truenas`).
  - **Single Source of Truth Storage**: `storage.json` (censimento dataset `stripe/hermesAgent/HermesMain`).

---

## 2. Nodi, IP e Rete Pertinenti (da `rete.json`)
- **Mac Studio M2 Max (Failover Node)**:
  - **IP**: `10.10.20.100` (VLAN 20 Client / Failover Target).
  - **Ruolo**: Ospita il motore di virtualizzazione **OrbStack** che esegue lo stack Docker di failover (13 container) in modalità `lab_mode_off` (RACK DARK).
  - **Mount Host**: `/Users/olindo/hermesAgent/HermesMain` montato su `/opt/data` nel container via driver cross-VM `virtiofs`.
- **TrueNAS SCALE Bare Metal (Primary Node)**:
  - **IP**: `10.10.20.50` (VLAN 20).
  - **Ruolo**: Ospita lo storage ZFS e i container Docker primari in modalità `lab_mode_full` e `lab_mode_eco`.
  - **Storage Hermes Primario**: `/mnt/stripe/hermesAgent/HermesMain` montato in `/opt/data` (Linux nativo ZFS su pool NVMe).
- **OPNsense Firewall & DNS (Gateway)**:
  - **IP**: `192.168.2.254` (Management) / `10.10.20.1` (VLAN 20 Gateway).
  - **Ruolo**: Gestisce il DNS Unbound con host override atomici:
    - In `lab_mode_full` ed `eco`: record `hermes.pindaroli.org`, `home-internal.pindaroli.org` puntano a `10.10.20.50` (TrueNAS).
    - In `lab_mode_off`: record commutati a `10.10.20.100` (Mac Studio).

---

## 3. Storage & Filesystem Pertinenti (da `storage.json`)
- **Storage Hermes su TrueNAS**:
  - Dataset: `stripe/hermesAgent` montato localmente su `/mnt/stripe/hermesAgent`.
  - Sottodirectory: `HermesMain/` montata in `/opt/data` nel container `hermes-main`.
  - Permessi: `777` con owner `olindo:k8s` (`uid: 1000`, `gid: 1000`).
- **Storage Hermes su Mac Studio**:
  - Directory APFS: `/Users/olindo/hermesAgent/HermesMain` e `/Users/olindo/hermesAgent/common/prj`.
  - Owner: `olindo:staff` (`uid: 501` su macOS, mappato a `uid: 1000` nel container OrbStack).
  - Driver di virtualizzazione VM: `virtiofs` (non supporta mmap POSIX shared memory affidabile tra host e guest VM).
- **I 6 Database SQLite coinvolti**:
  1. `/opt/data/state.db` (sessioni e routing gateway)
  2. `/opt/data/kanban.db` (kanban dispatch board)
  3. `/opt/data/projects.db` (gestione progetti ed esecuzioni)
  4. `/opt/data/cron/executions.db` (cron scheduler log)
  5. `/opt/data/response_store.db` (store risposte API gateway)
  6. `/opt/data/runs_idempotency.db` (lock idempotenza turni agent)

---

## 4. Vincoli Architetturali & Golden Rules Applicabili (da `GEMINI.md`)
1. **DICHIARATIVITÀ & GITOPS**: Nessun workaround manuale a caldo o fix estemporaneo "one-off". Qualsiasi configurazione o normalizzazione deve risiedere nel repository Git (`docker/hermes/s6/99-hermes-terminal.sh`, `services.yaml`) e convergere automaticamente.
2. **KISS ARCHITECTURE (Keep It Simple, Stupid)**: Massima semplicità e robustezza. Nessun layer di complessità aggiuntivo (come database esterni o container dedicati a SQLite): l'uso di `journal_mode: delete` è una direttiva nativa supportata da Hermes e SQLite senza dipendenze.
3. **IDENTITÀ UNICA UID/GID 1000:1000**: Tutta la flotta Hermes e TrueNAS converge sull'utente non privilegiato `olindo:k8s` (`1000:1000`).
4. **ZERO DATA LOSS GUARD**: Divieto assoluto di cancellare file `.db-wal` e `.db-shm` prima di aver verificato con successo l'esito di `wal_checkpoint(TRUNCATE)` e la restituzione di `mode == 'delete'`. Divieto assoluto di cancellare o escludere da `rsync` eventuali file `*.db-journal` (hot rollback journal).
5. **SIMMETRIA HOMEPAGE A 3 ISTANZE**: Qualsiasi modifica a servizi o monitoraggio deve propagarsi su tutte e tre le istanze della flotta (`homepage-mac`, `homepage-k8s`, `homepage-truenas`).
6. **PROTOCOL DI VERIFICA TEST-DRIVEN**: Ogni singola fase deve essere validata da comandi di ispezione reali (log Dozzle puliti, HTTP 200 via curl, interrogazione PRAGMA journal_mode).

---

## 5. Aree di Attenzione & Quesiti Specifici per il Consulto
1. **Impatto Prestazionale**: Il passaggio da WAL a DELETE introduce penalità di performance percettibili su un agente locale/gateway singolo con carichi I/O tipici?
2. **Concorrenza Thread/Processi nel Container Hermes**: Hermes v0.22.5 esegue più processi che accedono contemporaneamente agli stessi database (es. `gateway`, `kanban dispatcher`, `cron scheduler`)? Con `journal_mode: DELETE`, ci sono rischi di timeout `database is locked` sotto carico?
3. **Robustezza del Meccanismo di Self-Healing in `99-hermes-terminal.sh`**: L'esecuzione di `wal_checkpoint(TRUNCATE)` seguita da `PRAGMA journal_mode=DELETE;` al boot del container è sufficientemente robusta per gestire file temporaneamente lockati o casi limite?
4. **Monitoraggio Homepage**: La sostituzione di `/health` con `/api/health` su tutte e 3 le istanze è pienamente conforme all'architettura interna di autenticazione di Hermes v0.22.5?
