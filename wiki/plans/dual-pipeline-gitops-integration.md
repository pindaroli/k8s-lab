# Wiki Plan: Classical Homelab Integration & GitOps Orchestration

> [!IMPORTANT]
> **Stato**: 🔄 **PARZIALMENTE COMPLETATO / CONSOLIDATO (2026-05-18)**
> **Target**: Cluster GEMINI (`pindaroli.org`) · **Ultimo Aggiornamento**: 2026-05-18 23:05
> **Obiettivo**: Questo piano unificato definisce sia il rilascio Helm GitOps sia l'infrastruttura di contorno per l'Isola Classica segregata (`jellyfin-classic` e `lidarr-classic`), garantendo la coerenza con la Dual-Pipeline.
>
> ### 📌 Consolidamento Stato (Fine Sessione 2026-05-18)
> - **Storage PV/PVC**: **COMPLETATO** (`csi-nfs-stripe-arr-conf` e dataset classici agganciati).
> - **GitOps Workloads (Lidarr/Jellyfin Classic)**: **COMPLETATO** (Helm upgrade eseguito e Pods attivi e stabili).
> - **Infrastruttura di Ingresso (Traefik IngressRoutes)**: **COMPLETATO** (Dual-Route con OAuth2 per l'esterno e Direct-access per la LAN).
> - **DNS Split-Horizon (OPNsense)**: **COMPLETATO** (Nuovi domini classici interni/esterni mappati in `rete.json` e propagati su Unbound via Ansible).
> - **Presentation Layer (Homepage)**: **COMPLETATO** (Nuovi pannelli per Lidarr Classic e Jellyfin Classic inseriti e visibili).
>
> ### 🚀 Prossimi Passi (Domani)
> 1. Configurazione Categoria `lidarr-classic` su qBittorrent (share nfs `/mnt/oliraid/arrdata/classical/staging`).
> 2. Associazione tag `classical-indexers` su Prowlarr.
> 3. Disabilitazione "Completed Download Handling" su `lidarr-classic`.
> 4. Deploy del ConfigMap per `options.xml` di `jellyfin-classic` e aggancio del volume.
> 5. Implementazione e test dello script di riconciliazione/unmonitoring `segregate_classical.py` come post-import hook in Beets.

---

## 🗺️ Mappa delle Risorse & Relazioni

```mermaid
graph TD
    subgraph Storage [TrueNAS & K8s Storage]
        nfs["TrueNAS ZFS: /mnt/oliraid/arrdata/classical"]
        pv["PV: pv-classical-media"]
        pvc["PVC: servarr-classical-media"]
        nfs --> pv --> pvc
    end

    subgraph Pods [Workloads Segregati 1:1]
        j_classic["Pod: jellyfin-classic"]
        l_classic["Pod: lidarr-classic"]
        pvc -->|Mount Read-Only /media/music/classical| j_classic
        pvc -->|Mount Read-Write /media (staging)| l_classic
    end

    subgraph Traefik [Traefik Routing & Sicurezza]
        ir_ext_j["IngressRoute Ext: jellyfin-classic.pindaroli.org"]
        ir_int_j["IngressRoute Int: jellyfin-classic-internal.pindaroli.org"]
        ir_ext_l["IngressRoute Ext: lidarr-classic.pindaroli.org"]
        ir_int_l["IngressRoute Int: lidarr-classic-internal.pindaroli.org"]

        ir_ext_j -->|oauth2-auth| j_classic
        ir_int_j --> j_classic
        ir_ext_l -->|oauth2-auth| l_classic
        ir_int_l --> l_classic
    end

    subgraph OPNsense [DNS Split-Horizon]
        dns["OPNsense Unbound DNS"]
        dns -->|Internal IP| VIP[Traefik VIP: 10.10.20.254]
    end
```

---

## Pre-Condizione: Final Sync & Swap (Modern Music — Pop/Rock)

> [!CAUTION]
> **ESECUZIONE MANUALE**: Queste operazioni devono essere eseguite **dall'utente direttamente sul NAS** per garantire la massima velocità e sicurezza. L'AI non deve intervenire su processi o file in questa fase.

Questa sezione è il "chiusino" della rescue pipeline moderna: converte la Landing Zone (`music_backup`) nel dataset definitivo (`music/pop_rock`) e ripristina il seeding.

### Step 1: Backup e Offline
1. Backup manuale del DB Lidarr e del file `musiclibrary.db` di Beets.
2. Scalare Lidarr a 0: `kubectl scale deployment lidarr -n arr --replicas=0`.

### Step 2: Permission Sync
```bash
# Su TrueNAS via SSH — allineamento owner e permessi
chown -R 1000:1000 /mnt/oliraid/arrdata/media/music_backup
chmod -R 755 /mnt/oliraid/arrdata/media/music_backup
```

### Step 3: Lo Swap Fisico (Rename Atomico via ZFS)
```bash
# Su TrueNAS via SSH — rename ZFS atomico (nessuna copia di dati)
zfs rename oliraid/arrdata/media/music oliraid/arrdata/media/music_old
zfs rename oliraid/arrdata/media/music_backup oliraid/arrdata/media/music/pop_rock
```

### Step 4: Lidarr Recovery (Smart Library Import)
1. Riavviare `lidarr-pop`: `kubectl scale deployment lidarr -n arr --replicas=1`.
2. In Lidarr: **Library → Import** (NON Rescan) → puntare a `/media/music/pop_rock`.
3. Lidarr riconoscerà la struttura Beets e aggiornerà i path nel DB mantenendo la storia degli artisti.
4. Verifica riproduzione via Jellyfin per confermare i nuovi percorsi.

### Step 5: Riallineamento Hardlink Seeding (qBittorrent)
Per ogni album che risulta "Missing" su qBittorrent dopo lo swap:
```bash
# Ricrea il legame fisico (zero spazio extra)
cp -al "/Volumes/arrdata/media/music/pop_rock/Artista/Album/." \
       "/Volumes/arrdata/downloads/lidarr/Cartella_Originale_Torrent/"
```
In qBittorrent: selezionare i torrent → **Force Recheck** → attesa 100% → seeding ripristinato.
Dopo 48h di stabilità: `zfs destroy oliraid/arrdata/media/music_old`.

---

## 1. Topologia Storage (TrueNAS & NFS)

Per garantire la separazione fisica tra i domini, lo storage è organizzato a livello ZFS su TrueNAS SCALE con export NFS dedicati:

| Dataset ZFS Path | Recordsize | Condivisione NFS | Permessi UNIX | Pod K8s & Accesso |
| :--- | :--- | :--- | :--- | :--- |
| `oliraid/arrdata/media/music/pop_rock` | `1M` | Pop/Rock Final | `1000:1000` (Media) | `lidarr-pop` (RW), `jellyfin` (RO) |
| `oliraid/arrdata/staging/pop_rock` | `128K` | Pop/Rock Staging | `1000:1000` (Media) | `qbittorrent` (RW), `lidarr-pop` (RW) |
| `oliraid/arrdata/classical` | `1M` | Classical Unified | `1000:1000` (Media) | `qbittorrent` (RW), `jellyfin-classic` (RO) |

> [!IMPORTANT]
> **Isolamento Fisico (Copia)**:
> La libreria classica è interamente disaccoppiata dall'area di staging tramite la creazione di **copie fisiche** (`copy: yes` in Beets). L'uso di symlink o hardlink è stato deprecato per prevenire data-loss (cancellazione accidentale da staging) e la corruzione del seeding (modifica dei tag ID3).
> - **Stato Attuale**: Si accetta la duplicazione temporanea dello spazio per preservare il seeding torrent in `staging`.
> - **Cleanup Staging**: La pulizia di `/Volumes/classical/staging` è demandata all'utente manualmente a fine importazione e completamento seeding, e può essere eseguita in totale sicurezza senza impattare la `library`.

```
/Volumes/arrdata/classical/
├── staging/       ← qBittorrent scarica qui, seeding attivo
└── library/       ← Beets scrive qui (duplicato ZFS temporaneo)
```

---

## 2. Rilascio GitOps & Helm (`pindaroli-arr-helm`)

### 2.1 Definizione di `lidarr-classic`
L'istanza `lidarr-classic` agisce esclusivamente come motore di ricerca e invio torrent. È montata in sola lettura sul dataset classico.

```yaml
# values/lidarr-classic-values.yaml
podSecurityContext:
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000

ingress:
  enabled: false  # Gestito via IngressRoute Traefik custom in k8s-lab

persistence:
  config:
    enabled: true
    existingClaim: lidarr-classic-config-pvc
  staging-classical:
    enabled: true
    type: custom
    volumeSpec:
      nfs:
        server: 10.10.10.50
        path: /mnt/oliraid/arrdata/classical/staging
    mountPath: /staging/classical
    readOnly: false
```

### 2.2 Definizione di `jellyfin-classic` (Opzione A - 1:1)
`jellyfin-classic` è un'istanza segregata e indipendente che monta **esclusivamente** il dataset classico pulito.

```yaml
# values/jellyfin-classic-values.yaml
podSecurityContext:
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000

ingress:
  enabled: false  # Gestito via IngressRoute Traefik custom in k8s-lab

persistence:
  config:
    enabled: true
    existingClaim: jellyfin-classic-config-pvc
  media:
    enabled: true
    type: custom
    volumeSpec:
      nfs:
        server: 10.10.10.50
        path: /mnt/oliraid/arrdata/classical/library
    mountPath: /media/music/classical
    readOnly: true
```

---

## 3. Infrastruttura Non-Helm (`k8s-lab`)

### 3.1 PV & PVC: `storage/classical-media-pvc.yaml`
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-classical-media
spec:
  capacity:
    storage: 500Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: csi-nfs-stripe-arr-conf
  nfs:
    path: /mnt/oliraid/arrdata/classical
    server: 10.10.10.50
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: servarr-classical-media
  namespace: arr
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 500Gi
  storageClassName: csi-nfs-stripe-arr-conf
  volumeName: pv-classical-media
```

### 3.2 Ingress & Sicurezza (Traefik IngressRoutes)
Le rotte in `k8s-lab/traefik/all-arr-ingress-routes.yaml` per garantire il **Dual Ingress (Esterno con OAuth2, Interno Diretto)**:

```yaml
# IngressRoute per Jellyfin-Classic
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: jellyfin-classic-ingress-route
  namespace: arr
spec:
  entryPoints:
    - websecure
  routes:
    # Accesso Esterno: protetto da OAuth2
    - match: Host(`jellyfin-classic.pindaroli.org`)
      kind: Rule
      services:
        - name: oli-arr-jellyfin-classic
          port: 8096
      middlewares:
        - name: oauth2-auth
          namespace: traefik
    # Accesso Interno: diretto (No OAuth2)
    - match: Host(`jellyfin-classic`) || Host(`jellyfin-classic-internal.pindaroli.org`)
      kind: Rule
      services:
        - name: oli-arr-jellyfin-classic
          port: 8096
  tls:
    secretName: pindaroli-wildcard-tls

---
# IngressRoute per Lidarr-Classic
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: lidarr-classic-ingress-route
  namespace: arr
spec:
  entryPoints:
    - websecure
  routes:
    # Accesso Esterno: protetto da OAuth2
    - match: Host(`lidarr-classic.pindaroli.org`)
      kind: Rule
      services:
        - name: oli-arr-lidarr-classic
          port: 8686
      middlewares:
        - name: oauth2-auth
          namespace: traefik
    # Accesso Interno: diretto (No OAuth2)
    - match: Host(`lidarr-classic`) || Host(`lidarr-classic-internal.pindaroli.org`)
      kind: Rule
      services:
        - name: oli-arr-lidarr-classic
          port: 8686
  tls:
    secretName: pindaroli-wildcard-tls
```

### 3.3 DNS Split-Horizon (OPNsense / `rete.json`)
Aggiungere i seguenti alias sotto `traefik-lb` in `rete.json` ed avviare il sync DNS:
- `jellyfin-classic`
- `jellyfin-classic-internal`
- `lidarr-classic`
- `lidarr-classic-internal`

```bash
ansible-playbook ansible/playbooks/opnsense_sync_dns.yml
```

---

## 4. Integrazione Applicativa & Routing

### 4.1 qBittorrent (Routing per Categoria)
- **Categoria**: `lidarr-classic`
- **Save Path**: `/staging/classical` (TrueNAS: `/mnt/oliraid/arrdata/classical/staging`)

### 4.2 Prowlarr (Tagging degli Indexer Classici)
- **Tag**: `classical-indexers`
- Assegnare il tag agli indexer classical e forzare la sincronizzazione **solo** su `lidarr-classic`.

### 4.3 Completed Download Handling
- Disabilitare **"Enable Completed Download Handling"** in `lidarr-classic` settings.

### 4.4 API Reconciliation Loop (Chiusura del Cerchio)
Hook post-import Beets eseguito su macOS dopo ogni consolidamento di metadati classica per spegnere il monitoraggio dell'album in `lidarr-classic` (evitando loop di download infiniti):

```python
# import_classical/segregate_classical.py
import os
import sys
import requests

LIDARR_API_URL = "http://oli-arr-lidarr-classic.arr.svc.cluster.local:8686/api/v1"
API_KEY = os.environ.get("LIDARR_CLASSICAL_API_KEY")

def query_lidarr_album_by_path(folder_name):
    headers = {"X-Api-Key": API_KEY, "Accept": "application/json"}
    response = requests.get(f"{LIDARR_API_URL}/album", headers=headers)
    response.raise_for_status()
    for album in response.json():
        if folder_name.lower() in album.get("title", "").lower() or folder_name.lower() in album.get("path", "").lower():
            return album.get("id")
    return None

def unmonitor_album(album_id):
    headers = {"X-Api-Key": API_KEY, "Content-Type": "application/json", "Accept": "application/json"}
    payload = {"albumIds": [album_id], "monitored": False}
    r = requests.put(f"{LIDARR_API_URL}/album/monitor", headers=headers, json=payload)
    r.raise_for_status()
    print(f"Successfully unmonitored Classical Album ID: {album_id} in Lidarr-Classic")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    folder_path = sys.argv[1]
    folder_name = os.path.basename(os.path.normpath(folder_path))
    album_id = query_lidarr_album_by_path(folder_name)
    if album_id:
        unmonitor_album(album_id)
```

---

## 5. Hardening Presentation Layer (Jellyfin options.xml ConfigMap)

Per costringere `jellyfin-classic` a basarsi esclusivamente sui perfetti metadati Vorbis/ID3 generati da Beets e ignorare i DB web generici:

```yaml
# kubernetes/manifests/jellyfin-classic-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jellyfin-classic-options
  namespace: arr
data:
  options.xml: |
    <?xml version="1.0" encoding="utf-8"?>
    <LibraryOptions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <EnableEmbeddedTitles>true</EnableEmbeddedTitles>
      <PreferEmbeddedTitlesOverServerTitles>true</PreferEmbeddedTitlesOverServerTitles>
      <MetadataFetchers />
      <MetadataFetcherOrder />
      <ImageFetchers />
      <ImageFetcherOrder />
      <TypeOptions>
        <TypeOption>
          <Type>MusicAlbum</Type>
          <MetadataFetchers />
          <ImageFetchers />
        </TypeOption>
        <TypeOption>
          <Type>MusicArtist</Type>
          <MetadataFetchers />
          <ImageFetchers />
        </TypeOption>
      </TypeOptions>
    </LibraryOptions>
```

---

## 🔗 Relazioni & Tracciabilità
- Sostituisce: `classical-infrastructure-provisioning.md`
- Collegato a: [[classical-music-strategy]]
- Monitorato da: [[todo]]
