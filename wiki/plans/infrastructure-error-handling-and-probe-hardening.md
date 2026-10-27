---
title: "Hardening Gestione Errori, Health Gate CNPG e Probe Cross-Platform"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-27
tags:
  - "#ansible"
  - "#infrastructure"
  - "#automation"
  - "#hardening"
  - "#orbstack"
---

# Piano: Hardening Gestione Errori, Health Gate CNPG e Probe Cross-Platform

## 1. Obiettivo e Motivazione
A seguito dell'audit sui pattern di soppressione cieca degli errori (`ignore_errors: true` e `|| true`) nei playbook e negli script di orchestrazione Homelab, questo piano definisce gli interventi per eliminare i punti critici di fragilità rimanenti:
1. **Eliminazione del "False Green" su PostgreSQL CNPG** in [[ensure_compute_on.yml]]: rimozione di `ignore_errors: true` al Gate 5.2 per prevenire false attestazioni di salute se il cluster database non è pronto o è degradato.
2. **Fail-Fast sull'avvio VM Talos** in [[ensure_compute_on.yml]]: rimozione di `ignore_errors: true` durante l'avvio `qm start` per segnalare tempestivamente problemi di quorum o storage ZFS bloccato su Proxmox VE.
3. **Ottimizzazione Connect Timeout macOS BSD netcat** in [[lab_mode_status.sh]]: adozione del flag `-G 1` su Darwin (`macOS`) per impedire il blocco di 75 secondi del kernel sui nodi fisici spenti.
4. **Allineamento Nomi Container Failover** in [[lab_mode_status.sh]]: correzione dei filtri Docker con i nomi reali dei container (`hermes-main`, `litellm`).

---

## 2. Dettaglio degli Interventi

### 2.1 [ensure_compute_on.yml](file:///Users/olindo/prj/k8s-lab/ansible/playbooks/infrastructure/ensure_compute_on.yml)
- **Fase 1.5**: Rimuovere `ignore_errors: true` dal task di verifica e avvio automatico Talos VM. Se Proxmox fallisce l'avvio, il playbook deve arrestarsi immediatamente.
- **Gate 5.2**: Rimuovere `ignore_errors: true`. Il ciclo di polling `until: cnpg_status.stdout == "Cluster in healthy state"` deve avere valore vincolante prima della notifica Telegram di successo.

### 2.2 [lab_mode_status.sh](file:///Users/olindo/prj/k8s-lab/scripts/infrastructure/lab_mode_status.sh)
- **Probe TCP Cross-Platform**: Rilevare `uname -s`. Su `Darwin`, usare `nc -z -w 1 -G 1` (imposta sia il connection timeout sia l'inactivity timeout a 1s). Su Linux, mantenere `nc -z -w 1`.
- **Filtri Docker**: Sostituire `hermes-agent` e `litellm-proxy` con `hermes-main` e `litellm` per riflettere fedelmente `docker-compose.yaml` di OrbStack.

---

## 3. Piano di Test e Verifica
1. **Verifica Sintassi Ansible**:
   ```bash
   ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_compute_on.yml --syntax-check
   ```
2. **Benchmark di Esecuzione Diagnostica**:
   ```bash
   time bash scripts/infrastructure/lab_mode_status.sh --raw
   ```
   Verificare esecuzione sotto i 2.5 secondi a rack spento.
3. **Verifica Verbose di Stato**:
   ```bash
   bash scripts/infrastructure/lab_mode_status.sh -v
   ```
4. **Validazione di Rete e Wiki**:
   ```bash
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: COMPLETATO ✅
- **Ultima Azione Completata**: Applicate modifiche a `ensure_compute_on.yml` e `lab_mode_status.sh`, verificata sintassi Ansible e benchmark diagnostico completato in 1.14s con esito positivo al 100%.
- **Prossimo Passo Operativo**: Nessuno, piano concluso.
- **Blocchi/Decisioni Pendenti**: Nessuno.
