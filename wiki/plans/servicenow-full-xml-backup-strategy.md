---
title: Piano Backup XML Nativo Automatico e Completo per ServiceNow PDI
status: active
certified_for_ai: true
created_at: 2026-08-03
tags:
  - servicenow
  - backup
  - xml
  - automation
---

# 📦 Piano per l'Automazione del Backup XML Nativo Completo di ServiceNow

## 🎯 Obiettivo
Realizzare una procedura automatizzata in Python (`scripts/sn/dump_sn_xml.py`) che scarichi **in modo dinamico e completo** tutti i file **XML Nativi Ufficiali di ServiceNow** per tutte le tabelle di configurazione, credenziali, MID Server, ITOM, CMDB e personalizzazioni dell'istanza (`dev395227`), senza dover mai aggiornare lo script a mano in futuro.

---

## 🛠️ Architettura e Funzionamento dello Script (`scripts/sn/dump_sn_xml.py`)

### 1. Scoperta Dinamica delle Tabelle (`sys_db_object`)
Lo script interrogherà la tabella dizionario nativa di ServiceNow (`sys_db_object`) per identificare automaticamente tutte le tabelle appartenenti alle macro-categorie di configurazione:
- **ITOM & Discovery**: `ecc_agent`, `ecc_agent_property`, `discovery_credentials`, `discovery_status`, ecc.
- **Configurazioni & Proprietà di Sistema**: `sys_properties`, `sys_oauth_client`, `sys_user`, `sys_user_group`, `sys_user_role`.
- **Script & Personalizzazioni**: `sys_script`, `sys_script_include`, `sys_ui_policy`, `sys_ui_action`.
- **CMDB & Topologia**: `cmdb_ci`, `cmdb_ci_kubernetes_cluster`, `cmdb_ci_kubernetes_node`, `cmdb_ci_kubernetes_pod`, `cmdb_ci_kubernetes_service`.

### 2. Export XML Nativo Ufficiale ServiceNow (`UNLOAD.xml`)
Per ogni tabella individuata, lo script effettuerà il download usando l'endpoint nativo di export di ServiceNow:
`https://dev395227.service-now.com/<NOME_TABELLA>_list.do?UNLOAD`

Questo genera per ciascuna tabella un file `.xml` nativo identico a quello scaricato manualmente facendo clic destro ➔ *Export ➔ XML*.

### 3. Struttura dei File di Backup Locali
Tutti i file XML scaricati verranno salvati in modo ordinato nella cartella:
- `scripts/sn/backups/xml_latest/<NOME_TABELLA>.xml`
- Archivio ZIP compresso con timestamp per storico: `scripts/sn/backups/sn_xml_backup_YYYYMMDD_HHMMSS.zip`

---

## 🔄 Procedura di Ripristino da Zero (In caso di reset PDI)

Se la PDI viene resettata o ne viene assegnata una nuova:
1. Aprire la nuova istanza ServiceNow.
2. Su qualsiasi tabella, fare clic destro sull'intestazione di colonna ➔ **Import XML**.
3. Selezionare i file `.xml` dalla cartella `scripts/sn/backups/xml_latest/`.
4. ServiceNow ripristinerà istantaneamente i record mantenendo intatti tutti i `sys_id` e i parametri originali.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: [Stesura Piano Backup XML Dinamico]
- **Ultima Azione Completata**: Redazione del piano per l'automazione del dump XML nativo dinamico in `wiki/plans/servicenow-full-xml-backup-strategy.md`.
- **Prossimo Passo Operativo**: Creare lo script `scripts/sn/dump_sn_xml.py` ed eseguirlo per generare il primo backup XML completo.
- **Blocchi/Decisioni Pendenti**: In attesa di approvazione del piano da parte dell'utente.
