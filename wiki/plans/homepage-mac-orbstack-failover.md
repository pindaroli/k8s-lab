---
title: "Piano: Integrazione Homepage Mac e Console Traefik su OrbStack Failover"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-23
tags:
  - "#core"
  - "#app"
  - "#network"
  - "#active"
  - "#homepage"
---

# Piano Operativo: Integrazione Homepage Mac (`homepage-mac`) e Console Traefik su OrbStack

> **Percorso Canonico Wiki**: `wiki/plans/homepage-mac-orbstack-failover.md` (alias: `[[homepage-mac-orbstack-failover]]`)  
> **Comando di Attivazione per l'Agente Locale**: `/resume [[homepage-mac-orbstack-failover]]`  
> **Governance Collegata**: [[orbstack-failover-truenas-services]], [[SCHEMA]], [[go-launcher-script-pattern]].

---

## 1. Contesto e Obiettivo

Durante lo stato **RACK DARK (`lab_mode_off`)**, i server fisici Proxmox VE e TrueNAS SCALE sono spenti. I carichi AI e i 7 server MCP attivi sono migrati su **Mac Studio M2 Ultra (`10.10.20.100`)** tramite **OrbStack**.

L'obiettivo di questo piano è dotare Mac Studio di un'interfaccia visiva unificata **Homepage (`homepage-mac`)** accessibile su `http://10.10.20.100:3000` e abilitare la **Console Web Traefik** su `http://10.10.20.100:8180`, fornendo all'utente una dashboard immediata per monitorare e accedere a:
- **Hermes Agent** (`:9119`)
- **LiteLLM Proxy** (`:4000`)
- **Dozzle Log Viewer** (`:8888`)
- **Traefik Web Console** (`:8180`)
- **OPNsense WebGUI** (`https://192.168.2.254`)
- **Ollama Metal locale** (`:11434`)
- **I 7 Server MCP attivi** (OPNsense, Ollama, KEF, Meross, Gemini DeepSearch, GitHub, NowAIkit).

---

## 2. Decisioni Architetturali Approvate (Intervista `/grill-me`)

| # | Ambito | Decisione Approvata | Specifica Tecnica |
| :- | :--- | :--- | :--- |
| **1** | **Indirizzamento Homepage** | **Porta host standard `:3000`** | Raggiungibile direttamente su `http://10.10.20.100:3000` (e `http://localhost:3000`) senza modifiche ai record DNS Unbound di OPNsense. |
| **2** | **Console Web Traefik** | **Porta host dedicata `:8180`** | Abilitazione in Traefik di `--api.insecure=true` e `--api.dashboard=true` esponendo `8180:8080`, accessibile su `http://10.10.20.100:8180`. |
| **3** | **Perimetro Servizi** | **Suite Completa Failover** | Hermes Agent, LiteLLM, Ollama Metal, Dozzle, Traefik Console, OPNsense e i 7 server MCP attivi con relativi controlli di salute (ping). |
| **4** | **Ciclo di Vita** | **Integrata in OrbStack Failover** | Gestita direttamente da `docker-compose.orbstack.yaml`: si avvia atomicamente con `lab_mode_off.sh` e si spegne in standby con `lab_mode_eco.sh` / `lab_mode_full.sh`. |
| **5** | **Isolamento K8s** | **Esclusiva Mac Studio** | Nessun link/modifica alle dashboard Kubernetes (`homepage.yaml` e `homepage-local.yaml`), rimanendo dedicata al contesto RACK DARK. |

---

## 3. Mappa dei File da Creare o Modificare

| Azione | Percorso File | Descrizione |
| :--- | :--- | :--- |
| **CREAZIONE** | `docker/orbstack-failover/homepage-config/settings.yaml` | Layout a 3 colonne, tema dark, titolo personalizzato. |
| **CREAZIONE** | `docker/orbstack-failover/homepage-config/services.yaml` | Definizione dei servizi raggruppati in categorie con icone e URL. |
| **CREAZIONE** | `docker/orbstack-failover/homepage-config/widgets.yaml` | Widget risorse hardware (CPU, RAM, disco) e orologio. |
| **MODIFICA** | `docker/orbstack-failover/docker-compose.orbstack.yaml` | Aggiunta porta `:8180` e flag API a Traefik; aggiunta container `homepage-mac` (:3000). |
| **MODIFICA** | `scripts/infrastructure/orbstack_failover.sh` | Inclusione delle porte `:3000` e `:8180` nel gate di attesa healthcheck. |

---

## 4. Fasi Operative di Implementazione (Protocollo Test-Driven §12)

### FASE 1: Creazione dei File di Configurazione Homepage
Creare la directory `docker/orbstack-failover/homepage-config/` e scrivere:
1. `settings.yaml`
2. `services.yaml`
3. `widgets.yaml`

### FASE 2: Aggiornamento `docker-compose.orbstack.yaml`
1. Aggiornare `traefik` esponendo `8180:8080` e aggiungendo i comandi `--api.dashboard=true` e `--api.insecure=true`.
2. Aggiungere il servizio `homepage` (porta `3000:3000`, montaggio in sola lettura di `homepage-config/`).

### FASE 3: Aggiornamento Gate di Prontezza in `orbstack_failover.sh`
Includere le porte `3000` e `8180` nella condizione `until` di `activate_orbstack_failover`.

### FASE 4: Collaudo Isolato e Verifica HTTP
1. Avviare lo stack:
   ```bash
   bash -c 'ROOT_DIR="$(pwd)" && source scripts/infrastructure/orbstack_failover.sh && activate_orbstack_failover'
   ```
2. Verificare gli endpoint:
   - `http://10.10.20.100:3000`
   - `http://10.10.20.100:8180/dashboard/`
3. Eseguire il failback verso TrueNAS:
   ```bash
   bash -c 'ROOT_DIR="$(pwd)" && source scripts/infrastructure/orbstack_failover.sh && deactivate_orbstack_failover_to_truenas'
   ```
4. Eseguire validazione di rete e rigenerazione del wiki context:
   ```bash
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: COMPLETATO ✅ (Fasi 1-4 convalidate con esito positivo al 100%)
- **Ultima Azione Completata**: Collaudo E2E isolato eseguito con successo (homepage-mac su :3000 con HTTP 200, Traefik Dashboard su :8180 con HTTP 200, gate healthcheck su 6 porte, failback pulito e ripristino standby).
- **Prossimo Passo Operativo**: Nessuno. Piano eseguito, verificato e conforme al 100% a tutte le policy di progetto.
- **Blocchi/Decisioni Pendenti**: Nessun blocco. Tutte le funzionalità operative in `docker-compose.orbstack.yaml` e negli script di orchestrazione.
