---
title: "Piano: Integrazione Dozzle nello Stack Docker su TrueNAS SCALE (Porta 8888)"
type: plan
status: archived
certified_for_ai: false
resolved: true
resolved_at: "2026-10-03"
created_at: 2026-10-03
tags:
  - "#plan"
  - "#dozzle"
  - "#docker"
  - "#truenas"
  - "#monitoring"
  - "#observability"
---

# Piano: Integrazione Dozzle nello Stack Docker su TrueNAS SCALE (Porta 8888)

Questo piano definisce l'integrazione di **Dozzle** all'interno dello stack Docker primario su TrueNAS SCALE bare-metal (`10.10.20.50`), offrendo una dashboard web leggera, reattiva e in tempo reale per monitorare log, metriche (CPU/RAM), healthcheck e configurazioni di tutti i container del nodo senza introdurre complessità o rischi di configuration drift.

---

## 🎯 Obiettivi Architetturali

1. **Osservabilità Completa a Zero-Drift**:
   - Fornire una Web UI per ispezionare log live, streaming multi-container, healthcheck e parametri di runtime di tutti i container attivi su TrueNAS (inclusi Jellyfin, qBittorrent, Prowlarr, Homepage, MinimServer e l'intera flotta di 11 server MCP).
   - Preservare rigorosamente il principio *Git as Single Source of Truth*: Dozzle opera come strumento di sola ispezione e osservabilità, senza sovrascrivere o alterare i file dichiarativi.
2. **Impronta Minima & Assenza di Database**:
   - Dozzle è un singolo binario Go che consuma ~15 MB di RAM e comunica direttamente con l'API Docker locale tramite socket UNIX. Nessun database da manutenere o disallineare.
3. **Accesso Diretto LAN & Integrazione Dashboard**:
   - Esposizione diretta sulla porta host **`8888`** sull'IP `10.10.20.50` (evitando conflitti con la porta interna `8080` utilizzata da qBittorrent).
   - Registrazione del servizio nella dashboard Homepage di TrueNAS e Kubernetes.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[TrueNAS]] (TrueNAS SCALE bare-metal `10.10.20.50`)
- [[MCP_Platform]] (Flotta server MCP attivi su TrueNAS Docker porte 8101–8111)
- [[Homepage]] (Dashboard unificata di monitoraggio e servizi)
- [[servarr-truenas-permanent-migration]] (Stack container principale su TrueNAS)

---

## 1. Decisioni Architetturali & Specifiche

1. **Stack di Destinazione**:
   - Il servizio `dozzle` viene integrato all'interno dello stack principale `servarr/truenas-docker/docker-compose.yaml` (sincronizzato con `/mnt/stripe/truenas-docker/docker-compose.yaml` su TrueNAS).
   - Essendo collegato al socket host `/var/run/docker.sock`, Dozzle rileva automaticamente sia i container dello stack `servarr` sia i container dello stack adiacente `mcp` (`/mnt/stripe/truenas-docker/mcp/`).
2. **Version Pinning & Immagine OCI**:
   - Immagine ufficiale: `amir20/dozzle:v11.2.0` (ultima release stabile ufficiale pubblicata su GitHub, conforme alla regola homelab contro l'uso del tag `:latest`).
3. **Mappatura Porte & Rete**:
   - Porta interna container: `8080`
   - Porta host TrueNAS: **`8888`** (`8888:8080`)
   - URL LAN: `http://10.10.20.50:8888`
4. **Modalità Operativa, Socket e Persistenza**:
   - Mount del socket: `/var/run/docker.sock:/var/run/docker.sock:ro` (sola lettura per massima sicurezza e zero rischio di manipolazioni non tracciate).
   - Volume di persistenza: `/mnt/stripe/truenas-docker/dozzle:/data` (persiste utenti, impostazioni e preferenze del dashboard sul pool ZFS `stripe`).
   - Variabili d'ambiente raccomandate:
     - `DOZZLE_NO_ANALYTICS=true` (disabilitazione telemetria esterna)
     - `DOZZLE_LEVEL=info` (logging essenziale)

---

## 2. Definizione Dichiarativa del Servizio Docker Compose

Il blocco integrato in `servarr/truenas-docker/docker-compose.yaml`:

```yaml
  dozzle:
    image: amir20/dozzle:v11.2.0
    container_name: dozzle
    restart: unless-stopped
    ports:
      - "8888:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /mnt/stripe/truenas-docker/dozzle:/data
    environment:
      - DOZZLE_NO_ANALYTICS=true
      - DOZZLE_LEVEL=info
    healthcheck:
      test: ["CMD", "/dozzle", "healthcheck"]
      interval: 30s
      timeout: 5s
      retries: 3
```

---

## 3. Integrazione nella Dashboard Homepage

Aggiunta della card di servizio nella sezione infrastrutturale/monitoring di Homepage:

```yaml
    - Dozzle:
        icon: dozzle.png
        href: "http://10.10.20.50:8888"
        description: "TrueNAS Docker Logs & Container Monitor"
        ping: "http://10.10.20.50:8888/healthcheck"
```

---

## 4. Fasi Operative

### FASE 1: Aggiornamento Dichiarativo Repository
- [x] Aggiunta del servizio `dozzle` in `servarr/truenas-docker/docker-compose.yaml` (immagine `amir20/dozzle:v11.1.3`, porta `8888`, socket `:ro`).
- [x] Validazione sintattica YAML superata con successo (`ruby -ryaml`).

### FASE 2: Sincronizzazione e Rollout su TrueNAS (`10.10.20.50`)
- [x] Sincronizzazione del file `docker-compose.yaml` aggiornato su TrueNAS in `/mnt/stripe/truenas-docker/`.
- [x] Pull dell'immagine OCI `amir20/dozzle:v11.1.3`.
- [x] Avvio del container con `docker compose up -d dozzle`.

### FASE 3: Validazione Test-Driven & Ispezione
- [x] Verifica dello stato del container (`docker compose ps dozzle`) e superamento dell'healthcheck (`healthy`).
- [x] Test di connettività HTTP sulla porta LAN `8888`: `curl -i http://10.10.20.50:8888/healthcheck` (200 OK).
- [x] Verifica visiva nel browser di log, metriche e visibilità dell'intera flotta container TrueNAS (`/api/events/stream` attivo).

### FASE 4: Aggiornamento Homepage & Chiusura
- [x] Integrazione del link di Dozzle nella dashboard Homepage (K8s `homepage.yaml`, `homepage-local.yaml` e TrueNAS `services.yaml`).
- [x] Rollout della configurazione Homepage su Kubernetes e restart su TrueNAS completati con successo.
- [x] Consolidamento documentale e chiusura piano.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo (Fasi 1-4 completate).
- **Ultima Azione Completata**: Dozzle attivo 24/7 su TrueNAS (`10.10.20.50:8888`), status `healthy`, sola lettura `:ro`, integrato in tutte le dashboard Homepage.
- **Prossimo Passo Operativo**: Nessuno.
- **Blocchi/Decisioni Pendenti**: Nessuno.
