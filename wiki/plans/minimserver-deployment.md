---
title: "Piano: Deployment di MinimServer"
type: plan
status: active
certified_for_ai: true
created_at: 2026-07-02
tags:
  - "#plan"
  - "#network"
  - "#storage"
  - "#talos"
  - "#opnsense"
  - "#security"
---

# Piano: Deployment di MinimServer

**Target**: Cluster GEMINI (`pindaroli.org`) · **Data**: 2026-07-02
**Autore**: Antigravity AI Engineering

> [!IMPORTANT]
> MinimServer è un media server audio DLNA/UPnP molto efficiente, ideale per servire musica classica ad alta fedeltà.
> Architettura: **hostNetwork** per l'esposizione del protocollo SSDP (UDP 1900) + **NFS TrueNAS** per lo storage (/config e libreria musicale /music).

---

## Decisioni Architetturali

| Aspetto | Scelta | Motivazione |
| :--- | :--- | :--- |
| **Immagine Docker** | `minimworld/minimserver:2.2` | Immagine ufficiale e tag stabile (serie MinimServer 2) per evitare cambi automatici di major release. |
| **Networking** | `hostNetwork: true` | DLNA/UPnP si basa su messaggi multicast SSDP (UDP 1900) su rete locale fisica; l'isolamento bridge standard di K8s impedisce il corretto discovery dei client. |
| **DNS Policy** | `ClusterFirstWithHostNet` | Richiesto quando si usa `hostNetwork: true` per permettere al pod di risolvere i nomi interni di K8s (es. coreDNS). |
| **Libreria `/music`** | PVC `servarr-classical-media` con `subPath: library` (Read-Only) | Monta in sicurezza solo i file finali della musica classica provenienti dal dataset TrueNAS `/mnt/oliraid/arrdata/classical/library`. |
| **Storage `/config`** | PVC 1Gi via `csi-nfs-stripe-arr-conf` (Opzione A) | Persiste lo stato del database di MinimServer in una directory separata e isolata sotto `/mnt/stripe/k8s-arr` gestita in automatico tramite StorageClass NFS. |
| **Dimensionamento** | 50m CPU (500m Limit), 256Mi RAM (512Mi Limit) | Ottimizzato per massimo 4 client DLNA paralleli senza transcodifica attiva (streaming diretto di FLAC/ALAC). |

---

## Architettura Logica

```
MinimServer Pod (namespace: arr, in hostNetwork mode)
  ├── Porta HTTP (TCP 9790)   → Web UI di gestione console
  ├── Porta Status (TCP 9791) → Pagina di stato interna
  ├── Porta SSDP (UDP 1900)   → Broadcast DLNA/UPnP (diretto sulla LAN fisica)
  ├── /config                 → PVC NFS (NFS Stripe Config Share: /mnt/stripe/k8s-arr)
  └── /music (Read-Only)      → PVC NFS (NFS Classical Media: /mnt/oliraid/arrdata/classical/library)
```

---

## File da Creare (in pindaroli-arr-helm)

Creare la directory `charts/servarr/templates/minimserver/` con la seguente struttura:

- `deployment.yaml` · *Usa hostNetwork: true e DNS Policy per hostNet*
- `pvc.yaml` · *PVC opzionale per la configurazione se non si usa existingClaim*
- `service.yaml` · *Servizio ClusterIP di tipo headless o standard per porte 9790 e 9791*
- `ingress.yaml` · *Definizione Ingress per esporre la console a minimserver.local*
- `serviceaccount.yaml` · *ServiceAccount standard associato*

---

## File da Modificare

| File | Modifica |
| :--- | :--- |
| `charts/servarr/values.yaml` | Aggiungere la sezione delle variabili di default per `minimserver`. |
| `servarr/arr-values.yaml` (in `k8s-lab`) | Configurare i valori reali di deploy (abilitazione, risorsa limit, PVC configurazione e associazione PVC classica). |
| `rete.json` (in `k8s-lab`) | Aggiungere l'alias `minimserver` a Traefik per la risoluzione di `minimserver.local` o `minimserver-internal.pindaroli.org`. |
| `homepage/homepage.yaml` | Aggiungere l'applicazione MinimServer nella dashboard del cluster. |

---

## Modello dei Valori di Default (values.yaml)

```yaml
minimserver:
  enabled: false
  replicaCount: 1

  image:
    repository: minimworld/minimserver
    pullPolicy: IfNotPresent
    tag: "2.2"

  service:
    type: ClusterIP
    port: 9790
    statusPort: 9791

  ingress:
    enabled: false
    className: ""
    annotations: {}
    hosts:
      - host: minimserver.local
        paths:
          - path: /
            pathType: ImplementationSpecific

  resources:
    requests:
      cpu: 50m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi

  persistence:
    config:
      enabled: true
      storageClass: "csi-nfs-stripe-arr-conf"
      size: 1Gi
      existingClaim: ""
      accessMode: ReadWriteOnce
    media:
      enabled: true
      existingClaim: "servarr-classical-media"
      subPath: "library"
      mountPath: "/music"

  env:
    PUID: "1000"
    PGID: "1000"
    TZ: "Europe/Rome"
```

---

## Ordine di Esecuzione

- [ ] **Fase 1: Approvazione Piano**
  - [ ] Approvazione del piano di implementazione da parte dell'utente.
- [ ] **Fase 2: Sviluppo Helm (in pindaroli-arr-helm)**
  - [ ] Creazione dei template K8s in `charts/servarr/templates/minimserver/`.
  - [ ] Aggiunta dei default in `charts/servarr/values.yaml`.
  - [ ] Esecuzione `helm lint charts/servarr` e validazione tramite `helm template`.
- [ ] **Fase 3: Configurazione K8s-Lab**
  - [ ] Aggiunta della configurazione attiva in `servarr/arr-values.yaml`.
  - [ ] Registrazione record DNS per `minimserver` in `rete.json` e sync DNS con playbook Ansible.
- [ ] **Fase 4: Deploy & Validazione**
  - [ ] Esecuzione di `helm upgrade --install` dello stack `oli-arr`.
  - [ ] Monitoraggio dello stato del Pod e controllo dei log.
  - [ ] Verifica del discovery DLNA da un client locale e dell'interfaccia HTTP `/config` su porta 9790.
  - [ ] Aggiunta del widget in Homepage.

---

## Verifica

```bash
# Controlla che il pod minimserver sia Running
kubectl get pods -n arr -l app.kubernetes.io/name=minimserver

# Controlla che le porte siano in ascolto sulla rete dell'host
kubectl exec -n arr deploy/oli-arr-minimserver -- netstat -tulpn

# Controlla che la directory classica sia montata in sola lettura
kubectl exec -n arr deploy/oli-arr-minimserver -- ls -la /music
```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: In Sospeso (Fase 1 Approvata)
- **Ultima Azione Completata**: Piano di implementazione approvato dall'utente in data 2026-07-05.
- **Prossimo Passo Operativo**: Avviare lo sviluppo dei template Helm (Fase 2).
- **Blocchi/Decisioni Pendenti**: Attesa di ripresa attività su indicazione dell'utente.

---
*Piano redatto da Antigravity AI Engineering — 2026-07-02*
