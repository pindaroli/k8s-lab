---
title: "Piano: Configurazione Dichiarativa della Flotta Ollama tramite rete.json e Ansible"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-21
completed_at: 2026-10-21
tags:
  - "#ollama"
  - "#ansible"
  - "#automation"
  - "#pve3"
  - "#mac"
  - "#configuration"
---

# Piano: Configurazione Dichiarativa della Flotta Ollama tramite `rete.json` e Ansible

Il presente piano operativo definisce e consolida l'architettura e l'automazione Ansible per gestire in modo centralizzato, canonico e dichiarativo i parametri di configurazione dei nodi Ollama dell'homelab (`lxc-ollama` su PVE3 e `mac` locale su macOS) utilizzando come **Single Source of Truth** il registro canonico `rete.json` sotto i servizi dei rispettivi nodi.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[SCHEMA]] (Regole di Governance e Salvataggio del Wiki)
- [[Ollama]] (Entità Canonica del Servizio Ollama)
- [[lxc-ollama-hardware-limit-optimization]] (Dimensionamento Hardware e Parametri di Runtime su PVE3)
- [[Network_Registry]] (Censimento IP `10.10.20.33` e `127.0.0.1`)
- [[guidellm-benchmark-script]] (Tool di Benchmark che si interfaccia con i due nodi Ollama)

---

## 1. Architettura Implementata

1. **Sorgente di Verità Canonica (`rete.json`)**:
   - Invece di creare un file YAML/JSON isolato, i parametri sono censiti nel grafo canonico di rete in `rete.json`, all'interno della chiave `env` del servizio `ollama` per ciascun nodo:
     - `lxc-ollama` (`10.10.20.33`): `OLLAMA_NUM_PARALLEL: 2`, `OLLAMA_MAX_LOADED_MODELS: 1`, `OLLAMA_KEEP_ALIVE: -1`, `OLLAMA_FLASH_ATTENTION: 1`, `OLLAMA_KV_CACHE_TYPE: q8_0`.
     - `mac studio` (`10.10.20.100` / `localhost`): `OLLAMA_NUM_PARALLEL: 1`, `OLLAMA_MAX_LOADED_MODELS: 1`, `OLLAMA_KEEP_ALIVE: 5m`, `OLLAMA_FLASH_ATTENTION: 1`, `OLLAMA_KV_CACHE_TYPE: q8_0`.
2. **Template Jinja2 Specifici**:
   - `ansible/playbooks/infrastructure/templates/ollama.override.conf.j2`: Genera `/etc/systemd/system/ollama.service.d/override.conf` per Linux systemd.
   - `ansible/playbooks/infrastructure/templates/sh.brew.ollama.plist.j2`: Genera `~/Library/LaunchAgents/sh.brew.ollama.plist` per macOS launchd.
3. **Playbook Idempotente (`ansible/playbooks/infrastructure/configure_ollama_fleet.yml`)**:
   - Legge dinamicamente `rete.json` tramite `lookup('file', ...)` ed estrae il blocco `env` del rispettivo nodo.
   - Applica i file di configurazione solo se differiscono.
   - Gestisce il restart selettivo tramite handler:
     - Linux: `systemctl daemon-reload` e `systemctl restart ollama`.
     - macOS: `launchctl bootout` + `launchctl bootstrap` per caricare il nuovo plist in memoria senza sovrascritture esterne.
   - Health check integrato via HTTP `/api/version` per entrambi i nodi.
   - Idempotenza garantita al 100% (`changed=0` alla seconda esecuzione).

---

## 2. Esito delle Fasi Operative

- [x] **Fase 1: Censimento SSOT in `rete.json`**: Aggiunto blocco `env` sotto i servizi Ollama di `lxc-ollama` e `mac studio`. Validato con `validate_network.py`.
- [x] **Fase 2: Creazione Template Jinja2**: Sviluppati `ollama.override.conf.j2` e `sh.brew.ollama.plist.j2`.
- [x] **Fase 3: Sviluppo Playbook Ansible**: Creato `configure_ollama_fleet.yml` con task dichiarativi e health check.
- [x] **Fase 4: Validazione e Test Idempotenza**:
  - `lxc-ollama`: 0.34.2 healthy (`changed=0`).
  - `mac studio`: 0.32.1 healthy (`changed=0`).
- [x] **Fase 5: Documentazione e Wiki Sync**: Creata entità [[Ollama]], aggiornato `GEMINI.md`, validati e rigenerati i contesti wiki.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Completato (Fase 5)
- **Ultima Azione Completata**: Test di idempotenza del playbook Ansible con esito `changed=0` su entrambi i nodi ed esecuzione degli script di validazione e rigenerazione wiki.
- **Prossimo Passo Operativo**: Nessuno. Obiettivo completato.
- **Blocchi/Decisioni Pendenti**: Nessuno.
