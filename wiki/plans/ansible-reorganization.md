---
title: "Riorganizzazione Playbook e Segreti Ansible per Sistema"
status: archived
certified_for_ai: false
resolved: true
resolved_at: 2026-07-05
date: 2026-07-01
tags:
  - "#ansible"
  - "#refactoring"
  - "#opnsense"
  - "#plan"
---

# Piano: Riorganizzazione Playbook e Segreti Ansible per Sistema

Questo piano descrive la ristrutturazione della cartella `ansible/` per organizzare i playbook in sottodirectory per sistema ed adottare una struttura di variabili ibrida (comune + specifica).

## 🗺️ Nuova Struttura Cartelle Proposta

```text
ansible/
├── playbooks/
│   ├── cloudflare/
│   │   ├── cloudflare_sync.yml
│   │   └── delete_tunnel_overrides.yml
│   ├── infrastructure/
│   │   ├── setup_ups.yml
│   │   └── shutdown_lab.yml
│   ├── kubernetes/
│   │   ├── cleanup_old_services.yml
│   │   ├── deploy_xray_secret.yml
│   │   └── fix_minio_dns.yml
│   ├── opnsense/
│   │   ├── opnsense_adblock_automation.yml
│   │   ├── opnsense_portforward.yml
│   │   ├── opnsense_sync_dhcp.yml
│   │   ├── opnsense_sync_dns.yml
│   │   └── restart_unbound.yml
│   └── truasnas/
│       └── truenas_nvme_setup.yml
└── vars/
    ├── common_secrets.yml        # Cifrato (Cloudflare, Telegram, GitHub, SSH Key)
    ├── opnsense_secrets.yml      # In chiaro (api_key, api_secret di OPNsense)
    ├── kubernetes_secrets.yml    # Cifrato (MinIO, Grafana, n8n, Prefect DB)
    └── system_secrets.yml        # Cifrato (PBS, Switch ONTI)
```

## 🛠️ Fasi del Piano

### Fase 1: Creazione Sottodirectory e Spostamento Playbook
1. Creare le cartelle sotto `ansible/playbooks/`:
   - `cloudflare/`
   - `infrastructure/`
   - `kubernetes/`
   - `opnsense/`
   - `truenas/`
2. Spostare i file dei playbook nelle rispettive cartelle.
3. Archiviare o eliminare i backup temporanei non più necessari (es. `OLD_dhcp_reservations.yml.backup`).

### Fase 2: Suddivisione delle Variabili e Segreti
1. Utilizzando la password in `.ansible/vault_pass.txt`, decifreremo il file `ansible/vars/secrets.yml`.
2. Creeremo i nuovi file sotto `ansible/vars/`:
   - `common_secrets.yml` (Vault-cifrato)
   - `kubernetes_secrets.yml` (Vault-cifrato)
   - `system_secrets.yml` (Vault-cifrato)
3. Rimuoveremo il vecchio `ansible/vars/secrets.yml` per evitare ridondanze.

### Fase 3: Aggiornamento Percorsi e Importazione nei Playbook
Per ogni playbook spostato, aggiorneremo la direttiva `vars_files` per risalire di due livelli (`../../vars/...`) e importare la combinazione corretta di variabili comuni e specifiche.

Esempio per `ansible/playbooks/kubernetes/fix_minio_dns.yml`:
```yaml
  vars_files:
    - "../../vars/common_secrets.yml"
    - "../../vars/kubernetes_secrets.yml"
```

Esempio per `ansible/playbooks/opnsense/opnsense_sync_dns.yml`:
```yaml
  vars_files:
    - "../../vars/common_secrets.yml"
    - "../../vars/opnsense_secrets.yml"
```

### Fase 4: Validazione e Test (Dry-run)
Eseguiremo dei test in modalità dry-run (`--check`) sui principali playbook (es. sincronizzazione DNS di OPNsense e setup UPS) per assicurarci che la risoluzione delle variabili e i percorsi siano perfetti e non ci siano regressioni.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Archiviato
- **Ultima Azione Completata**: Riorganizzazione degli script principali e dei segreti Ansible conclusa con successo. Archiviazione documentale eseguita in data 2026-07-05.
- **Prossimo Passo Operativo**: Nessuno.
- **Blocchi/Decisioni Pendenti**: Nessuno.
