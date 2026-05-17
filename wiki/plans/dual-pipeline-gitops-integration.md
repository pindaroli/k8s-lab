# Piano: GitOps Orchestration for Segregated Ontological Structures (Dual-Pipeline Ingestion)

**Stato**: 🔵 Pianificato — In attesa di approvazione
**Data**: 2026-05-17
**Obiettivo**: Piano finale e unificante dell'architettura musicale. Copre il **Final Sync** della libreria moderna, l'**avvio della pipeline classica in parallelo**, e il **deploy GitOps K8s** dell'intera infrastruttura duale (Lidarr-Pop + Lidarr-Classical + Jellyfin segregato).

> [!NOTE]
> **Dipendenze (Subordinazione)**:
> - Questo piano si attiva quando [[beets-music-rescue-pipeline]] raggiunge la Fase 4.2 (Case Clash completato, DB stabile).
> - [[classical-music-strategy]] può essere avviata **in parallelo** alla Fase 3 della rescue pipeline, in quanto usa un database Beets separato (`classical_musiclibrary.db`) e path di staging distinti. Nessun conflitto di I/O o DB con la pipeline moderna.

---

## Pre-Condizione: Final Sync & Swap (Modern Music — ex Fase 5 + 6)

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
| `oliraid/arrdata/classical` | `1M` | Classical Unified | `1000:1000` (Media) | `qbittorrent` (RW), `jellyfin` (RO) |

> [!IMPORTANT]
> **Dataset Classico Unificato & Nota Duplicazione**:
> Sebbene staging e library risiedano nello stesso dataset ZFS (`oliraid/arrdata/classical`), l'utilizzo di Beets con `write: yes` da macOS via NFS rompe gli hardlink all'atto della scrittura dei metadati (Mutagen riscrive fisicamente il file).
> - **Stato Attuale**: Si accetta la duplicazione temporanea dello spazio per preservare il seeding e la perfezione dei metadati fisici.
> - **Cleanup Staging**: La pulizia di `/Volumes/classical/staging` è demandata all'utente manualmente a fine importazione e completamento seeding.
> - **Automazione Futura**: È pianificata l'integrazione di uno script di cleanup post-seeding agganciato a qBittorrent o l'esecuzione periodica di `jdupes`/`duperemove` sul NAS per rifondere i blocchi identici tramite il ZFS Block Cloning nativo del pool.

```
/Volumes/arrdata/classical/
├── staging/       ← qBittorrent scarica qui, seeding attivo
└── library/       ← Beets scrive qui (duplicato ZFS temporaneo)
```

---

## 2. Manifesti Kubernetes & Overrides Helm (`pindaroli-arr-helm`)

### 2.1 Deployment `lidarr-classical`
Questo pod agisce esclusivamente come motore di ricerca e invio torrent. È privo di accesso in scrittura al dataset `/music/classical`.

```yaml
# values/lidarr-classical-values.yaml
podSecurityContext:
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000

ingress:
  enabled: true
  hosts:
    - host: lidarr-classical.internal.pindaroli.org
      paths:
        - path: /
          pathType: Prefix

persistence:
  config:
    enabled: true
    existingClaim: lidarr-classical-config-pvc
  staging-classical:
    enabled: true
    type: custom
    volumeSpec:
      nfs:
        server: truenas.internal.pindaroli.org
        path: /mnt/oliraid/arrdata/staging/classical
    mountPath: /staging/classical
    readOnly: false
```

### 2.2 Mount Segregati in `jellyfin`
Jellyfin monta entrambi i percorsi in modalità **strettamente read-only**.

```yaml
# values/jellyfin-values.yaml (estratto)
persistence:
  music-pop:
    enabled: true
    type: custom
    volumeSpec:
      nfs:
        server: truenas.internal.pindaroli.org
        path: /mnt/oliraid/arrdata/media/music/pop_rock
    mountPath: /media/music/pop_rock
    readOnly: true
  music-classical:
    enabled: true
    type: custom
    volumeSpec:
      nfs:
        server: truenas.internal.pindaroli.org
        path: /mnt/oliraid/arrdata/classical/library
    mountPath: /media/music/classical
    readOnly: true
```

---

## 3. Instradamento & Disaccoppiamento (Prowlarr & qBittorrent)

### 3.1 Tagging Indexer (Prowlarr)
1. In Prowlarr, creare il tag `classical-indexers`.
2. Assegnare questo tag esclusivamente agli indexer ad alta fedeltà classica (RED, Usenet dedicati).
3. Mappare i profili di sincronizzazione in modo che:
   - I tracker generici vengano inviati solo a `lidarr-pop`.
   - I tracker `classical-indexers` vadano esclusivamente a `lidarr-classical`.

### 3.2 Categorie di Routing (qBittorrent)
qBittorrent mappa i save path fisici in base alla categoria passata dalle API delle applicazioni:
- Categoria **`music-pop`** $\rightarrow$ Save Path: `/staging/pop_rock`
- Categoria **`music-classical`** $\rightarrow$ Save Path: `/staging/classical`

### 3.3 Disabilitazione Completed Download Handling
> [!CRITICAL]
> In `lidarr-classical` $\rightarrow$ **Settings** $\rightarrow$ **Download Clients**, disabilitare **"Enable Completed Download Handling"**.
> Questo interrompe il controllo di Lidarr sul file system una volta completato il download, lasciando il payload in staging per la curation Beets. Ignorare il warning di errore permanente visualizzato nella dashboard di Lidarr.

---

## 4. API Reconciliation Loop (Chiusura del Cerchio)

Poiché Lidarr non sposta i file, crederà che l'album sia permanentemente mancante e continuerà a cercarlo. Risolviamo questo loop tramite uno script di unmonitoring API eseguito al termine dell'importazione Beets.

```python
# import_classical/segregate_classical.py (Hook post-import Beets)
import os
import sys
import requests

LIDARR_API_URL = "http://lidarr-classical.svc.cluster.local:8686/api/v1"
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
    print(f"Successfully unmonitored Classical Album ID: {album_id} in Lidarr-Classical")

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

## 5. Hardening Presentation Layer (Jellyfin options.xml)

Per impedire a Jellyfin di interrogare database web musicali e distruggere l'ontologia Bespoke creata da Beets, usiamo un ConfigMap Kubernetes montato in `/config/root/default/Classical/options.xml` per la libreria classica.

```yaml
# kubernetes/manifests/jellyfin-classical-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jellyfin-classical-options
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

QuestoConfigMap rimuove gli array di scraping per la libreria Classica, forzando Jellyfin a basarsi esclusivamente sui tag Vorbis/ID3 ed elaborando correttamente i delimitatori di artisti multipli (es. `Compositore; Direttore; Orchestra`).

---

## Relazioni
- Implementa: [[classical-music-strategy]]
- Dipende da: [[beets-music-rescue-pipeline]]
- Configura: [[Servarr]]
