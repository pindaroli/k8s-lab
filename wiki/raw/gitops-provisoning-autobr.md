Architettura di Provisioning Dichiarativo e GitOps per Autobrr: Ingegnerizzazione del Progetto GEMININel contesto dell'automazione dei carichi di lavoro in ambienti cloud-native, il Progetto GEMINI si configura come un'infrastruttura homelab guidata dai principi della metodologia GitOps, in cui la riproducibilità dello stato e la separazione dei compiti rappresentano i pilastri fondamentali. La distribuzione di Autobrr — un'applicazione per l'automazione dei download basata su eventi e feed — introduce una sfida architetturale tipica dei sistemi a stato misto. Mentre i parametri infrastrutturali di rete, crittografia e connettività esterna vengono definiti in modo statico nel file config.toml o tramite variabili d'ambiente, le logiche di business applicative, quali i filtri di selezione, le credenziali dei client di download e i canali di notifica, risiedono interamente all'interno dello schema relazionale del database.Per garantire un flusso di lavoro GitOps puro, in cui l'intero ecosistema applicativo possa essere ricostruito a partire dal solo codice sorgente dichiarativo, si rende necessaria una rigorosa analisi delle modalità di iniezione di questo stato all'interno del database PostgreSQL gestito dall'operatore CloudNativePG (CNPG) tramite il servizio interno postgres-main-rw.cnpg-system.svc.cluster.local.Analisi Comparativa delle Metodologie di ProvisioningLa scelta della strategia per l'applicazione della configurazione logica su Autobrr determina il livello di accoppiamento del ciclo di vita del database rispetto a quello dell'applicazione. Vengono analizzati di seguito i quattro approcci principali, valutandone l'efficacia operativa e descrivendo le metodoloji di gestione dei dati sensibili per ciascuno scenario.MetodologiaVantaggi (Pro)Svantaggi (Contro)Gestione dei Segreti (GitOps)API REST via K8s Job• Validazione dei dati eseguita dal motore applicativo.• Disaccoppiamento totale dallo schema fisico del database.• Idempotenza nativa tramite verbi HTTP.• Richiede che il pod di Autobrr sia attivo e in stato Ready prima dell'esecuzione.• Necessita di una chiave API valida o di credenziali di bypass.Templating a runtime tramite Kubernetes Secret montati come variabili d'ambiente nel container del Job.Seeding SQL PostgreSQL• Configurazione istantanea prima ancora dell'avvio del container.• Non richiede connettività HTTP interna all'avvio.• Eseguito nativamente dal controller CNPG.• Forte accoppiamento con lo schema tabellare interno.• Rischio di bloccare le migrazioni automatiche dell'ORM ad ogni aggiornamento.Crittografia dei file SQL tramite Mozilla SOPS o SealedSecrets prima del push su Git, decrittografati poi dall'operatore in cluster.Iniezione via CLI (autobrrctl)• Strumento ufficiale fornito dai manutentori del progetto.• Gestione nativa del hashing delle password.• Copertura limitata: autobrrctl gestisce solo utenti e conversioni DB.• Impossibile dichiarare filtri o client via CLI.Passaggio delle variabili d'ambiente protette dal Secret di Kubernetes direttamente ai comandi CLI dell'InitContainer.Ripristino di Backup Pre-configurati• Semplicità in scenari di Disaster Recovery completo.• Ripristino di uno stato consolidato e testato.• Mancanza di granularità: non permette modifiche parziali.• I segreti storici rimangono congelati nel dump del database.Crittografia del dump binario (es. PG_DUMP) tramite chiavi gestite da KMS esterno (Vault) e storicizzazione in bucket S3 protetti.API REST Post-Installazione via Kubernetes Job (Approccio Consigliato)Questa metodologia sfrutta l'API HTTP interna di Autobrr per configurare lo stato applicativo. L'esecuzione avviene tramite un container effimero (Kubernetes Job) che si attiva solo dopo che l'applicazione principale ha completato la fase di bootstrap e le relative migrazioni interne dello schema. La validazione logica operata dal backend impedisce l'inserimento di dati incoerenti, garantendo la stabilità del servizio.La gestione dei segreti in questo flusso si affida all'uso combinato di HashiCorp Vault e External Secrets Operator (ESO). L'operatore ESO interroga il modulo Vault del cluster, estrae le credenziali e genera un Secret Kubernetes di tipo Opaque nel namespace dell'applicazione. Il Job monta questo segreto e, prima di avviare le chiamate HTTP, utilizza un'utilità di templating leggera (come envsubst o script Python nativi) per interpolare le variabili d'ambiente all'interno dei manifest JSON dei filtri e dei client. Questo previene in modo assoluto la presenza di chiavi API in chiaro all'interno dei repository Git.Seeding SQL Diretto su PostgreSQLL'inserimento diretto di record tramite istruzioni INSERT INTO sulle tabelle di sistema di Autobrr (quali download_client, filter o indexer) rappresenta una tentazione comune a causa della sua immediatezza. Tuttavia, i database delle applicazioni moderne sono soggetti a frequenti aggiornamenti di schema guidati da migrazioni interne. L'iniezione manuale bypassa i vincoli di integrità dell'ORM e rischia di generare conflitti sulle sequenze delle chiavi primarie, bloccando l'avvio di Autobrr dopo un aggiornamento dell'immagine del container.In caso si decidesse di percorrere questa strada, i segreti dovrebbero essere gestiti tramite strumenti di crittografia dei manifest Git, come Mozilla SOPS o SealedSecrets. I valori in chiaro delle password o dei token verrebbero cifrati asimmetricamente prima di essere storicizzati nel repository di codice, lasciando che sia un controller interno al cluster a decifrarli e a passarli al pod incaricato dell'esecuzione dello script SQL.Iniezione tramite CLI (autobrrctl)Il binario di supporto autobrrctl permette di interagire con il database ed eseguire alcune operazioni amministrative direttamente da riga di comando. La limitazione intrinseca dello strumento risiede nella sua parzialità: è progettato principalmente per la rotazione delle password, la gestione degli utenti e i processi di conversione o migrazione strutturale del database. Non offre alcuna interfaccia per la dichiarazione sistematica di filtri o client di download.I segreti per questa metodologia vengono gestiti associando un InitContainer al deployment di Autobrr. L'InitContainer attinge ai dati sensibili tramite variabili d'ambiente legate a Secret di Kubernetes. Al momento dell'esecuzione di comandi quali create-user, le password non vengono passate come argomento visibile nei log dei processi, ma veicolate in modo sicuro tramite canali di standard input (stdin).Ripristino di Backup Pre-configuratiIl caricamento di un dump pre-esistente del database PostgreSQL rappresenta una soluzione di ripristino globale, ma si scontra con la filosofia dichiarativa di GitOps. Non è possibile tracciare le differenze (diff) dei singoli filtri o client modificati nel tempo, poiché risiedono all'interno di un file binario o di un unico file SQL monolitico. Inoltre, i segreti di connessione ai servizi esterni rimangono memorizzati all'interno dei record delle tabelle, rendendo complessa la rotazione periodica delle credenziali. I backup devono essere gestiti unicamente come strumenti di ripristino d'emergenza (Disaster Recovery), crittografando i dump tramite algoritmi AES-256 e salvandoli su storage S3 con politiche di accesso ristrette.Pattern di Configurazione Dichiarativa per il Progetto GEMINIDi seguito vengono analizzate le specifiche tecniche e forniti i pattern dichiarativi per l'implementazione dei sei pilastri operativi richiesti dal Progetto GEMINI.1. Credenziali di Accesso (Amministratore)All'avvio iniziale, Autobrr non presenta credenziali di default. L'approccio classico richiede la creazione manuale del primo utente tramite l'interfaccia web. Per automatizzare questo comportamento in un ambiente GitOps senza interazione umana, si utilizza lo strumento CLI autobrrctl integrato nell'immagine ufficiale.Il comando create-user richiede l'accesso al percorso in cui risiede il file di configurazione config.toml (specificato tramite il parametro --config) per determinare la stringa di connessione al database PostgreSQL di CNPG. Poiché la creazione dell'utente è un'operazione che deve avvenire una sola volta all'atto del primo bootstrap, la si racchiude all'interno di un Kubernetes Job contrassegnato con un hook di pre-installazione Helm o un'annotazione di sincronizzazione di Argo CD.La password dell'amministratore viene estratta in modo sicuro da un segreto di Kubernetes e passata direttamente al comando tramite una pipe di sistema, evitando l'esposizione in chiaro nei log del container. Di seguito si riporta il pattern del manifest per questa operazione:YAMLapiVersion: batch/v1
kind: Job
metadata:
  name: autobrr-admin-bootstrap
  namespace: arr
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: bootstrap
        image: ghcr.io/autobrr/autobrr:latest
        env:
        - name: ADMIN_USER
          valueFrom:
            secretKeyRef:
              name: autobrr-credentials
              key: admin-username
        - name: ADMIN_PASS
          valueFrom:
            secretKeyRef:
              name: autobrr-credentials
              key: admin-password
        volumeMounts:
        - name: config-volume
          mountPath: /config
        command:
        - /bin/sh
        - -c
        - |
          # Si attende che il servizio PostgreSQL di CNPG sia raggiungibile
          until pg_isready -h postgres-main-rw.cnpg-system.svc.cluster.local -p 5432; do
            echo "In attesa del database PostgreSQL..."
            sleep 2
          done
          
          # Creazione non interattiva dell'utente amministratore
          # L'argomento del comando deve puntare alla cartella contenente config.toml
          echo "$ADMIN_PASS" | autobrrctl --config /config create-user "$ADMIN_USER" || echo "Utente già configurato."
      volumes:
      - name: config-volume
        persistentVolumeClaim:
          claimName: autobrr-nfs-pvc
2. Connessione al Download Client (qBittorrent)I servizi ospitati all'interno dello stesso cluster Kubernetes devono comunicare sfruttando la risoluzione dei nomi offerta dal CoreDNS interno. qBittorrent, residente nel namespace arr, espone la propria interfaccia di gestione all'indirizzo http://qbittorrent.arr.svc.cluster.local:8080.Per registrare questo client all'interno di Autobrr in modo programmatico, si inoltra una richiesta POST verso l'endpoint /api/download_clients. L'utilizzo di port: 0 nel payload indica ad Autobrr di derivare la porta di connessione direttamente dall'URL fornito nel campo host, evitando conflitti logici. Di seguito viene mostrato lo schema del payload JSON per effettuare tale registrazione, includendo parametri avanzati per il controllo di banda e la gestione delle code:JSON{
  "name": "qBittorrent-Cluster",
  "type": "QBITTORRENT",
  "enabled": true,
  "host": "http://qbittorrent.arr.svc.cluster.local:8080",
  "port": 0,
  "tls": false,
  "tls_skip_verify": true,
  "username": "${QBITTORRENT_USERNAME}",
  "password": "${QBITTORRENT_PASSWORD}",
  "settings": {
    "basic": {
      "auth": true,
      "username": "${QBITTORRENT_USERNAME}",
      "password": "${QBITTORRENT_PASSWORD}"
    },
    "rules": {
      "enabled": true,
      "max_active_downloads": 3,
      "ignore_slow_torrents": true,
      "ignore_slow_torrents_condition": "MAX_DOWNLOADS_REACHED",
      "download_speed_threshold": 10240,
      "upload_speed_threshold": 512
    }
  }
}
3. Integrazione con Prowlarr e Sincronizzazione degli IndexerProwlarr è uno strumento specializzato nella centralizzazione e nel monitoraggio degli indexer e dei tracker Usenet e Torrent. Tuttavia, Autobrr non dispone di un meccanismo nativo di sincronizzazione bidirezionale che consenta di importare in automatico tutte le definizioni dei tracker salvate all'interno di Prowlarr.Per implementare questa integrazione in maniera robusta all'interno del Progetto GEMINI, si adotta una strategia basata su due flussi operativi paralleli:                            +-----------------------------------+
                            |             Prowlarr              |
                            +-----------------+-----------------+
                                              |
                     +------------------------+------------------------+
                     | Sincronizzazione Torznab                        | Sincronizzazione Liste Monitored
                     v                                                 v
         +-----------------------+                         +-----------------------+
         |   Autobrr: Feeds      |                         |       Omegabrr        |
         |  - Tracker Generici   |                         |  - Sincronizzazione   |
         |  - No IRC Support     |                         |    Monitored Movies/TV|
         |  - Usenet Indexers    |                         |  - Filtri Dinamici    |
         +-----------------------+                         +-----------------------+
La gestione di questa architettura si articola come segue:Sincronizzazione tramite Feed Torznab (Pull): Per i tracker che non supportano gli annunci in tempo reale via IRC, si utilizza Prowlarr come proxy Torznab. Nel menu di Prowlarr si copia l'indirizzo del feed dell'indexer (ad esempio: http://prowlarr:9696/15/api?apikey=...). All'interno di Autobrr si registra un nuovo indexer di tipo "Generic Torznab", configurando l'URL del server interno al cluster e inserendo la chiave API globale di Prowlarr come parametro di autorizzazione sicuro.Iniezione Dinamica delle Liste tramite Omegabrr: Per sincronizzare i contenuti effettivamente monitorati all'interno delle istanze di Sonarr e Radarr senza dover definire filtri globali statici che sovraccaricherebbero l'applicazione, si distribuisce nel cluster l'utility Omegabrr. Omegabrr agisce come un demone di sincronizzazione: interroga periodicamente Sonarr/Radarr per ottenere l'elenco dei media desiderati dall'utente e, tramite l'API di Autobrr, aggiorna dinamicamente i filtri interni inserendo solo i titoli richiesti. Questo metodo garantisce la massima efficienza d'azione e azzera il rischio di incorrere in ban dai tracker privati a causa di query API indiscriminate.4. Configurazione delle Notifiche Push (Telegram)La storicizzazione e il monitoraggio degli eventi di acquisizione dei rilasci sono gestiti tramite l'integrazione di canali di notifica esterni. Per configurare in modo dichiarativo un client di notifica basato sul bot API di Telegram, si utilizza l'endpoint /api/notification_clients.Il payload richiede l'inserimento del Token univoco generato tramite il BotFather di Telegram e degli ID numerici delle chat (o canali) di destinazione. Gli eventi di attivazione previsti coprono l'intero spettro operativo dell'applicazione:JSON{
  "name": "Telegram-GEMINI",
  "type": "TELEGRAM",
  "enabled": true,
  "token": "${TELEGRAM_BOT_TOKEN}",
  "targets": "${TELEGRAM_CHAT_ID}",
  "events": [
    "approved",
    "rejected",
    "error",
    "irc_down",
    "irc_up"
  ]
}
5. Definizione e Importazione Dichiarativa di Filtri ComplessiI filtri costituiscono il nucleo operativo di Autobrr. Essi elaborano le stringhe degli annunci in ingresso applicando regole logiche di inclusione ed esclusione.La sintassi dei filtri di Autobrr implementa la logica dei caratteri jolly (wildcard), in cui il carattere * rappresenta una sequenza di zero o più caratteri e ? indica esattamente un singolo carattere. Tutti i campi di testo dei filtri sono trattati nativamente come case-insensitive, eliminando la necessità di duplicare le stringhe per coprire variazioni di maiuscole e minuscole.Un dettaglio tecnico di fondamentale importanza riguarda la gestione dei controlli sulla dimensione dei file. Molti tracker non annunciano la dimensione del rilascio direttamente all'interno della stringa inviata sul canale IRC. Di conseguenza, se all'interno del filtro vengono valorizzati i parametri di dimensione minima (Min. size) o massima (Max. size), Autobrr sarà costretto a effettuare una chiamata API immediata verso il tracker per scaricare il file .torrent al solo scopo di leggerne i metadati ed estrarne la dimensione effettiva. Per evitare di sovraccaricare il server web del tracker — azione che potrebbe tradursi in una revoca delle credenziali API dell'utente — si raccomanda di utilizzare filtri basati su parametri testuali espliciti presenti nell'annuncio (quali codec, risoluzione e sorgente) per determinare l'accettazione logica del rilascio, ricorrendo alle soglie fisiche di dimensione solo in caso di assoluta necessità.Di seguito viene riportata la struttura di un payload JSON completo per l'importazione dichiarativa di un filtro di selezione avanzato ("GEMINI-Movies-Racing") tramite chiamata POST verso /api/filters:JSON{
  "name": "GEMINI-Movies-Racing",
  "enabled": true,
  "priority": 100,
  "use_regex": true,
  "resolutions": ["1080p", "2160p"],
  "codecs": ["H.264", "HEVC", "x265"],
  "sources": ["BluRay", "WEB-DL"],
  "containers": ["MKV"],
  "origins": ["INTERNAL"],
  "years": "2023-2030",
  "match_releases": ".*(FRENCH|MULTi|TRUEFRENCH).*",
  "except_releases": ".*(3D|REMUX|Stereo).*",
  "indexers": [
    {
      "name": "ShareTheFiles",
      "identifier": "sharethefiles"
    }
  ],
  "actions": [
    {
      "name": "Push-to-qBittorrent",
      "type": "QBITTORRENT",
      "enabled": true,
      "client_id": 1,
      "category": "movies-racing",
      "tags": "autobrr-grab",
      "save_path": "/downloads/movies",
      "reannounce_interval": 5,
      "reannounce_max_attempts": 10
    }
  ]
}
6. Architettura dei Feeds in Autobrr: Differenze con IRC (Push vs Pull)Il corretto utilizzo di Autobrr richiede una chiara comprensione delle differenze architetturali e operative che intercorrono tra il recupero dati basato su eventi in tempo reale e il monitoraggio periodico tramite feed strutturati.IRC (Modello Event-Driven / Push)Il protocollo IRC (Internet Relay Chat) rappresenta il meccanismo primario per la partecipazione tempestiva allo sciame iniziale (initial swarm) di un rilascio.Funzionamento: L'applicazione mantiene una connessione persistente verso il server IRC del tracker privato. Nel momento esatto in cui un file viene caricato sulla piattaforma, un bot del tracker invia un messaggio di annuncio sul canale dedicato. Autobrr intercetta immediatamente la stringa, la convalida tramite i filtri attivi e, in caso di esito positivo, invia il torrent al client di download.Latenza: Estremamente ridotta, quantificabile in millisecondi dall'effettivo caricamento sulla sorgente.Impatto sui Server: Minimo. Il server web del tracker non riceve query di ricerca ripetute, poiché l'annuncio viene propagato passivamente sulla rete chat.Feeds (Modello Polling / Pull)I "Feeds" raggruppano le tecnologie di recupero dati basate su interrogazioni cicliche di file XML o JSON, strutturati secondo gli standard RSS, Torznab o Newznab.Funzionamento: Ad intervalli temporali regolari definiti dall'utente (es. ogni 10 o 15 minuti), Autobrr invia una richiesta HTTP GET verso l'URL del feed per ottenere la lista degli ultimi caricamenti.Latenza: Variabile, legata direttamente all'intervallo di polling configurato. Può variare da pochi minuti fino a diverse ore, rendendo questo approccio inadatto per le attività di racing in cui la velocità di associazione ai primi peer determina la riuscita del caricamento.Impatto sui Server: Elevato. Ogni chiamata di polling costringe il server del tracker a elaborare una query e a generare una risposta dinamica. Per questo motivo, i gestori delle piattaforme applicano severe restrizioni temporali all'accesso ai feed, superate le quali l'utenza viene bloccata per eccesso di richieste (Rate Limiting).Meccanismo di Caching dei FeedsPer evitare il download indiscriminato di file già analizzati, Autobrr implementa un sistema di tracciamento dello stato basato su cache relazionale gestita all'interno del database PostgreSQL.Al momento della prima attivazione di un nuovo feed, l'applicazione esegue una cosiddetta "esecuzione a freddo" (cold run). Durante questa fase, Autobrr interroga il feed, estrae l'elenco degli ultimi 25 elementi disponibili e memorizza i relativi identificativi univoci (hash o GUID) all'interno del database, senza inoltrare alcuna richiesta di download ai client. Questo previene lo scaricamento massivo e non intenzionale dello storico dei file presenti sul tracker.A partire dalla seconda esecuzione, il demone confronta gli elementi presenti nel feed con quelli registrati nella cache del database: solo i record inediti vengono processati attraverso la catena dei filtri applicativi. La cache degli elementi storici viene ripulita in modo automatico con cadenza trentennale (ogni 30 giorni), prevenendo una crescita incontrollata delle dimensioni delle tabelle all'interno del cluster CNPG.Architettura del Kubernetes Job di Provisioning ApplicativoPer implementare l'approccio consigliato basato sull'interazione con l'API REST di Autobrr a seguito dell'avvenuta installazione dell'applicazione, si riporta di seguito lo script di automazione inserito all'interno del Kubernetes Job post-installazione. Lo script attende la disponibilità dell'applicazione, recupera in sicurezza i segreti decifrati dall'External Secrets Operator, genera i payload strutturati ed esegue il provisioning dei client, dei canali di notifica e dei filtri complessi.Bash#!/bin/sh
set -e

# Definizione dei percorsi dei segreti generati da ESO nel cluster
API_URL="http://autobrr.arr.svc.cluster.local:7474/api"
AUTOBRR_API_KEY=$(cat /var/run/secrets/autobrr/api-key)

echo "Verifica dello stato di liveness e readiness di Autobrr..."
until curl -s -f -H "X-API-Token: ${AUTOBRR_API_KEY}" "${API_URL}/healthz/readiness" > /dev/null; do
  echo "Autobrr non è ancora pronto. Attesa di 5 secondi..."
  sleep 5
done

echo "Autobrr è operativo. Avvio del provisioning dichiarativo..."

# 1. Configurazione del Download Client (qBittorrent)
# Le credenziali vengono lette dai file montati dal Secret Kubernetes
Q_USER=$(cat /var/run/secrets/qbittorrent/username)
Q_PASS=$(cat /var/run/secrets/qbittorrent/password)

CLIENT_PAYLOAD=$(cat <<EOF
{
  "name": "qBittorrent-GEMINI",
  "type": "QBITTORRENT",
  "enabled": true,
  "host": "http://qbittorrent.arr.svc.cluster.local:8080",
  "port": 0,
  "tls": false,
  "tls_skip_verify": true,
  "username": "${Q_USER}",
  "password": "${Q_PASS}",
  "settings": {
    "basic": {
      "auth": true,
      "username": "${Q_USER}",
      "password": "${Q_PASS}"
    },
    "rules": {
      "enabled": true,
      "max_active_downloads": 3,
      "ignore_slow_torrents": true,
      "ignore_slow_torrents_condition": "MAX_DOWNLOADS_REACHED"
    }
  }
}
EOF
)

echo "Registrazione del client qBittorrent..."
curl -X POST "${API_URL}/download_clients" \
  -H "X-API-Token: ${AUTOBRR_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "${CLIENT_PAYLOAD}"

# 2. Configurazione delle Notifiche Telegram
TG_TOKEN=$(cat /var/run/secrets/telegram/token)
TG_CHAT=$(cat /var/run/secrets/telegram/chat-id)

TELEGRAM_PAYLOAD=$(cat <<EOF
{
  "name": "Telegram-Alerts",
  "type": "TELEGRAM",
  "enabled": true,
  "token": "${TG_TOKEN}",
  "targets": "${TG_CHAT}",
  "events": ["approved", "rejected", "error", "irc_down", "irc_up"]
}
EOF
)

echo "Configurazione del canale di notifica Telegram..."
curl -X POST "${API_URL}/notification_clients" \
  -H "X-API-Token: ${AUTOBRR_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "${TELEGRAM_PAYLOAD}"

# 3. Importazione del Filtro di Rilascio Complesso
FILTER_PAYLOAD=$(cat <<EOF
{
  "name": "GEMINI-Movies-Racing",
  "enabled": true,
  "priority": 100,
  "use_regex": true,
  "resolutions": ["1080p", "2160p"],
  "codecs": ["H.264", "HEVC", "x265"],
  "sources": ["BluRay", "WEB-DL"],
  "containers": ["MKV"],
  "origins": ["INTERNAL"],
  "years": "2023-2030",
  "match_releases": ".*(FRENCH|MULTi|TRUEFRENCH).*",
  "except_releases": ".*(3D|REMUX|Stereo).*",
  "indexers": []
}
EOF
)

echo "Importazione del filtro di selezione dei rilasci..."
curl -X POST "${API_URL}/filters" \
  -H "X-API-Token: ${AUTOBRR_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "${FILTER_PAYLOAD}"

echo "Provisioning completato con successo per il Progetto GEMINI."
