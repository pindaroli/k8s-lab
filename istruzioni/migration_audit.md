# Audit Files di Progetto per Migrazione Talos

Ecco l'analisi di tutti i file e cartelle presenti nel progetto `k8s-lab`.
Li ho divisi in 3 gruppi: **Da Migrare** (tengono la configurazione attiva), **Da Archiviare/Cancellare** (script vecchi o obsoleti), e **Utilities** (da tenere "just in case").

## ✅ 1. Gruppo "CORE" (Da Migrare e Usare)
Queste cartelle contengono i manifest Kubernetes che useremo nel **Piano 04**.
*   **`servarr/`**: Contiene tutte le app (*arr*). **CRITICO**. (Nota: contiene anche `opnsense-port-forward-config.md` che è documentazione utile).
*   **`metallb/`**: Configurazione LoadBalancer. **CRITICO**.
*   **`traefik/`**: Ingress Controller e rotte. **CRITICO**.
*   **`cert-manager/`**: Gestione certificati TLS. **CRITICO**.
*   **`oauth2-proxy/`**: Autenticazione Google. **CRITICO**.
*   **`calibre/`, `homepage/`, `kasmweb/`, `n8n/`, `cloudflare/`**: Applicazioni accessorie. **MIGRARE**.
*   **`istruzioni/migration/`**: I nostri 4 piani attuali. **FONTE DI VERITÀ**.
*   **`jellyfin-external-service.yaml`**: Il nuovo file creato per Jellyfin esterno. **NUOVO**.

## ❌ 2. Gruppo "OBSOLETE" (Da Archiviare o Cancellare)
Questi file appartengono alla vecchia installazione (probabilmente MicroK8s o tentativi precedenti) e **non sono compatibili** con il nuovo cluster Talos "pulito".
*   **`install.sh`**: Script monolitico per installare tutto. Riferimenti a `microk8s`, path assoluti errati. **DA ELIMINARE** (usiamo i piani 01-04 ora).
*   **`CSI-driver/`**: Contiene vecchi manifest per NFS driver. **DA VERIFICARE** (Il piano 04 usa Helm per nfs-csi, quindi questi file manuali potrebbero essere superflui).
*   **`ansible/`**: Se usavamo Ansible per configurare i nodi Ubuntu, con Talos non serve più (è immutabile). **DA ARCHIVIARE**.
*   **`terraform/`**: Configurazione Terraform per vecchie VM o Proxmox? Se non è aggiornata a Talos, crea solo confusione. **DA VALUTARE**.
*   **`descheduler/`**: Tool avanzato per ri-bilanciare i pod. Per ora aggiunge complessità inutile. **RIMUOVERE** (lo rimetteremo se servirà).
*   **`suggestions/`**: Note sparse o idee. **ARCHIVIARE**.

## 🛠 3. Gruppo "UTILITIES" (Da Tenere)
Script utili che non dipendono dal cluster ma fanno comodo.
*   **`download_plugins.sh` / `.py`**: Scaricano plugin per qBittorrent. **TENERE**.
*   **`verify_vm_config.sh`**: Script di check generico? **TENERE**.
*   **`*.md` / `*.json`**: Documentazione (`rete.json`, `CLUSTER-OPERATIONS.md`, ecc.). **TENERE SEMPRE**.
*   **`*.cfg`**: Backup switch/router. **TENERE**.
*   **`k8s-dash.*`**: Certificati manuali? **ARCHIVIARE** (usiamo cert-manager).

---

### Azione Consigliata
Posso creare una cartella `_OLD_ARCHIVE` e spostarci dentro tutto il **Gruppo 2**?
Così la root rimane pulita solo con le cartelle che ci servono davvero per la Fase 4.
