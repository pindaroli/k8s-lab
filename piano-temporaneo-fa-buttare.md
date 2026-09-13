Architettura di Disaster Recovery e Failover Bidirezionale per Jellyfin: Sincronizzazione Consistente tra Ambienti Eterogenei Proxmox LXC e TrueNAS Docker (Specifiche Jellyfin 12.0)L'erogazione continua di un'infrastruttura multimediale basata su Jellyfin 12.0 tra due ambienti architetturalmente eterogenei richiede una precisa scomposizione tra lo stato transazionale dell'applicazione, la topologia di rete e i profili di accelerazione hardware.Con il rilascio della versione 12.0 (che abbandona formalmente la storica numerazione 10.x.x e consolida la radicale ristrutturazione del backend avviata con Entity Framework Core), l'architettura interna dei dati subisce una profonda semplificazione strutturale: il vecchio modello a doppio database SQLite (jellyfin.db e library.db) scompare definitivamente in favore di un unico database unificato e relazionale.Nel contesto in esame:Il nodo primario di produzione è attestato su un container Proxmox LXC (Debian nativo) operante su microarchitettura Intel con grafica integrata QuickSync (driver iHD, FFmpeg 8.1) passata tramite /dev/dri/renderD128.Il nodo di failover secondario è implementato come container Docker (lscr.io/linuxserver/jellyfin:12.0.0) su piattaforma TrueNAS SCALE Bare Metal, alimentata da APU AMD Ryzen Cezanne con grafica Radeon Vega e stack VAAPI (radeonsi).L'attivazione di un failover bidirezionale senza soluzione di continuità e senza perdite di dati transazionali impone la risoluzione di quattro criticità sistemistiche:La segregazione fisica tra le configurazioni legate al silicio (encoding.xml) e i metadati applicativi.La neutralizzazione delle barriere di accesso L3 introdotte dalla virtualizzazione di rete Docker.La preservazione dell'identità crittografica del server multimediale (<ServerId>) per evitare la deregistrazione massiva dei client.La garanzia della consistenza transazionale del motore relazionale SQLite/EF Core durante le fasi di trasferimento dati su storage ZFS.1. Anatomia dei Dati in Jellyfin 12.0: Architettura Unificata EF Core, XML e File SystemA differenza delle release legacy della serie 10.10.x, Jellyfin 12.0 consolida a regime il sottosistema di persistenza basato su Entity Framework Core (EF Core). La storica frammentazione tra database concorrenti è superata: tutte le entità risiedono ora all'interno di un'unica base dati relazionale con chiavi esterne e integrità referenziale nativa.Il Ruolo del Database Unificato jellyfin.dbTutti i dati strutturati risiedono nella sottodirectory data/ (/var/lib/jellyfin/data/ nell'LXC Debian e /config/data/ nell'immagine LinuxServer Docker) e operano con journalizzazione Write-Ahead Logging (WAL):jellyfin.db (Unificato): In Jellyfin 12.0, questo singolo file racchiude l'intero stato operativo del server:Autenticazione e Utenze: Tabelle utenti, credenziali con hash Argon2, policy di accesso, sessioni attive e token crittografici dei dispositivi.UserData (Storico Visioni): La tabella UserData mantiene le tuple utente-media con lo stato di visualizzazione (IsPlayed), la posizione temporale esatta espressa in tick (PlaybackPositionTicks), il contatore riproduzioni (PlayCount) e i segnalibri/preferiti (IsFavorite).Catalogo Multimediale (ex library.db): Tutti i metadati delle librerie (film, serie, stagioni, episodi, brani musicali, e il nuovo supporto nativo per libri/fumetti) sono migrati e gestiti da tabelle EF Core all'interno di jellyfin.db.Playlists e Collezioni Ristrutturate: In 12.0 le collezioni e le playlist non sono più memorizzate come liste serializzate grezze, bensì come entità relazionali vere e proprie nella nuova tabella LinkedChildren, con chiavi esterne GUID (OwnerId, PrimaryVersionId).File Temporanei WAL e SHM (jellyfin.db-wal, jellyfin.db-shm): Costituiscono la memoria transazionale attiva e l'indice di memoria condivisa. EF Core introduce un proprio layer di gestione dei lock in scrittura; pertanto, sincronizzare il file system mentre il demone è attivo o mentre il file WAL contiene pagine non riversate (uncommitted) comporta il danneggiamento logico immediato dell'intera istanza.I File di Configurazione XMLI descrittori XML risiedono nella directory radice di configurazione (/etc/jellyfin/ su Debian LXC, /config/ nel container Docker) e continuano a regolare i parametri operativi di base del runtime ASP.NET Core Kestrel:system.xml: Contiene l'identità dell'istanza. Il parametro cardine è <ServerId>, una stringa GUID univoca. I client Jellyfin (web, TV, mobile) memorizzano localmente il <ServerId> per validare i token di sessione. Qualora il GUID differisse tra il nodo Proxmox e il nodo TrueNAS, qualsiasi client autenticato verrebbe immediatamente disconnesso con richiesta di re-login manuale.network.xml: Istruisce Kestrel su porte HTTP/HTTPS (<InternalHttpPort>, <InternalHttpsPort>), interfacce di rete consentite, subnet considerate locali (<LocalNetworkSubnets>) e blocco del traffico extra-subnets (<EnableRemoteAccess>).encoding.xml: Definisce l'accelerazione hardware della pipeline FFmpeg 8.1 (<HardwareAccelerationType>), i render nodes (<VaapiDevice>), il tone mapping HDR dinamico e i formati di decodifica abilitati per codec moderni (H.264, HEVC 10-bit, VP9, AV1).Le Directory di Dati Specializzate su File SystemAll'interno della cartella data/ sono allocate risorse ausiliarie su file system:data/users/<GUID>/: File JSON contenenti la disposizione personalizzata dei widget dell'interfaccia utente (nuovo Modern Web Layout standard in 12.0).data/subtitles/: Repository delle tracce dei sottotitoli scaricate on-demand o estratte runtime dai file multimediali.Componente ArchitetturalePercorso File SystemFunzione Primaria (Jellyfin 12.0)Dinamismo DatiPortabilità tra Host Eterogeneijellyfin.dbdata/jellyfin.dbDatabase Unificato EF Core: Utenti, permessi, sessioni, UserData, catalogo media, collezioni e playlist.Continuo (a ogni transazione di visione/modifica)Totale (richiede checkpoint WAL e versione identica)library.dbdata/library.dbDeprecato ed eliminato in 12.0 (non più utilizzato).N/ANon replicare / eliminabile.system.xmlRoot Config (/config o /etc/jellyfin)Identità istanza (<ServerId>) e flag di setup.StaticoSelettiva (solo <ServerId> deve essere identico).network.xmlRoot Config (/config o /etc/jellyfin)Binding Kestrel, subnet LAN autorizzate, policy remote.StaticoNessuna (strettamente vincolato allo stack L3 host).encoding.xmlRoot Config (/config o /etc/jellyfin)API accelerazione GPU (QSV vs VAAPI), filtri HDR.StaticoNessuna (strettamente dipendente dal silicio GPU).data/users/data/users/<GUID>/Layout visuali e dashboard profili utente.BassoTotale.data/subtitles/data/subtitles/Tracce sottotitoli esterne ed estratte.IncrementaleTotale.2. Risoluzione del Blocco di Rete su Docker TrueNASDiagnostica del Blocco 403 ForbiddenL'errore "We're unable to connect to the selected server right now" è causato dal sottosistema NetworkManager di Jellyfin.In configurazione standard con bridge Docker (172.18.0.0/16), Jellyfin interroga lo stack TCP/IP locale del container. Con il tag <LocalNetworkSubnets /> vuoto, il server elegge esclusivamente la subnet virtuale del container (172.18.0.0/16) come perimetro LAN legittimo.Quando i client della VLAN 10.10.20.0/24 instradano il traffico verso l'interfaccia fisica di TrueNAS (10.10.10.50:8096), i pacchetti IP raggiungono Kestrel esponendo come sorgente l'indirizzo reale 10.10.20.x (o l'IP del gateway NAT). Poiché tale IP non appartiene a 172.18.0.0/16 e la direttiva <EnableRemoteAccess> è impostata a false, Jellyfin classifica la chiamata API come tentativo di accesso WAN non autorizzato, bloccandola con codice HTTP 403 Forbidden.Valutazione Comparativa: Bridge con Iniezione Subnet vs Network HostParametro ArchitetturaleDocker Bridge + Subnet InjectionDocker network_mode: host (Scelta Raccomandata)Trasparenza dello Stack di ReteBassa: impone la manipolazione statica o scriptata di network.xml.Totale: il container condivide direttamente i socket di rete del kernel di TrueNAS SCALE.Preservazione IP ClientDipendente dalle regole NAT/iptables del bridge.Nativa: nessun livello di Source NAT intermedio, l'IP originale è preservato.Autodiscovery (SSDP / DLNA)Compromesso o nullo: i pacchetti multicast UDP non transitano attraverso il bridge senza relay esterni.Nativo: pacchetti broadcast e multicast su porte 1900/7359 visibili direttamente sulla LAN.Overhead di RetePresente: attraversamento dei moduli conntrack, iptables e interfaccia virtuale veth.Nullo: instradamento a velocità di linea senza penalty computazionale.Rischio di Config DriftElevato: sovrascritture accidentali di network.xml bloccano l'accesso web.Nullo: l'istanza non dipende dalle mappature porte Docker o da bridge esterni.La soluzione architetturale definitiva per il container Docker su TrueNAS SCALE consiste nell'impostare network_mode: host all'interno del descrittore Compose.Per garantire che Jellyfin tratti tutte le classi di indirizzi dell'infrastruttura come locali anche in scenari di routing complessi, il file isolato /mnt/stripe/k8s-arr/servarr-jellyfin-config/network.xml su TrueNAS deve essere staticamente preconfigurato come segue:XML<?xml version="1.0" encoding="utf-8"?>
<NetworkConfiguration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <InternalHttpPort>8096</InternalHttpPort>
  <InternalHttpsPort>8920</InternalHttpsPort>
  <PublicHttpPort>8096</PublicHttpPort>
  <PublicHttpsPort>8920</PublicHttpsPort>
  <EnableRemoteAccess>true</EnableRemoteAccess>
  <LocalNetworkSubnets>
    <string>10.10.0.0/16</string>
  </LocalNetworkSubnets>
</NetworkConfiguration>
3. Strategia di Sincronizzazione Bidirezionale e Isolamento HardwareDefinizione del Perimetro Esatto di ReplicaCon Jellyfin 12.0, il processo di sincronizzazione bidirezionale risulta notevolmente semplificato e reso più robusto grazie all'eliminazione di library.db. La replica deve operare esclusivamente sulla cartella dei dati applicativi:LXC Debian: /var/lib/jellyfin/data/TrueNAS SCALE: /mnt/stripe/k8s-arr/servarr-jellyfin-db/Oggetti ammessi alla replica bidirezionale:jellyfin.db: Il database unificato SQLite/EF Core contenente utenti, cataloghi, metadati e storico di fruizione (UserData).Eventuali file transazionali post-chiusura: jellyfin.db-wal e jellyfin.db-shm.Directory data/users/: Impostazioni personalizzate della nuova Modern UI introdotta in 12.0.Directory data/subtitles/: Archivio dei sottotitoli.Oggetti esclusi categoricamente dalla replica:encoding.xml: Incompatibilità architetturale tra GPU Intel QuickSync e GPU AMD Vega.network.xml: Parametri di rete dipendenti dall'ambiente host.system.xml: Parametri di sistema locali (il <ServerId> deve essere allineato una sola volta durante la messa in funzione iniziale).library.db*: File obsoleti di precedenti release 10.x, non più utilizzati in 12.0.File di log (*.log) e directory volatili transcodes/ e cache/.Isolamento Hardware della Transcodifica (Intel QSV vs AMD VAAPI)In Jellyfin 12.0 il motore di transcodifica adotta FFmpeg 8.1 come stack predefinito. Le opzioni di compilazione e i filtri di accelerazione hardware divergono in base all'hardware sottostante:Nodo Primario LXC: Grafica Intel UHD con QuickSync Video (qsv), driver Intel Compute Runtime OpenCL e VPP Tonemapping per flussi HDR.Nodo di Riserva TrueNAS: APU AMD Ryzen Cezanne con grafica Radeon Vega, driver open-source Mesa radeonsi tramite interfaccia VAAPI generica (vaapi).Qualora encoding.xml venisse accidentalmente scambiato tra gli host, Jellyfin tenterebbe di invocare filtri di decodifica non supportati dal driver caricato nel kernel, provocando il fallimento immediato delle sessioni di transcodifica.I due file devono risiedere esclusivamente nella rispettiva root di configurazione locale.Configurazione LXC Intel QSV (/etc/jellyfin/encoding.xml):XML<?xml version="1.0" encoding="utf-8"?>
<EncodingOptions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <HardwareAccelerationType>qsv</HardwareAccelerationType>
  <VaapiDevice>/dev/dri/renderD128</VaapiDevice>
  <EnableDecodingColorDepth10Hevc>true</EnableDecodingColorDepth10Hevc>
  <EnableDecodingColorDepth10Vp9>true</EnableDecodingColorDepth10Vp9>
  <EnableDecodingColorDepth10Av1>true</EnableDecodingColorDepth10Av1>
  <EnableEnhancedNvdecDecoder>false</EnableEnhancedNvdecDecoder>
  <EnableTonemapping>true</EnableTonemapping>
  <EnableVppTonemapping>true</EnableVppTonemapping>
</EncodingOptions>
Configurazione TrueNAS Docker AMD Vega (/mnt/stripe/k8s-arr/servarr-jellyfin-config/encoding.xml):XML<?xml version="1.0" encoding="utf-8"?>
<EncodingOptions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <HardwareAccelerationType>vaapi</HardwareAccelerationType>
  <VaapiDevice>/dev/dri/renderD128</VaapiDevice>
  <EnableDecodingColorDepth10Hevc>true</EnableDecodingColorDepth10Hevc>
  <EnableDecodingColorDepth10Vp9>true</EnableDecodingColorDepth10Vp9>
  <EnableDecodingColorDepth10Av1>false</EnableDecodingColorDepth10Av1>
  <EnableEnhancedNvdecDecoder>false</EnableEnhancedNvdecDecoder>
  <EnableTonemapping>true</EnableTonemapping>
  <EnableVppTonemapping>false</EnableVppTonemapping>
</EncodingOptions>
Parità Assoluta dei Percorsi Storage MultimedialiNel database EF Core unificato di Jellyfin 12.0, tutti i file multimediali sono referenziati tramite il loro percorso assoluto POSIX.Se il container Docker su TrueNAS montasse lo share NFS su /media, all'avvio Jellyfin non troverebbe i file nei percorsi originali registrati nel database (/mnt/oliraid/arrdata/media/...). In Jellyfin 12.0 il controllo di coerenza all'avvio è particolarmente rigoroso e pulisce i record non trovati sul disco; una discrepanza nei percorsi provocherebbe la cancellazione immediata di tutte le voci della libreria.Il container Docker su TrueNAS deve replicare esattamente il mount point di produzione:- /mnt/oliraid/arrdata/media:/mnt/oliraid/arrdata/media:roRiconciliazione dei Permessi POSIX (UID/GID Shifting)Sui container Proxmox LXC unprivileged, il kernel applica un mapping scalare agli ID utente (di base +100000). Il demone Jellyfin in esecuzione nell'LXC con UID 105 scrive su disco ZFS come proprietario 100105:100110.Sul nodo TrueNAS SCALE, il container Docker LinuxServer opera invece con i parametri PUID=1000 e PGID=1000 associati all'amministratore locale.La replica con rsync deve escludere i metadati di ownership (--no-owner --no-group), delegando ad Ansible la normalizzazione esplicita dei permessi POSIX prima dell'avvio del container di ricezione, evitando blocchi di scrittura o errori critici di SQLite (disk I/O error).4. Procedura Operativa di Disaster Recovery e Failover AutomatizzatoCon l'adozione di Jellyfin 12.0 e l'unificazione del database, la sequenza automatizzata gestisce unicamente il file transazionale jellyfin.db, riducendo le finestre di fermo e azzerando i rischi di disallineamento tra database multipli.Sequenza di Failover (Andata): Da Proxmox LXC a TrueNAS Bare MetalYAML---
- name: Disaster Recovery Jellyfin 12.0 - Transizione da PVE LXC a TrueNAS Docker
  hosts: localhost
  gather_facts: false
  vars:
    pve_node: "10.10.20.32"
    truenas_host: "10.10.10.50"
    lxc_vmid: "2200"
    pve_zfs_dataset: "/rpool/data/jellyfin-db/"
    truenas_db_path: "/mnt/stripe/k8s-arr/servarr-jellyfin-db/"
    truenas_compose_file: "/mnt/stripe/k8s-arr/docker-compose-jellyfin.yml"
    truenas_puid: "1000"
    truenas_pgid: "1000"

  tasks:
    - name: 1. Arresto controllato del servizio Jellyfin 12.0 nell'LXC
      ansible.builtin.command: >
        pct exec {{ lxc_vmid }} -- systemctl stop jellyfin
      delegate_to: "{{ pve_node }}"

    - name: 2. Checkpoint esplicito del WAL per consolidare jellyfin.db
      ansible.builtin.command: >
        pct exec {{ lxc_vmid }} -- sqlite3 /var/lib/jellyfin/data/jellyfin.db "PRAGMA wal_checkpoint(TRUNCATE);"
      delegate_to: "{{ pve_node }}"

    - name: 3. Arresto completo del Container Proxmox LXC 2200
      ansible.builtin.command: >
        pct stop {{ lxc_vmid }}
      delegate_to: "{{ pve_node }}"

    - name: 4. Replica differenziale consistente verso TrueNAS SCALE
      ansible.posix.rsync:
        src: "{{ pve_zfs_dataset }}"
        dest: "root@{{ truenas_host }}:{{ truenas_db_path }}"
        mode: push
        delete: yes
        archive: yes
        rsync_opts:
          - "--no-owner"
          - "--no-group"
          - "--exclude=*.log"
          - "--exclude=transcodes/"
          - "--exclude=cache/"
          - "--exclude=library.db*"
          - "--exclude=encoding.xml"
          - "--exclude=network.xml"
          - "--exclude=system.xml"
      delegate_to: "{{ pve_node }}"

    - name: 5. Allineamento permessi POSIX per runtime Docker TrueNAS (UID 1000)
      ansible.builtin.file:
        path: "{{ truenas_db_path }}"
        owner: "{{ truenas_puid }}"
        group: "{{ truenas_pgid }}"
        recurse: yes
      delegate_to: "{{ truenas_host }}"

    - name: 6. Avvio dello stack Docker Jellyfin 12.0 su TrueNAS SCALE
      ansible.builtin.command: >
        docker compose -f {{ truenas_compose_file }} up -d
      delegate_to: "{{ truenas_host }}"

    - name: 7. Verifica disponibilità endpoint API Kestrel su TrueNAS
      ansible.builtin.uri:
        url: "http://{{ truenas_host }}:8096/System/Info/Public"
        status_code: 200
      register: truenas_health
      until: truenas_health.status == 200
      retries: 15
      delay: 4

    - name: 8. Poweroff ordinato dei nodi fisici del cluster Proxmox
      ansible.builtin.command: systemctl poweroff
      delegate_to: "{{ item }}"
      loop:
        - "10.10.20.30"
        - "10.10.20.31"
        - "10.10.20.32"
Specifica Docker Compose per il Nodo di Riserva (TrueNAS SCALE)YAMLservices:
  jellyfin:
    image: lscr.io/linuxserver/jellyfin:12.0.0
    container_name: jellyfin-failover
    network_mode: host
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Rome
    volumes:
      - /mnt/stripe/k8s-arr/servarr-jellyfin-config:/config
      - /mnt/stripe/k8s-arr/servarr-jellyfin-db:/config/data
      - /mnt/oliraid/arrdata/media:/mnt/oliraid/arrdata/media:ro
    devices:
      - /dev/dri:/dev/dri
    restart: unless-stopped
Sequenza di Ripristino (Failback): Da TrueNAS Bare Metal a Proxmox LXCAl termine dell'emergenza o della manutenzione, le variazioni registrate dagli utenti su TrueNAS (nuove visioni nella tabella UserData, avanzamenti dei tick di riproduzione, modifiche ai preferiti o scalette musicali) vengono riportate in modo atomico sull'LXC.YAML---
- name: Disaster Recovery Jellyfin 12.0 - Rientro da TrueNAS Docker a PVE LXC
  hosts: localhost
  gather_facts: false
  vars:
    pve_node: "10.10.20.32"
    truenas_host: "10.10.10.50"
    lxc_vmid: "2200"
    pve_zfs_dataset: "/rpool/data/jellyfin-db/"
    truenas_db_path: "/mnt/stripe/k8s-arr/servarr-jellyfin-db/"
    truenas_compose_file: "/mnt/stripe/k8s-arr/docker-compose-jellyfin.yml"
    lxc_shifted_uid: "100105"
    lxc_shifted_gid: "100110"

  tasks:
    - name: 1. Arresto controllato del container Jellyfin su TrueNAS
      ansible.builtin.command: >
        docker compose -f {{ truenas_compose_file }} stop
      delegate_to: "{{ truenas_host }}"

    - name: 2. Esecuzione manuale checkpoint WAL sul database jellyfin.db
      ansible.builtin.command: >
        sqlite3 {{ truenas_db_path }}jellyfin.db "PRAGMA wal_checkpoint(TRUNCATE);"
      delegate_to: "{{ truenas_host }}"

    - name: 3. Distruzione container Docker su TrueNAS per liberare descrittori
      ansible.builtin.command: >
        docker compose -f {{ truenas_compose_file }} down
      delegate_to: "{{ truenas_host }}"

    - name: 4. Attesa raggiungibilità nodo primario Proxmox (avviato via WoL/IPMI)
      ansible.builtin.wait_for:
        host: "{{ pve_node }}"
        port: 22
        state: started
        timeout: 300

    - name: 5. Replica a ritroso delle modifiche transazionali verso ZFS PVE3
      ansible.posix.rsync:
        src: "{{ truenas_db_path }}"
        dest: "root@{{ pve_node }}:{{ pve_zfs_dataset }}"
        mode: push
        delete: yes
        archive: yes
        rsync_opts:
          - "--no-owner"
          - "--no-group"
          - "--exclude=*.log"
          - "--exclude=transcodes/"
          - "--exclude=cache/"
          - "--exclude=library.db*"
          - "--exclude=encoding.xml"
          - "--exclude=network.xml"
          - "--exclude=system.xml"
      delegate_to: "{{ truenas_host }}"

    - name: 6. Ripristino dei permessi compatibili con UID shifting LXC
      ansible.builtin.file:
        path: "{{ pve_zfs_dataset }}"
        owner: "{{ lxc_shifted_uid }}"
        group: "{{ lxc_shifted_gid }}"
        recurse: yes
      delegate_to: "{{ pve_node }}"

    - name: 7. Avvio del container LXC 2200 su Proxmox
      ansible.builtin.command: >
        pct start {{ lxc_vmid }}
      delegate_to: "{{ pve_node }}"

    - name: 8. Avvio del demone di sistema Jellyfin all'interno dell'LXC
      ansible.builtin.command: >
        pct exec {{ lxc_vmid }} -- systemctl start jellyfin
      delegate_to: "{{ pve_node }}"

    - name: 9. Convalida disponibilità endpoint API Kestrel primario
      ansible.builtin.uri:
        url: "http://{{ pve_node }}:8096/System/Info/Public"
        status_code: 200
      register: lxc_health
      until: lxc_health.status == 200
      retries: 15
      delay: 3
5. Sintesi Operativa e Prerequisiti per l'Upgrade a Jellyfin 12.0L'adozione di Jellyfin 12.0 consolida notevolmente la robustezza dell'infrastruttura di disaster recovery:Unico Punto di Sincronizzazione: L'eliminazione di library.db e l'accentramento di tutte le tabelle relazionali e dello stato visioni in jellyfin.db evita disallineamenti tra metadati e dati utente durante la retro-copia.Ottimizzazioni EF Core: Le query per la navigazione e il recupero dello stato di riproduzione sfruttano l'indicizzazione nativa della tabella LinkedChildren e le chiavi esterne, eliminando le latenze su playlist e cataloghi complessi.Isolamento dell'Accelerazione: Mantenere segregati i file encoding.xml protegge le pipeline multimediali basate su FFmpeg 8.1, permettendo al silicio Intel QuickSync di operare con filtri OpenCL VPP su LXC e alla GPU AMD Vega di sfruttare VAAPI radeonsi su TrueNAS.Avvertenza sull'Upgrade Iniziale a 12.0:
La migrazione da una versione precedente (10.10.7 o 10.11.x) a Jellyfin 12.0 riscrive completamente lo schema relazionale al primo avvio. Questa procedura deve essere eseguita esclusivamente sul nodo primario Proxmox LXC, assicurandosi di:Eseguire un backup completo a freddo prima del primo avvio.Verificare che non esistano account utente con nomi duplicati per differenza di maiuscole/minuscole (in 12.0 i nomi utente sono case-insensitive con indice unico).Lasciare completare la migrazione iniziale e la scansione completa della libreria prima di avviare per la prima volta la sincronizzazione verso TrueNAS.Bloccare le versioni dei binari Debian su LXC e l'immagine Docker su TrueNAS al medesimo tag esatto (12.0.0), evitando derive di schema non retrocompatibili.