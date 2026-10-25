---
title: "Piano: Hermes Agent Hardening Sincronizzazione Failover, Convergenza Ownership UID 1000 e UI Web Terminal"
type: plan
status: archived
certified_for_ai: false
superseded_by: "[[homelab-hermes-convergence-and-compose-cross-hardening]]"
created_at: 2026-10-25
tags:
  - "#plan"
  - "#hermes"
  - "#orbstack"
  - "#truenas"
  - "#docker"
  - "#sync"
  - "#security"
---

# Piano: Hermes Agent Hardening Sincronizzazione Failover, Convergenza Ownership UID 1000 e UI Web Terminal

> [!NOTE]
> **Stato**: `active` / `certified_for_ai: true`.
> Piano strutturale di hardening formulato a seguito dell'incidente post-startup Mac Studio: risoluzione alla radice del crash loop Gateway Hermes, esclusione IPC/socket in rsync, convergenza globale dell'ownership su UID 1000 e fissaggio definitivo del Web Terminal nella WebGUI.

---

## 1. Contesto, Analisi Post-Mortem & Decisioni Architetturali

### 1.1 Sintomi Rilevati Post-Startup
All'accensione del Mac Studio in modalità failover/ripristino verso TrueNAS (`lab_mode_eco`), l'utente ha riscontrato:
1. **Mancata risposta ai prompt in chat**: l'interfaccia Web di Hermes (`:9119`) carica la pagina correttamente, ma qualsiasi messaggio inviato rimane senza risposta.
2. **Pulsante Web Terminal invisibile**: nella sidebar della WebGUI non compare la voce "Terminale" per aprire la sessione shell `ttyd`.

### 1.2 Root Cause Analysis (Evidenze di Runtime)
Dall'ispezione analitica dei log container e del codice sorgente (`/opt/hermes/gateway/control_socket.py`):
1. **Crash Loop del processo `gateway-default`**:
   - Mentre il servizio `dashboard` (FastAPI) è attivo, il servizio core `gateway-default` (engine per chat e sessioni) si riavvia ogni 20 secondi con:
     ```text
     WARNING gateway.control_socket: Gateway control socket failed to start (non-fatal): control socket belongs to another user
     RuntimeError: gateway session bootstrap control listener unavailable
     WARNING gateway.host_rendezvous: ignoring host record /opt/data/.local/state/hermes/gateway-locks/host-gateway.json: owned by uid 1000 (expected 10000)
     ```
   - Nel codice di Hermes:
     ```python
     if bind_path.exists():
         if bind_path.lstat().st_uid != os.getuid():
             raise PermissionError("control socket belongs to another user")
         bind_path.unlink()
     ```
   - All'interno del container `hermes-main`, l'utente `hermes` ha UID **10000**.
   - Sul Mac (OrbStack) o post-chown su TrueNAS, i file in `/mnt/stripe/hermesAgent/HermesMain` avevano UID **1000** (`olindo:k8s`).
   - Quando Hermes tenta di inizializzare `/opt/data/gateway.sock`, trova un socket preesistente con UID 1000 (`st_uid != os.getuid()`), rifiuta di rimuoverlo o aprirlo per motivi di sicurezza e fallisce il bootstrap del listener.
2. **Trasferimento indebito di socket IPC e lock di processo via `rsync`**:
   - Lo script `orbstack_failover.sh` sincronizzava `HermesMain/` senza escludere socket UNIX (`.sock`) e lock di processo (`gateway-locks/`).
   - I socket UNIX sono costrutti IPC effimeri vincolati al kernel locale: trasferirli su un altro host crea sempre file orfani "morti" che bloccano il nuovo demone.
3. **Mancata visualizzazione del pulsante Terminale**:
   - `terminal-inject.js` utilizzava `document.querySelectorAll("nav, aside")[0].appendChild(terminalNavBtn)`.
   - Nella SPA React di Hermes, la sidebar (`aside#app-sidebar`) è un layout flexbox con sub-container scrollabile (`coreItems`) e footer pinned. Fare `appendChild` sul nodo radice `<aside>` inserisce il pulsante in fondo al div, fuori dal flusso visivo o sotto il viewport.
   - Inoltre, `index.html` viene cachato dal browser senza cache-busting esplicito.

---

### 1.3 Decisioni Architetturali Consolidate (Le 3 Invarianti)

| # | Invariante | Soluzione Architetturale | Beneficio SRE |
| :--- | :--- | :--- | :--- |
| **1** | **Anti-Orphan Sync Protection** | Esclusione formale in `rsync` di `*.sock*`, `*.lock`, `gateway-locks/` + bonifica automatica al boot in `99-hermes-terminal.sh`. | I socket e i lock effimeri non vengono MAI trasferiti tra host. In caso di crash/spegnimento brutale, il boot del container pulisce automaticamente eventuali residui orfani prima di avviare il gateway. |
| **2** | **Convergenza Universale UID 1000** | Rimappatura trasparente dell'utente `hermes` nel container da UID 10000 a **UID 1000 / GID 1000** tramite `usermod`/`groupmod` nel cont-init. | **Unica identità numerica 1000:1000 per l'intero homelab**: TrueNAS ZFS (`olindo:k8s`), Mac Studio (OrbStack), Git in `common/prj` e processo Hermes. Zero attriti di permessi, zero problemi di "dubious ownership" in Git, zero mismatch sui socket. |
| **3** | **Ancoraggio Robusto UI Terminale** | Inserimento in `terminal-inject.js` come elemento fratello (sibling) del pulsante `Chat` (`[href*="/chat"]`), fallback floating pill e cache-buster `?v=2.2` in `index.html`. | Il pulsante terminale si integra nativamente nel menu di navigazione React, visibile sia su desktop che su mobile/sidebar collassata, con garanzia di download immediato dal browser. |

---

## 2. Mappa dei File da Creare o Modificare

```
k8s-lab/
├── scripts/infrastructure/
│   └── orbstack_failover.sh                    # [MODIFICA] Aggiunta esclusioni rsync socket/lock e unificazione chown 1000:1000
├── docker/hermes/
│   ├── s6/
│   │   └── 99-hermes-terminal.sh               # [MODIFICA] usermod UID 1000 + auto-clean socket + cache-buster index.html
│   └── web/
│       └── terminal-inject.js                  # [MODIFICA] Riprogettazione injection DOM con target sibling [href*="/chat"]
└── wiki/plans/
    └── hermes-agent-failover-sync-hardening-and-uid-convergence.md # [CREAZIONE] Questo piano operativo
```

---

## 3. Fasi Operative con Protocollo Test-Driven (§12)

### FASE 1: Aggiornamento File di Configurazione Container

#### 1.1 Aggiornamento `99-hermes-terminal.sh`
- Aggiunta rimappatura UID/GID `hermes` a 1000:
  ```bash
  if [ "$(id -u hermes 2>/dev/null)" != "1000" ]; then
      groupmod -g 1000 hermes 2>/dev/null || true
      usermod -u 1000 -g 1000 hermes 2>/dev/null || true
  fi
  ```
- Aggiunta auto-clean socket e lock al boot:
  ```bash
  rm -f /opt/data/*.sock /opt/data/*.sock.path /opt/data/*.lock
  rm -rf /opt/data/.local/state/hermes/gateway-locks/*
  chown -R hermes:hermes /opt/data
  ```
- Aggiornamento iniezione cache-buster in `index.html`:
  `<script src="/terminal-inject.js?v=2.2" defer></script>`.

#### 1.2 Riprogettazione `terminal-inject.js`
- Ricerca attiva del container dei bottoni (`[href*="/chat"]` o `.nav-item`).
- Inserimento del pulsante come elemento di primo livello della lista di navigazione.
- Inserimento di una pillola/pulsante di fallback galleggiante in basso a sinistra in caso di sidebar collassata.

#### 1.3 Test di Validazione Fase 1
- Sintassi bash validata con `bash -n`.
- Validazione parsing JavaScript.

---

### FASE 2: Distribuzione File su TrueNAS e Mac Studio

#### 2.1 Allineamento locale su Mac Studio
- Copia dei file aggiornati in `~/.homelab-failover/hermes/s6/` e `~/.homelab-failover/hermes/web/`.

#### 2.2 Distribuzione remota su TrueNAS (10.10.20.50)
- Trasferimento via `scp` su `/mnt/stripe/truenas-docker/hermes/s6/99-hermes-terminal.sh` e `/mnt/stripe/truenas-docker/hermes/web/terminal-inject.js`.

#### 2.3 Test di Validazione Fase 2
- Verifica integrità MD5/SHA256 tra file sorgente e destinazione su Mac e TrueNAS.

---

### FASE 3: Hardening di `orbstack_failover.sh`

#### 3.1 Esclusione Socket e Lock in tutti i blocchi `rsync`
- Aggiunta ai comandi `rsync` (sia `sync_hermes_state_from_truenas` che `deactivate_orbstack_failover_to_truenas`):
  ```bash
  --exclude='*.sock*' \
  --exclude='*.lock' \
  --exclude='gateway-locks/' \
  --exclude='.local/state/hermes/gateway-locks/' \
  ```

#### 3.2 Unificazione Normalizzazione Permessi
- Normalizzazione univoca `sudo -n chown -R olindo:k8s '${HERMES_ROOT_REMOTE}'` su TrueNAS, che ora corrisponde perfettamente a UID 1000:1000 sia per l'host che per il container.

#### 3.3 Test di Validazione Fase 3
- Esecuzione dry-run con `bash -n scripts/infrastructure/orbstack_failover.sh`.

---

### FASE 4: Bonifica dello Stato TrueNAS e Riavvio Container

#### 4.1 Rimozione manuale una tantum dei file orfani su TrueNAS
- Comando:
  ```bash
  ssh olindo@10.10.20.50 "sudo -n rm -f /mnt/stripe/hermesAgent/HermesMain/*.sock /mnt/stripe/hermesAgent/HermesMain/*.sock.path /mnt/stripe/hermesAgent/HermesMain/*.lock && sudo -n rm -rf /mnt/stripe/hermesAgent/HermesMain/.local/state/hermes/gateway-locks/*"
  ```

#### 4.2 Riavvio del container `hermes-main`
- Comando:
  ```bash
  ssh olindo@10.10.20.50 "sudo -n docker restart hermes-main"
  ```

#### 4.3 Test di Validazione Fase 4
- Ispezione log di avvio s6:
  ```bash
  ssh olindo@10.10.20.50 "sudo -n docker exec hermes-main s6-svstat /run/service/gateway-default /run/service/dashboard /run/service/ttyd"
  ```
  *Criterio di successo*: tutti i servizi riportano `up` con PID stabile (nessun incremento continuo di tempo/riavvio).
- Ispezione UID del processo:
  ```bash
  ssh olindo@10.10.20.50 "sudo -n docker exec hermes-main ps -ef | grep gateway"
  ```
  *Criterio di successo*: il processo gira con UID 1000 (`hermes`).

---

### FASE 5: Collaudo E2E Test-Driven

#### 5.1 Test di Risposta Chat (API / Web)
- Invio di un prompt di test tramite l'endpoint HTTP di Hermes o direttamente dalla WebGUI.
- Verifica ricezione risposta completa dall'agente.

#### 5.2 Test di Rendering Web Terminal
- Apertura della WebGUI su `https://hermes-internal.pindaroli.org:8443` (o `http://10.10.20.50:9119`).
- Verifica visiva del pulsante "Terminale" nella sidebar.
- Click sul pulsante e verifica apertura iframe con shell interattiva `[root@truenas]:/opt/data#`.
- Verifica persistenza della sessione al cambio di scheda.

---

## 4. Piano di Rollback

In caso di anomalia bloccante durante l'esecuzione del piano:
1. **Ripristino permessi container predefiniti**:
   - Rimuovere le righe `usermod`/`groupmod` da `99-hermes-terminal.sh`.
   - Reimpostare `chown -R 10000:10000 /mnt/stripe/hermesAgent/HermesMain` su TrueNAS.
2. **Ripristino file di failover**:
   - `git checkout scripts/infrastructure/orbstack_failover.sh`.
3. **Riavvio del container**:
   - `docker restart hermes-main` su TrueNAS.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 0 (Attesa consulto e autorizzazione utente)
- **Ultima Azione Completata**: Redazione del piano architetturale di hardening e convergenza UID 1000.
- **Prossimo Passo Operativo**: Presentazione del prompt di consulto e avvio Fase 1 previa approvazione.
- **Blocchi/Decisioni Pendenti**: Attesa esito consulto architetturale.
