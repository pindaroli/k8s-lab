# Wiki Plan: Classical Ingestion Routing & qBittorrent Category Integration

> [!IMPORTANT]
> **Stato**: 📝 **IN FASE DI DEFINIZIONE / APPROVAZIONE**
> **Target**: Cluster GEMINI (`pindaroli.org`) · **Ultimo Aggiornamento**: 2026-05-24
> **Obiettivo**: Questo piano definisce le modifiche dichiarative e applicative per instradare i torrent lanciati da `lidarr-classic` tramite una categoria dedicata in qBittorrent, depositandoli nello staging della musica classica in attesa dell'importazione via Beets.
>
> ### 🔗 Relazioni & Tracciabilità
> - Collegato a: [[dual-pipeline-gitops-integration]], [[classical-music-strategy]]
> - Monitorato da: [[todo]]

---

## 🗺️ Mappa dei Percorsi & Relazioni Logiche

Per garantire la coerenza logica e la stabilità delle due pipeline parallele (moderna vs classica), la struttura di rete e di storage viene allineata in questo modo:

```
[Lidarr-Classic] --(Invia Torrent + Categoria: lidarr-classic)--> [qBittorrent]
                                                                        │
                                                     (Scarica su NVMe in /data/incomplete)
                                                                        │
                                                     (Sposta completato nella share nfs /mnt/oliraid/arrdata/classical/staging)
                                                                        │
[Mac Studio (Beets)] --(Importazione con copia fisica)-----------------▼
   │
   └─► [Destinazione Library]: /Volumes/classical/library (Jellyfin-Classic RO)
```

---

## 1. Topologia Storage & Percorsi Mount

Per consentire a qBittorrent di scrivere nel dataset della musica classica, allineiamo i mount point nel file `arr-values.yaml`:

| Servizio K8s | Risorsa NFS (TrueNAS) | Mount Path Interno | Permessi | Ruolo |
| :--- | :--- | :--- | :--- | :--- |
| `qbittorrent` | `/mnt/oliraid/arrdata/classical/staging` | `/staging/classical` | RW | Area di atterraggio torrent completati |
| `lidarr-classic` | `/mnt/oliraid/arrdata/classical/staging` | `/media` (o `/staging/classical`) | RW | Scansione download completati (CDH disabilitato) |
| `jellyfin-classic`| `/mnt/oliraid/arrdata/classical/library` | `/media/music/classical` | RO | Esposizione streaming audio pulito |

---

## 2. Modifiche Dichiarative Helm (`servarr/arr-values.yaml`)

Aggiungeremo il mount della PVC `servarr-classical-media` a qBittorrent modificando le sezioni `extraVolumes` e `additionalMounts`:

```yaml
# servarr/arr-values.yaml

qbittorrent:
  # ...
  extraVolumes:
    - name: incomplete-dw
      persistentVolumeClaim:
        claimName: pvc-incomplete-dw
    # NUOVO VOLUME PER LA STAGING AREA CLASSICA
    - name: classical-staging
      persistentVolumeClaim:
        claimName: servarr-classical-media

  persistence:
    # ...
    additionalMounts:
      - name: incomplete-dw
        mountPath: /data/incomplete
      # NUOVO MOUNT PER LA STAGING AREA CLASSICA
      - name: classical-staging
        mountPath: /staging/classical
        subPath: staging
```

---

## 3. Configurazione Applicativa (WebUIs) [DA DEFINIRE]

> [!IMPORTANT]
> **Stato Sezione**: **DA DEFINIRE / IN CORSO DI VALIDAZIONE**
> Questa sezione descrive una bozza preliminare della configurazione applicativa. I dettagli esatti sul path mapping e sulle impostazioni definitive saranno validati ed eventualmente raffinati sul campo durante la fase di test.

### 3.1 Automazione Configurazione a Freddo qBittorrent (Ansible)

La configurazione della categoria `lidarr-classic` e del suo Save Path in qBittorrent **NON** deve essere eseguita a caldo via WebUI per evitare sovrascritture di memoria da parte del demone qBittorrent all'arresto.

L'operazione sarà gestita dichiarativamente tramite un **Playbook Ansible** che opera direttamente sul file `qBittorrent.conf` memorizzato sul NAS (`/mnt/stripe/k8s-arr/servarr-qbittorrent/qBittorrent/qBittorrent.conf`).

#### A. Orchestrazione dello Spegnimento (Scaling a Replica 0)
Per eliminare qualsiasi intervento manuale ed evitare che qBittorrent sovrascriva il file al momento dello spegnimento, il playbook Ansible si occuperà di orchestrare autonomamente il ciclo di vita dei pod:
1.  **Cattura dello Stato Attivo**: Il playbook interroga il cluster K8s (`kubernetes.core.k8s_info`) per registrare e salvare come variabili il numero corrente di repliche attive di ciascun deployment nel namespace `arr` (`qbittorrent`, `lidarr-pop`, `lidarr-classic`, `sonarr`, `radarr`).
2.  **Graceful Scaling a Replica 0**: Esegue lo scaling a 0 di tutti i deployment, spegnendo ordinatamente l'intera stack Arr e qBittorrent.
3.  **Attesa di Spegnimento Completo**: Il playbook attende che K8s confermi che tutte le istanze sono state arrestate (repliche effettive = 0).

#### B. Backup con Data/Ora, Update a Freddo & Ripristino
Una volta che l'ambiente è congelato a replica 0:
1.  **Backup Dinamico**: Il playbook effettua una copia di sicurezza del file di configurazione corrente con marcatura temporale estesa in formato:
    `qBittorrent.conf.YYYYMMDD_HHMMSS` (es. `qBittorrent.conf.20260524_114000`).
2.  **Aggiornamento Configurazione**: Esegue l'update sul file esistente tramite il modulo `ini_file` di Ansible, inserendo o modificando le chiavi nella sezione delle categorie:
    ```ini
    [BitTorrent\Categories]
    lidarr-classic\save_path=/staging/classical
    ```
3.  **Ripristino Automatico delle Repliche**: Conclusa la modifica del file, il playbook ripristina ciascun deployment al numero di repliche originale salvato nella Fase A, riavviando ordinatamente la stack. In questo modo il demone qBittorrent si avvia leggendo la configurazione già aggiornata su disco, senza possibilità di sovrascrittura.

### 3.2 Lidarr-Classic: Provisioning Dichiarativo via REST API (A Caldo post-bootstrap)

Il provisioning delle impostazioni interne di `lidarr-classic` viene gestito in modo deterministico e idempotente da un Playbook Ansible che esegue chiamate REST API (a caldo subito dopo l'avvio del pod). Questo approccio garantisce la coerenza dello stato eliminando i passaggi manuali.

#### A. Pre-flight Check (Polling di Bootstrap)
Spesso, all'avvio iniziale, il pod transisce allo stato `Running` prima che l'applicazione interna abbia terminato le migrazioni del database SQLite e inizializzato il server web. Il playbook implementa un pre-flight check resiliente basato su una progressione lineare:
$$T_{\text{attesa}} = R \times D$$
Con $R = 30$ (tentativi di retry) e $D = 10$ (ritardo in secondi), il playbook attenderà fino a **300 secondi (5 minuti)** che l'endpoint `/api/v1/system/status` risponda con codice `200 OK` prima di procedere.

#### B. Disabilitazione Globale del Completed Download Handling (CDH)
Per impedire a Lidarr-Classic di interferire con la pipeline esterna Beets, disabilitiamo il CDH globale inviando una richiesta PUT all'endpoint `/api/v1/config/downloadclient`. Il payload include i parametri strutturali completi per evitare il ripristino ai valori predefiniti:
```json
{
  "id": 1,
  "enableCompletedDownloadHandling": false,
  "checkForFinishedDownloadInterval": 1,
  "autoRedownloadFailed": true,
  "downloadClientWorkingFolders": "_UNPACK_|_FAILED_"
}
```

#### C. Registrazione Idempotente del Download Client (qBittorrent)
Il playbook esegue una chiamata GET preventiva a `/api/v1/downloadclient` per verificare l'esistenza del client `qBittorrent-Classical`. Se assente, esegue una chiamata POST all'endpoint `/api/v1/downloadclient` con il payload:
```json
{
  "name": "qBittorrent-Classical",
  "enable": true,
  "protocol": "torrent",
  "priority": 1,
  "implementation": "QBittorrent",
  "configContract": "QBittorrentSettings",
  "fields": [
    { "name": "host", "value": "10.10.20.60" },
    { "name": "port", "value": 8080 },
    { "name": "useSsl", "value": false },
    { "name": "username", "value": "admin" },
    { "name": "password", "value": "adminadmin" },
    { "name": "category", "value": "lidarr-classic" }
  ]
}
```

#### D. Registrazione Idempotente del Remote Path Mapping
Poiché qBittorrent scarica nella share NFS fisica (vista dal suo pod come `/staging/classical/`) e `lidarr-classic` monta lo staging su `/media/`, dobbiamo mappare i percorsi. Il mapping deve corrispondere esattamente all'IP configurato nel download client (`10.10.20.60`). Eseguiamo un GET preventivo a `/api/v1/remotepathmapping` e, se assente, inviamo un POST a `/api/v1/remotepathmapping`:
```json
{
  "host": "10.10.20.60",
  "remotePath": "/staging/classical/",
  "localPath": "/media/"
}
```

### 3.3 Prowlarr: Segregazione degli Indexer Classici via Tag Relazionali

Per impedire a `lidarr-classic` di ricevere indexer non specializzati e proteggere le statistiche di API/ratio sui tracker di musica classica, la sincronizzazione viene segregata in Prowlarr tramite tag relazionali. Il provisioning segue un flusso sequenziale in due fasi distinte gestito via Ansible:

#### Fase 1: Creazione/Verifica del Tag in Prowlarr
I tag in Prowlarr sono entità relazionali identificate da un ID numerico incrementale nel database. Il playbook esegue una chiamata POST all'endpoint `/api/v1/tag` di Prowlarr per verificare/creare l'etichetta `classical-indexers`. La risposta restituisce l'ID numerico generato (ad esempio, `3` per `{"id": 3, "label": "classical-indexers"}`).

#### Fase 2: Registrazione Idempotente dell'Applicazione Lidarr-Classic in Prowlarr
Utilizzando l'ID numerico ottenuto (es. `3`), il playbook registra `lidarr-classic` in Prowlarr inviando una richiesta POST a `/api/v1/applications`. Questo propaga in modo esclusivo a `lidarr-classic` solo gli indexer marcati con lo stesso tag:
```json
{
  "name": "Lidarr-Classic",
  "enable": true,
  "syncLevel": "fullSync",
  "implementation": "Lidarr",
  "implementationName": "Lidarr",
  "configContract": "LidarrSettings",
  "tags": [ 3 ],
  "fields": [
    { "name": "baseUrl", "value": "http://oli-arr-lidarr-classic.arr.svc.cluster.local:8686" },
    { "name": "apiKey", "value": "{{ lidarr_api_key }}" }
  ]
}
```

---

## 4. Test di Verifica & Flusso Operativo

Una volta applicate le modifiche, effettueremo un test di validazione end-to-end:

1. **Verifica Mount**:
   Eseguire il deploy e controllare che il pod qBittorrent acceda correttamente al volume classica:
   ```bash
   kubectl exec -it -n arr deploy/qbittorrent -- ls -la /staging/classical
   ```
2. **Test di Ingestione**:
   - Aggiungere un album classico di prova in Lidarr-Classic e avviare la ricerca.
   - Verificare in qBittorrent che il torrent venga avviato con la categoria `lidarr-classic`.
   - A download completato, verificare che il file venga spostato in `/staging/classical` su Kubernetes, e che appaia in `/Volumes/classical/staging` su Mac Studio.
   - Eseguire a mano o in batch la pipeline Beets per spostare il file normalizzato in `/Volumes/classical/library`.
   - Verificare che lo script `segregate_classical.py` disabiliti il monitoring dell'album in Lidarr-Classic.

---
*Piano redatto da Antigravity AI Engineering — 2026-05-24*
