---
title: "Refactoring Alerting Telegram su Supergruppo con Topic Dedicati"
type: plan
status: draft
certified_for_ai: true
created_at: 2026-10-26
tags:
  - "#alerting"
  - "#telegram"
  - "#automation"
  - "#monitoring"
  - "#sops"
---

# Piano: Refactoring Alerting Telegram su Supergruppo con Topic Dedicati

## 1. Obiettivo e Motivazione
Attualmente l'intero alerting dell'Homelab (`scripts/infrastructure/utils.sh`, script `lab_mode_*`, `Alertmanager`, webhook dei container e script cron) invia messaggi piatti ad una singola chat Telegram (`chat_id` memorizzato in `secrets-sops/alertmanager-telegram.enc.yaml`).

L'obiettivo è migrare a un'architettura **Telegram Supergroup con Topic (Forum Mode)** in modalità bacheca ad amministratore singolo (sola lettura per i membri, scrittura riservata al Bot). Questa struttura permette:
- **Isolamento per canale logico**: fine del feed unico caotico con alert critici mescolati ad avvisi di routine.
- **Gestione notifiche gerarchica**: mutare i topic a bassa priorità o alto volume (es. download completati o sync orari) e mantenere notifiche push/audio attive sui topic critici (failover, spegnimenti, errori K8s).
- **Anti-spam & Zero-Maintenance**: permessi dei membri ristretti globalmente a sola lettura (`can_send_messages = false`), bot amministratore unico.

---

## 2. Architettura & Pattern di Riferimento

### Modello Telegram Supergroup
- **Supergruppo Telegram**: creato con flag forum `is_forum = true`.
- **RBAC Telegram Sola Lettura**:
  - `setChatPermissions` con permessi membro disabilitati (`can_send_messages=false`, `can_send_media=false`, ecc.).
  - Bot con permessi amministratore: gestione topic, invio messaggi, pinning.
- **Indirizzamento**:
  - Ogni invio verso un topic richiede il parametro `message_thread_id`.
  - Il thread `General` (ID nullo o default) rimane riservato a comunicazioni di servizio o setup iniziale.

### Matrice di Routing & Topic Proposti (Da finalizzare prima dell'esecuzione)
La lista esatta dei topic verrà concordata e validata prima di avviare il provisioning:
1. `📢 Annunci & Mode Switch`: Cambio stato homelab (`lab_mode_full`, `lab_mode_eco`, `lab_mode_off`), manutenzioni pianificate.
2. `🚨 Alert Critici & Errori`: Notifiche di emergenza, fallimento script gerarchici, blackout, alert P1.
3. `⚙️ Infrastruttura & Nodi`: Proxmox VE, Talos K8s, VM, OPNsense, bonding di rete.
4. `📦 Storage & Backup`: TrueNAS, snapshot ZFS, PBS backup, scrub pool.
5. `🎬 Media & Automazioni`: Notifiche Servarr, qBittorrent, ingestion video, task di download.

---

## 3. Gestione della Configurazione e Segreti
I riferimenti ai topic saranno integrati in modo dichiarativo e sicuro:
- **Segreto SOPS**: Aggiornamento di `secrets-sops/alertmanager-telegram.enc.yaml` con:
  - `token`: Token del Bot Telegram esistente.
  - `supergroup_chat_id`: Nuovo ID chat supergruppo (`-100...`).
  - Mappatura chiavi JSON o variabili dedicate per i singoli `thread_id` (es. `topic_infra_id`, `topic_alerts_id`, ecc.).
- **Compatibilità retroattiva**: Il wrapper manterrà un topic predefinito di fallback qualora uno script non specifichi il target esatto.

---

## 4. Fasi di Implementazione

### Fase 1: Automazione Setup Telegram (Script One-Off)
- Sviluppo di uno script Python/bash (`scripts/alerting/setup_telegram_supergroup.py`) che utilizza la Telegram Bot API:
  - Verifica/creazione del Supergruppo abilitato a forum.
  - Esecuzione `createForumTopic` per ciascun topic concordato con relative icone custom.
  - Configurazione `setChatPermissions` per blindare la chat in sola lettura.
  - Estrazione dei `message_thread_id` creati e output pronto per l'aggiornamento SOPS.

### Fase 2: Refactoring del Wrapper di Notifica (`utils.sh`)
- Aggiornamento della funzione canonica `send_telegram()` in `scripts/infrastructure/utils.sh`:
  - Firma estesa: `send_telegram <messaggio_html> [titolo_opzionale] [topic_target] [silent_mode]`
  - Lettura dinamica dei `thread_id` decifrati da SOPS o esposti via env.
  - Risoluzione automatica del topic in base all'evento se non specificato esplicitamente.

### Fase 3: Adeguamento Script Infrastruttura & Mode Switch
- Aggiornamento delle chiamate `send_telegram` nei file:
  - `scripts/infrastructure/lab_mode_full.sh`
  - `scripts/infrastructure/lab_mode_eco.sh`
  - `scripts/infrastructure/lab_mode_off.sh`
  - `scripts/infrastructure/lxc-steam-hook.sh`
  - Normalizzatori e notificatori media.

### Fase 4: Integrazione K8s Alertmanager (Se applicabile)
- Aggiornamento del secret K8s `monitoring/alertmanager-telegram-secret`.
- Configurazione dei receiver Alertmanager con `message_thread_id` per indirizzare gli allarmi Prometheus sul topic dedicato (`🚨 Alert Critici & Errori` o `⚙️ Infrastruttura`).

### Fase 5: Validazione e Test-Driven Execution
- Invio test su ciascun topic via script e verifica del recapito su client mobile/desktop.
- Test permessi membro per verificare l'impossibilità di postare da account standard.
- Test fallback silente vs notifica con suono su alert P1.

---

## 5. Criteri di Accettazione e Verifica
- [ ] Il Bot Telegram crea/amministra i topic sul Supergruppo.
- [ ] Gli utenti standard non possono inviare messaggi in nessun topic.
- [ ] Gli script `lab_mode_*` postano sul topic dedicato senza errori.
- [ ] Il secret SOPS contiene e protegge token e thread IDs.
- [ ] Nessun messaggio cade nel vuoto se inviato da un vecchio script senza `topic_target` (fallback automatico sul topic generale).

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 0 (Definizione & Planning)
- **Ultima Azione Completata**: Redazione del piano ufficiale in `wiki/plans/telegram-topic-supergroup-alerting-refactoring.md`.
- **Prossimo Passo Operativo**: Definire la lista finale dei Topic prima di passare all'esecuzione dello script di setup.
- **Blocchi/Decisioni Pendenti**: Scelta finale dei nomi/icone dei Topic da creare su Telegram.
