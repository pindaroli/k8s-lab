---
title: "Piano: Mitigazione Bitmagnet DHT Crawler, Ottimizzazione Scaling Factor e State Limiter OPNsense"
type: plan
status: archived
archived_at: 2026-10-17
certified_for_ai: false
completed_at: 2026-10-17
resolved: true
resolved_at: "2026-10-17"
created_at: 2026-10-17
tags:
  - "#plan"
  - "#bitmagnet"
  - "#opnsense"
  - "#pf"
  - "#truenas"
  - "#docker"
  - "#dht"
  - "#network"
---

# Piano: Mitigazione Bitmagnet DHT Crawler, Ottimizzazione Scaling Factor e State Limiter OPNsense

Questo piano operativo definisce la strategia di contenimento, isolamento e mitigazione per l'istanza di **Bitmagnet** (DHT Crawler & Torznab indexer) in esecuzione sullo stack Docker di **TrueNAS SCALE** (`10.10.20.50`), a seguito dell'incidente di saturazione della linea FTTH, blocco ricorsivo di Unbound DNS e flap del link WAN fisico `igc0` su OPNsense.

---

## 🎯 Obiettivi Architetturali

1. **Prevenzione Bufferbloat e Saturazione ONT**:
   - Limitare rigidamente la generazione e permanenza degli stati UDP effimeri verso la WAN, impedendo il collasso delle code di trasmissione dell'ONT WindTre 2.5G.
2. **Resilienza DNS e Isolamento Servizi Core**:
   - Garantire che le ricorsioni DNS di Unbound (`192.168.2.254:53`) e il traffico P2P ordinario di qBittorrent (`porta 30661`) non subiscano degradazioni o timeout.
3. **Contenimento Applicativo a Monte (TrueNAS)**:
   - Ridurre al minimo lo scaling factor dei worker interni di Bitmagnet (`DHT_CRAWLER_SCALING_FACTOR=1`) per minimizzare la generazione di query UDP al secondo.
4. **Circuito di Sicurezza a Valle (OPNsense pf)**:
   - Inserire una regola `Pass` con `quick` sull'interfaccia di transito `opt4` (`igc1`), con tetto massimo rigido di 300 stati contemporanei e timeout contratti per sessioni UDP incomplete.
5. **Zero-Downtime e Rollback Immediato**:
   - Snapshot preventivo ZFS su TrueNAS e backup della configurazione di OPNsense prima di qualsiasi modifica operativa.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[OPNsense]] (Firewall primario, Unbound DNS, pf state table)
- [[TrueNAS]] (TrueNAS SCALE bare-metal `10.10.20.50` su VLAN 20)
- [[Servarr]] (Stack Docker multimediale e qBittorrent)
- [[bitmagnet-truenas-docker-integration]] (Piano di deploy originale)
- [[Network_Registry]] (Topologia di rete, SVI EXOS e transito L3)

---

## 🛡️ Strategia Preventiva di Sicurezza: Snapshot e Backup

Prima di procedere all'applicazione delle modifiche, è fortemente raccomandata l'esecuzione di due misure di salvaguardia istantanee:

### 1. Snapshot ZFS su TrueNAS SCALE (Zero-Cost, Rollback Istantaneo)
- **Target**: Dataset `/mnt/stripe/truenas-docker` (contiene sia la cartella dati/PostgreSQL di Bitmagnet, sia il file `docker-compose.yaml`).
- **Autenticazione**: Accesso SSH tramite utente `olindo` (chiave `~/.ssh/id_ed25519` con `sudo`).
- **Motivazione**: Uno snapshot ZFS è atomico, richiede meno di 1 secondo, ha overhead zero in spazio disco finché i blocchi non divergono, e garantisce un ripristino istantaneo dello stato del database e delle configurazioni in caso di problemi post-restart.
- **Comando**:
  ```bash
  ssh truenas "sudo zfs snapshot stripe/truenas-docker@pre-bitmagnet-mitigation-\$(date +%F)"
  ```

### 2. Backup Configurazione OPNsense (History / XML)
- **Target**: Configurazione attiva di OPNsense (`config.xml`).
- **Funzionamento OPNsense**: OPNsense registra automaticamente un checkpoint di backup cronologico ad ogni singola modifica salvata in **System -> Configuration -> History**, permettendo il rollback con un singolo click.
- **Azione Preventiva**: Effettuare il download manuale del backup `config.xml` da **System -> Configuration -> Backups** prima di inserire la nuova regola di filtraggio.

---

## 📋 Fasi Operative Dettagliate

### Fase 1: Snapshot Preventivo su TrueNAS SCALE

1. Eseguire lo snapshot ZFS del dataset dello stack Docker su TrueNAS:
   ```bash
   ssh truenas "sudo zfs snapshot stripe/truenas-docker@pre-bitmagnet-mitigation-\$(date +%F)"
   ```
2. **Verifica Test-Driven**:
   ```bash
   ssh truenas "sudo zfs list -t snapshot | grep pre-bitmagnet-mitigation"
   ```

---

### Fase 2: Configurazione e Tuning Applicativo Docker (TrueNAS)

1. Nel file `/mnt/stripe/truenas-docker/docker-compose.yaml` (o nel repository `servarr/truenas-docker/docker-compose.yaml`), aggiornare l'ambiente del servizio `bitmagnet`:
   ```yaml
     bitmagnet:
       image: ghcr.io/bitmagnet-io/bitmagnet:v0.10.1
       # ...
       environment:
         # ...
         - DHT_CRAWLER_SCALING_FACTOR=1
         - DHT_CRAWLER_SAVE_FILES_THRESHOLD=500
         - DHT_CRAWLER_SAVE_PIECES=false
         - LOG_LEVEL=info
         - TZ=Europe/Rome
   ```
2. Riavviare il container `bitmagnet` per caricare le nuove variabili:
   ```bash
   ssh truenas "cd /mnt/stripe/truenas-docker && sudo docker compose up -d bitmagnet"
   ```
3. **Verifica Test-Driven**:
   - Verificare che il container sia UP:
     ```bash
     ssh truenas "sudo docker ps --filter name=bitmagnet"
     ```
   - Verificare che il parametro `DHT_CRAWLER_SCALING_FACTOR=1` sia caricato:
     ```bash
     ssh truenas "sudo docker inspect bitmagnet --format '{{json .Config.Env}}' | grep DHT_CRAWLER_SCALING_FACTOR"
     ```

---

### Fase 3: Creazione Regola State Limiter su OPNsense

Inserire via Web UI su OPNsense (**Firewall -> Rules -> OPT4** / Transit) la seguente regola, posizionandola **in cima** alla lista (sopra la regola `Allow All Transit`):

- **Action**: `Pass`
- **Quick**: `Checked` (applica immediatamente ed evita fall-through)
- **Interface**: `opt4` (`igc1` - Transit L3)
- **Direction**: `in`
- **TCP/IP Version**: `IPv4`
- **Protocol**: `UDP`
- **Source**: `Single host or Network` -> `10.10.20.50`
- **Source Port Range**: `from: 3334` `to: 3334`
- **Destination**: `any`
- **Destination Port Range**: `any`
- **State Options (Advanced)**:
  - **Max states**: `300` (tetto massimo globale sulla regola)
  - **Max source states**: `300` (tetto per singolo IP sorgente)
  - **State Timeout (udp.single)**: `8` (scadenza in 8 secondi per pacchetti UDP senza risposta)
  - **State Timeout (udp.multiple)**: `20` (scadenza in 20 secondi per scambi UDP bidirezionali)
- **Description**: `Bitmagnet DHT Crawler State Limiter`

Sintassi `pf` risultante attesa:
```text
pass in quick on igc1 inet proto udp from 10.10.20.50 port 3334 to any keep state (max 300, max-src-states 300, udp.single 8, udp.multiple 20) label "Bitmagnet DHT Crawler State Limiter"
```

---

### Fase 4: Protocollo di Collaudo e Verifica Test-Driven

1. **Verifica Stati pf su OPNsense**:
   Controllare che gli stati associati alla porta 3334 non superino la soglia di 300:
   ```bash
   pfctl -s state | grep "10.10.20.50:3334" | wc -l
   ```
2. **Verifica Regola e Drop Counter su OPNsense**:
   ```bash
   pfctl -v -s rules | grep -A 4 "Bitmagnet DHT Crawler State Limiter"
   ```
3. **Verifica Assenza di Impatto su qBittorrent e DNS**:
   - Test risoluzione DNS da TrueNAS:
     ```bash
     ssh truenas "dig @192.168.2.254 tracker.openbittorrent.com +short"
     ```
   - Controllo stati qBittorrent su OPNsense (porta 30661 libera da limiti):
     ```bash
     pfctl -s state | grep "10.10.20.50:30661" | head -n 5
     ```
4. **Verifica Stabilità Interfaccia WAN `igc0`**:
   Verificare che non vi siano nuovi eventi di link flap nel buffer del kernel:
   ```bash
   dmesg | grep "igc0: link state changed" | tail -n 5
   ```
5. **Verifica Operatività Bitmagnet**:
   - Accesso alla Web UI: `http://10.10.20.50:3333`
   - Log live tramite Dozzle: `http://10.10.20.50:8888` (assenza di storm di errori DNS o deadlock)

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Applicazione State Limiter (max 300 / max-src 300) su OPNsense TRANSIT; tuning Bitmagnet Scaling Factor 1; test-driven verification completa (DNS Unbound OK, Bitmagnet WebUI OK, qBittorrent OK, Jellyfin OK, Prowlarr OK).
- **Prossimo Passo Operativo**: Monitoraggio ordinario dei log Bitmagnet su Dozzle e dell'andamento stati su OPNsense.
- **Blocchi/Decisioni Pendenti**: Nessun blocco pendente. Infrastruttura stabile e convergente.
