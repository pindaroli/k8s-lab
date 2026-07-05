# Prompt di Configurazione MinimServer per Gemini Deep Search

Usa questo prompt per fare pianificare in dettaglio l'aggiunta di MinimServer nello stack Helm "servarr".

---

## CONTESTO & OBIETTIVI

Stiamo lavorando sul cluster Kubernetes homelab (Progetto GEMINI). La repository di riferimento per i chart Helm è `pindaroli-arr-helm`, la quale contiene un chart ombrello chiamato `servarr` (in `charts/servarr`) che gestisce i vari componenti dello stack (sonarr, radarr, jellyfin, jellyfin-classic, lidarr-classic, ecc.).

Vogliamo aggiungere un nuovo servizio chiamato `minimserver` (MinimServer DLNA/UPnP Media Server) all'interno del chart ombrello `servarr`.

Di seguito sono riportati tutti i dettagli tecnici rilevati dal nostro cluster per guidarti nella stesura di un piano di implementazione dettagliato e dichiarativo (niente modifiche manuali a caldo).

---

## DETTAGLI ARCHITETTURALI E CONFIGURAZIONI REALI

### 1. Modello Architetturale di Riferimento: Jellyfin-Classic
Poiché MinimServer è un media server DLNA con requisiti di rete e storage simili a `jellyfin-classic`, useremo quest'ultimo come modello architetturale di riferimento nel nostro chart.

#### Configurazione di Rete (DLNA/SSDP):
Per consentire la scoperta DLNA (SSDP multicast su UDP porta 1900), il pod deve poter accedere direttamente alla rete dell'host. Nel template del deployment di `jellyfin-classic` (`charts/servarr/templates/jellyfin-classic/deployment.yaml`) questo è implementato così:

```yaml
    spec:
    {{- if (index .Values "jellyfin-classic").enableDLNA }}
      hostNetwork: true
      dnsPolicy: ClusterFirstWithHostNet
    {{- end }}
```

E nel container sono mappate le relative porte DLNA:
```yaml
          ports:
            - name: http
              containerPort: {{ (index .Values "jellyfin-classic").service.port }}
              protocol: TCP
          {{ if (index .Values "jellyfin-classic").enableDLNA }}
            - name: dlna
              containerPort: 1900
              hostPort: 1900
              protocol: UDP
          {{- end }}
```

---

### 2. Dettagli sul Mount delle Share NFS (Musica Classica & Config)
Nel nostro cluster, la musica classica risiede sul server TrueNAS `10.10.10.50` nel dataset `/mnt/oliraid/arrdata/classical`.
Nel cluster K8s è attiva una PersistentVolumeClaim (PVC) condivisa chiamata `servarr-classical-media` (StorageClass: `csi-nfs-stripe-arr-conf`) che punta a tale share.

Prendendo come esempio la configurazione di `jellyfin-classic` nel file `arr-values.yaml`:

```yaml
jellyfin-classic:
  enabled: false
  image:
    tag: "10.10.7"
  persistence:
    config:
      enabled: true
      storageClass: csi-nfs-stripe-arr-conf
      storageClassName: csi-nfs-stripe-arr-conf
    media:
      enabled: true
      type: persistentVolumeClaim
      existingClaim: servarr-classical-media
      subPath: "library"
```

Per MinimServer, dovremo pianificare:
1. **La Libreria Musicale (Read-Only):** Deve montare la PVC `servarr-classical-media` impostando `subPath: library` (la sottocartella in cui risiede la libreria finale).
2. **Lo Storage di Configurazione (/config):** Deve puntare a un percorso persistente sulla nostra share NFS dedicata alle configurazioni. Possiamo farlo in due modi:
   - **Opzione A:** Creare un PVC dinamico usando la StorageClass `csi-nfs-stripe-arr-conf` (che punta alla share NFS `/mnt/stripe/k8s-arr` su TrueNAS e genera in automatico la cartella corretta per il servizio).
   - **Opzione B:** Utilizzare un subpath all'interno della stessa PVC della musica classica (es. `subPath: config/minimserver`).

---

### 3. Dettagli Tecnici & Docker MinimServer
- **Repository Immagine Ufficiale:** `minimworld/minimserver`
- **Versione Consigliata (Tag):** Utilizzare la versione stabile della serie MinimServer 2, nello specifico il tag `2.2` (es. `minimworld/minimserver:2.2`), per evitare rotture improvvise derivanti dall'uso del tag `latest`.
- **Porte MinimServer:**
  - `9790` (TCP) - HTTP Console / Web UI per la gestione e configurazione.
  - `9791` (TCP) - HTTP Status page.
  - `1900` (UDP) - SSDP discovery (necessario abilitarla sul servizio/pod).

---

### 4. Dimensionamento e Risorse Consigliate (Max 4 Client)
MinimServer è estremamente leggero (Java-based). Per servire fino a 4 client contemporanei senza transcodifica attiva (streaming diretto di FLAC/ALAC/MP3):
- **CPU Requests:** `50m` (0.05 CPU core) per consentire l'esecuzione in background.
- **CPU Limits:** `500m` (0.5 CPU core) per gestire picchi veloci durante la fase iniziale di scansione dei file musicali all'avvio.
- **Memory Requests:** `256Mi` (sufficiente per la Java Virtual Machine e la cache iniziale dell'indice).
- **Memory Limits:** `512Mi` (per evitare OOM in caso di librerie molto estese durante la scansione).

---

## OUTPUT RICHIESTO

Fornisci un piano di implementazione dettagliato diviso in fasi:

1. **Definizione dei Template YAML:** Mostra il codice esatto dei file da posizionare in `charts/servarr/templates/minimserver/` (`deployment.yaml`, `pvc.yaml`, `service.yaml`, `ingress.yaml` se necessario, ecc.) assicurandoti che integrino il supporto a `hostNetwork` condizionale (o abilitato di default) e le porte corrette.
2. **Definizione delle Variabili di Default (`values.yaml`):** Lo schema esatto di variabili da aggiungere in `charts/servarr/values.yaml` sotto la sezione `minimserver:`.
3. **Definizione dei Valori di Personalizzazione (`arr-values.yaml`):** Il blocco YAML reale da aggiungere nel file di deploy locale `servarr/arr-values.yaml` (in `k8s-lab`), configurando:
   - Abilitazione del server (`enabled: true`)
   - Configurazione dell'immagine (`minimworld/minimserver:2.2`)
   - Mount della share classica read-only via `servarr-classical-media`
   - Configurazione dello storage di configurazione persistente
   - Configurazione di CPU e Memory limits
4. **Procedura di Verifica:** I comandi per verificare la correttezza del template helm prima dell'applicazione e per monitorare lo stato del pod e la connettività di rete dopo il deploy.
