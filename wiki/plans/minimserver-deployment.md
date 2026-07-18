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

**Target**: Cluster GEMINI (`pindaroli.org`) · **Data**: 2026-07-17 (Aggiornato)
**Autore**: Antigravity AI Engineering

> [!IMPORTANT]
> MinimServer è un media server audio DLNA/UPnP molto efficiente, ideale per servire musica ad alta fedeltà.
> Architettura: **hostNetwork** per l'esposizione del protocollo SSDP (UDP 1900) + **NFS TrueNAS** per lo storage (/config e l'intera share media /media in sola lettura).
> Esposizione: Console Web gestita tramite **Traefik IngressRoute** e integrata nella **Homepage** (modello Lidarr).

---

## Decisioni Architetturali

| Aspetto | Scelta | Motivazione |
| :--- | :--- | :--- |
| **Immagine Docker** | `minimworld/minimserver:2.2` | Immagine ufficiale e tag stabile (serie MinimServer 2) per evitare cambi automatici di major release. |
| **Networking** | `hostNetwork: true` | DLNA/UPnP si basa su messaggi multicast SSDP (UDP 1900) su rete locale fisica; l'isolamento bridge standard di K8s impedisce il corretto discovery dei client. |
| **DNS Policy** | `ClusterFirstWithHostNet` | Richiesto quando si usa `hostNetwork: true` per permettere al pod di risolvere i nomi interni di K8s (es. coreDNS). |
| **Libreria `/media`** | PVC `servarr-jellyfin-media` (Read-Only) | Monta in sola lettura l'intera share media di TrueNAS `/mnt/oliraid/arrdata/media`, permettendo a MinimServer di accedere a tutte le sottocartelle musicali (es. classica, musica generale, ecc.). |
| **Storage `/config`** | PVC 1Gi via `csi-nfs-stripe-arr-conf` | Persiste lo stato del database di MinimServer in una directory separata e isolata sotto `/mnt/stripe/k8s-arr` gestita in automatico tramite StorageClass NFS (`servarr-minimserver`). |
| **Esposizione Console** | Traefik IngressRoute (`pindaroli-wildcard-tls`) | La porta di gestione HTTP 9790 viene esposta su `minimserver.pindaroli.org` (protetta da OAuth2 Proxy) e `minimserver-internal.pindaroli.org` / `minimserver` (senza autenticazione per uso interno). |
| **Dimensionamento** | 50m CPU (500m Limit), 256Mi RAM (512Mi Limit) | Ottimizzato per massimo 4 client DLNA paralleli senza transcodifica attiva (streaming diretto di FLAC/ALAC). |

---

## Architettura Logica

```
MinimServer Pod (namespace: arr, in hostNetwork mode)
  ├── Porta HTTP (TCP 9790)   → Web UI di gestione console
  │                              ├── Esposto via Traefik IngressRoute su minimserver.pindaroli.org (Esterno, OAuth2)
  │                              └── Esposto via Traefik IngressRoute su minimserver-internal.pindaroli.org / minimserver (Interno)
  ├── Porta Status (TCP 9791) → Pagina di stato interna
  ├── Porta SSDP (UDP 1900)   → Broadcast DLNA/UPnP (diretto sulla LAN fisica)
  ├── /config                 → PVC NFS (NFS Stripe Config Share: /mnt/stripe/k8s-arr)
  └── /media (Read-Only)      → PVC NFS (NFS Media: /mnt/oliraid/arrdata/media)
```

---

## File da Creare (in pindaroli-arr-helm)

Creare la directory `charts/servarr/templates/minimserver/` con la seguente struttura:

- `deployment.yaml` · *Usa hostNetwork: true e DNS Policy per hostNet*
- `pvc.yaml` · *PVC opzionale per la configurazione se non si usa existingClaim*
- `service.yaml` · *Servizio ClusterIP standard per porte 9790 e 9791*
- `serviceaccount.yaml` · *ServiceAccount standard associato*

---

## File da Modificare

| File | Modifica |
| :--- | :--- |
| `charts/servarr/values.yaml` | Aggiungere la sezione delle variabili di default per `minimserver` (con Ingress disabilitato nel chart). |
| `servarr/arr-values.yaml` (in `k8s-lab`) | Configurare i valori reali di deploy (abilitazione, risorsa limit, PVC configurazione e associazione PVC media generale). |
| `traefik/all-arr-ingress-routes.yaml` (in `k8s-lab`) | Aggiungere la risorsa `IngressRoute` di Traefik per esporre MinimServer su porta 9790 con TLS ed eventuale middleware OAuth2. |
| `rete.json` (in `k8s-lab`) | Aggiungere gli alias `minimserver` e `minimserver-internal` sotto `traefik-lb` per la risoluzione DNS. |
| `homepage/homepage.yaml` | Aggiungere MinimServer nel gruppo "Media" puntando a `https://minimserver.pindaroli.org`. |
| `homepage/homepage-local.yaml` | Aggiungere MinimServer nel gruppo "Media" puntando a `https://minimserver-internal.pindaroli.org`. |

---

## Dettaglio delle Rotte Traefik (`all-arr-ingress-routes.yaml`)

```yaml
---
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: minimserver-ingress-route
  namespace: arr
spec:
  entryPoints:
    - websecure
  routes:
    # Accesso Esterno protetto da OAuth2
    - match: Host(`minimserver.pindaroli.org`)
      kind: Rule
      services:
        - name: servarr-minimserver
          port: 9790
      middlewares:
        - name: oauth2-auth
          namespace: traefik
    # Accesso Interno libero
    - match: Host(`minimserver`) || Host(`minimserver-internal.pindaroli.org`)
      kind: Rule
      services:
        - name: servarr-minimserver
          port: 9790
  tls:
    secretName: pindaroli-wildcard-tls
```

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
      existingClaim: "servarr-jellyfin-media"
      subPath: ""
      mountPath: "/media"

  env:
    PUID: "1000"
    PGID: "1000"
    TZ: "Europe/Rome"
```

---

## Ordine di Esecuzione

- [x] **Fase 1: Approvazione Piano**
  - [x] Approvazione del piano di implementazione da parte dell'utente.
- [x] **Fase 2: Sviluppo Helm (in pindaroli-arr-helm)**
  - [x] Creazione dei template K8s in `charts/servarr/templates/minimserver/`.
  - [x] Aggiunta dei default in `charts/servarr/values.yaml` e versione incrementata a `1.6.0`.
  - [x] Esecuzione `helm lint charts/servarr` e validazione tramite `helm template`.
  - [x] Commit & Push sul repo `pindaroli-arr-helm` e rilascio versione `1.6.0`.
- [x] **Fase 3: Configurazione K8s-Lab**
  - [x] Aggiunta della configurazione attiva in `servarr/arr-values.yaml`.
  - [x] Aggiunta delle rotte IngressRoute di Traefik in `traefik/all-arr-ingress-routes.yaml`.
  - [x] Aggiunta dei widget in `homepage/homepage.yaml` e `homepage-local.yaml`.
  - [x] Registrazione record DNS per `minimserver` e `minimserver-internal` in `rete.json` e validazione della rete.
- [x] **Fase 4: Deploy & Validazione**
  - [x] Esecuzione di `helm upgrade --install servarr pindaroli/servarr -f servarr/arr-values.yaml -n arr` con il pacchetto ufficiale `1.6.0`.
  - [x] Applicazione dei manifesti di Traefik IngressRoute.
  - [x] Monitoraggio dello stato del Pod (`servarr-minimserver` Running 1/1).
  - [x] Ispezione del mount `/media` (accesso completo a tutte le sottocartelle del NAS).
  - [x] Verifica HTTP su porta 9790 (esito HTTP 302 OK).

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato 🎉
- **Ultima Azione Completata**: Deploy ed esecuzione con successo di MinimServer (chart version `1.6.0`, namespace `arr`), IngressRoute Traefik e widget Homepage.
- **Prossimo Passo Operativo**: Nessuno (Servizio operativo in produzione).
- **Blocchi/Decisioni Pendenti**: Configurazione iniziale di `contentDir` da parte dell'utente tramite la Web UI su `minimserver-internal.pindaroli.org` o tramite MinimWatch.


---
*Piano redatto da Antigravity AI Engineering — 2026-07-17*
