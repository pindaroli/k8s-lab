---
status: active
certified_for_ai: true
---

# Piano di Deployment per Hermes Agent in Kubernetes (k8s-lab) - REVISIONATO v3

Questo documento illustra il piano dettagliato per il deployment di **Hermes Agent** nel cluster Kubernetes (`k8s-lab`), basato sul chart Helm `jyje/hermes-agent-helm`. Questa revisione (v3) rafforza ulteriormente le policy di sicurezza garantendo che nessun dato sensibile sia in chiaro nel repository.

## 1. Storage & TrueNAS

- **Azione:** Creazione del dataset ZFS in `/mnt/stripe/hermes-agent` tramite MCP TrueNAS.
- **Integrazione K8s:** Configurazione PV e PVC NFS in modalità `ReadWriteMany` agganciati al nuovo dataset.

## 2. Iniezione Segreti e Zero Plaintext (SOPS)

**In accordo con le Golden Rules:**
- **Zero Plaintext:** Nessuna password, token o utente verrà salvato in chiaro nei file manifest (es. `values.yaml`).
- **Strategia SOPS Universale:** Tutte le credenziali necessarie al deployment saranno criptate in file SOPS all'interno di `secrets-sops/hermes-secrets.enc.yaml`. Questo includerà:
  - Chiave API DeepSeek.
  - Credenziali di autenticazione base/Web UI per Hermes (Utente e Password).
  - Qualsiasi token necessario ai server MCP (es. API key per TrueNAS o token GitHub).
- **Iniezione (Kubeconfig & Talosconfig):** I file fisici come `kubeconfig` e `talosconfig` verranno parimenti criptati in SOPS e montati come volumi Secret o come variabili d'ambiente direttamente nei container sidecar o principale.

## 3. Architettura Container MCP (Sidecar)

- **Strategia:** Deployare gli MCP server come container **sidecar** all'interno dello stesso Pod di Hermes.
- **Azione:** Creazione delle definizioni dei sidecar container all'interno del `values.yaml` sfruttando i costrutti del chart (o patch Kustomize/Helm), facendo in modo che ogni sidecar legga le proprie credenziali in modo sicuro dai Secret SOPS descritti al punto 2.

## 4. Rete, Ingress e Interfaccia Web (Accesso Esterno Parziale)

- **Configurazione Multi-Ingress:** 
  - **Ingress Interno (`hermes-internal.pindaroli.org`):** Per chiamate API locali e l'uso fiduciario in rete locale.
  - **Ingress Esterno (`hermes.pindaroli.org`):** Puntato specificamente alla console Web UI di Hermes.
- **Sicurezza:**
  - L'Ingress Esterno è protetto tramite il middleware **OAuth2 Proxy** e instradato in modo da bloccare gli endpoint API core (`/api/*`), permettendo solo le route necessarie all'interfaccia utente.
- **Azione:** 
  - Aggiornamento `rete.json` con i nuovi DNS alias.
  - Configurazione DNS/Cloudflare e host override su OPNsense.
  - Implementazione dei due blocchi Ingress nel file `values.yaml`.
  - Aggiunta in `homepage.yaml`.

## 5. StatefulSet vs Deployment per Hermes

- **Decisione:** **Deployment** confermato, per mantenere il paradigma stateless e l'alta resilienza tipica della nostra infrastruttura basata su storage condiviso NFS.

## 6. Sottopiano: Gestione Multi-Tenant RAG e "Isole" Wiki

**Hook Architetturale:**
- I chunk testuali in `postgres-main` (via pgvector) conterranno una colonna di metadati `island_id` o `project_id`.
- Sfrutteremo l'architettura Deployment Stateless (vedi Punto 5) per la **Multi-Istanziazione K8s**: istanzieremo più deployment di Hermes isolati e indipendenti (es. `hermes-k8s-agent`, `hermes-personal-agent`). 
- Ogni istanza monterà il proprio ConfigMap e le proprie credenziali SOPS per istruire il sidecar MCP RAG a interrogare solo la specifica "isola" di competenza (`island_id=k8s-lab-wiki`), garantendo zero contaminazione del contesto tra agenti diversi.

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Setup Storage e Storage Provider
- **Ultima Azione Completata**: Piano di implementazione approvato e persistito nel Wiki.
- **Prossimo Passo Operativo**: Creazione del dataset ZFS `stripe/hermes-agent` tramite MCP TrueNAS.
- **Blocchi/Decisioni Pendenti**: Nessuno.
