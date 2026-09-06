---
title: "Automazione Rilevazione Dati SMART via Ansible"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-06
tags:
  - "#plan"
  - "#ansible"
  - "#storage"
  - "#monitoring"
  - "#truenas"
  - "#proxmox"
---

# Piano Operativo: Automazione Rilevazione Dati S.M.A.R.T. via Ansible

Questo piano definisce la progettazione e l'implementazione di un playbook Ansible centralizzato per la raccolta automatica, l'analisi preventiva e l'alerting dello stato di salute dei dischi fisici (**S.M.A.R.T.**) sui nodi dell'infrastruttura homelab (nodo Bare Metal [[TrueNAS]] e hypervisor [[Proxmox]] `pve1`, `pve2`, `pve3`).

---

## 🎯 Obiettivi
1. **Raccolta Centralizzata**: Eseguire via Ansible (`smartctl --json`) la rilevazione non invasiva su tutti i drive (SATA HDD, SSD SATA, NVMe) presenti nell'inventory.
2. **Parsing & Threshold Guard**: Valutare automaticamente attributi critici (settori riallocati `Reallocated_Sector_Ct`, settori pendenti `Current_Pending_Sector`, temperatura, usura SSD/NVMe `percentage_used`).
3. **Reportistica & Alerting**: Generare un report diagnostico sintetico su controller locale ed eventuale notifica preventiva in caso di anomalie fisiche.
4. **Interoperabilità**: Supportare l'inoltro delle telemetrie verso l'app Scrutiny (InfluxDB) o integration pipeline.

---

## 📋 Fasi di Implementazione

### Fase 1: Discovery e Inventario Dischi
- [ ] Definizione del playbook `ansible/playbooks/monitoring/collect_smart_data.yml`.
- [ ] Identificazione dinamica dei drive tramite `smartctl --scan -j` su TrueNAS e Proxmox.
- [ ] Filtraggio dei dischi fisici escludendo dispositivi virtuali (es. loopback, zvols, dischi virtuali QEMU).

### Fase 2: Estrazione Metriche & Parsing JSON
- [ ] Estrazione telemetria grezza tramite `smartctl -a -j /dev/sdX` e `smartctl -a -j /dev/nvmeXn1`.
- [ ] Strutturazione del modulo Ansible / Jinja2 filter per normalizzare i dati tra dischi ATA/SATA e NVMe.
- [ ] Mappatura attributi critici:
  - `smart_status.passed` (Health Check complessivo)
  - `reallocated_sector_ct` (ID 5 per HDD)
  - `current_pending_sector` (ID 197 per HDD)
  - `temperature.current`
  - `nvme_smart_health_information_log.percentage_used` (per NVMe)
  - `power_on_time.hours`

### Fase 3: Logica di Alerting e Generazione Report
- [ ] Regole di soglia:
  - Fallimento se `smart_status.passed == false`.
  - Warning se `reallocated_sector_ct > 0` o `current_pending_sector > 0`.
  - Warning se `temperature > 50°C` su HDD o `> 65°C` su NVMe.
- [ ] Creazione template report Markdown (`ansible/templates/smart_health_report.j2`) salvato in reportistica locale.

### Fase 4: Integrazione Scrutiny / Semaphore
- [ ] Invio opzionale delle metriche estratte all'endpoint HTTP/InfluxDB di Scrutiny (`10.10.10.50:8086`).
- [ ] Integrazione del job nel motore di automazione Semaphore (`ansible-engine` LXC 200).

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 1 / Pianificazione & Setup
- **Ultima Azione Completata**: Creazione piano e censimento in `todo.md`
- **Prossimo Passo Operativo**: Redazione del playbook `collect_smart_data.yml` su `ansible/playbooks/monitoring/`
- **Blocchi/Decisioni Pendenti**: Nessun blocco; in attesa di richiesta avvio implementazione
