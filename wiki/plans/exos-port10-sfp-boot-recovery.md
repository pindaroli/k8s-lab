---
title: "Automazione Startup SFP+ Porta 10 su Extreme EXOS"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-11
tags:
  - "#network"
  - "#exos"
  - "#ansible"
  - "#active"
---

# Piano: Automazione Startup SFP+ Porta 10 su Extreme EXOS ([[exos-port10-sfp-boot-recovery]])

## 1. Obiettivo e Contesto
Allo startup dello Switch Core Extreme Networks Summit X620-10x (`192.168.2.1`), la connettività 10 GbE con lo switch GoodTop GT-ST024M (`192.168.2.2`, stanza da letto) sulla **Porta 10** non sale automaticamente, richiedendo un intervento manuale di disconnessione e riconnessione fisica dell'adattatore SFP+ in rame (`10G-T30-CSC`).

### Diagnosi Tecnica (Root Cause)
* **Modulo Hardware**: Ricetrasmettitore 10GBASE-T RJ45 OEM (`10G-T30-CSC`, emulato come `SF+_SR (Unsupported)` a 850 nm, temperatura ~61 °C).
* **Meccanismo di Errore**: All'avvio di EXOS, le porte DAC passive (1–9) si sincronizzano istantaneamente (<1s). Il modulo rame attivo nella Porta 10 impiega 2–3 secondi per il boot interno del PHY e 8–10 secondi per il link training PAM16 sul doppino Cat6A. Con la porta configurata su `auto off speed 10000 duplex full`, la SerDes Broadcom di EXOS va in timeout all'avvio e non ritenta il Clock/Data Recovery (CDR) continuo.
* **Soluzione Architetturale**: Creazione di uno script di boot nativo (`autoexec.xsf` / `bounce_port10.py`) su EXOS che, al termine del caricamento del sistema, esegue in autonomia il bounce software della porta (`disable ports 10` seguito da `enable ports 10`), riallineando la SerDes con il modulo già caldo e operativo.

---

## 2. Architettura dei File su EXOS

1. **`/usr/local/cfg/bounce_port10.py`**:
   Script Python nativo EXOS che attende 15 secondi (garantendo il completamento del boot del modulo) e resetta la porta 10:
   ```python
   #!/usr/bin/env python
   import time
   import exsh

   time.sleep(15)
   exsh.clicmd("disable ports 10")
   time.sleep(2)
   exsh.clicmd("enable ports 10")
   ```
2. **`/usr/local/cfg/autoexec.xsf`**:
   Script Extreme Scripting Facility standard richiamato automaticamente da EXOS all'avvio dopo che la configurazione primaria è operativa:
   ```text
   # ExtremeXOS Autoexec - Recovery SFP+ Porta 10 al boot
   run script bounce_port10.py
   ```

---

## 3. Fasi Operative

### Fase 1: Creazione Script Locali nel Repository
* Creazione di `scripts/network/exos/bounce_port10.py` e `scripts/network/exos/autoexec.xsf`.

### Fase 2: Implementazione Playbook Ansible Permanente
* Creazione di `ansible/playbooks/infrastructure/exos_port10_boot_recovery.yml` conforme alle regole IaC (`ansible_network_os=extreme.exos.exos`).
* Distribuzione dei file su EXOS tramite SCP sicuro (`id_rsa_extreme`).

### Fase 3: Esecuzione Playbook e Verifica Presenza File
* Esecuzione del playbook Ansible.
* Ispezione della memoria flash di EXOS (`ls`) e verifica dei permessi.

### Fase 4: Consolidamento Documentale & Knowledge Base
* Aggiornamento di `Network_Registry.md`, `todo.md` e `GEMINI.md`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 3 / Validazione Test-Driven Flash e Interprete Python
- **Ultima Azione Completata**: Playbook Ansible `exos_port10_boot_recovery.yml` eseguito con successo (6/6 task ok, `autoexec.xsf` e `bounce_port10.py` caricati su EXOS).
- **Prossimo Passo Operativo**: Consolidamento documentale o test controllato a caldo (opzionale).
- **Blocchi/Decisioni Pendenti**: Nessun blocco; in attesa di eventuale richiesta di test live a caldo da parte dell'utente.
