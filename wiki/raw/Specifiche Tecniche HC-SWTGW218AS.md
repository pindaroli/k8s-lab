# **Specifiche Tecniche, Architettura Hardware, Ecosistema Firmware e Sistemi di Monitoraggio dello Switch HC-SWTGW218AS**

## **Architettura Hardware e Componentistica di Rete**

Lo switch HC-SWTGW218AS (distribuito sotto vari marchi OEM tra cui Horaco, Sodola con il codice SL902-SWTGW218AS, Lianguo e Optfocus) si basa su un'architettura integrata a basso consumo prodotta da Realtek1. Il piano di commutazione logico è governato dal controller principale **Realtek RTL8373**, coadiuvato dal ricetrasmettitore PHY multi-velocità **Realtek RTL8224**3. Questa combinazione offre una capacità di commutazione complessiva di 60 Gbps e un tasso di inoltro dei pacchetti pari a 44,64 Mpps, garantendo prestazioni wire-speed non bloccanti su tutte le interfacce1.
L'apparato dispone di otto porte RJ45 conformi allo standard IEEE 802.3bz (2.5G Base-T) e di una singola porta SFP+ operante a 10 Gbps1. Le porte RJ45 sono retrocompatibili con le velocità di 1000M e 100M7. La porta SFP+ gestisce moduli ottici (10GBASE-SR/LR), cavi DAC (Direct Attach Copper) e ricetrasmettitori attivi RJ45 a 10 Gbps7.
La progettazione fisica presenta alcune peculiarità riscontrate dagli operatori in fase di installazione. I connettori RJ45 mostrano una tolleranza meccanica ristretta rispetto ai fermi di plastica delle clip dei cavi ethernet9. Questo difetto costruttivo comporta una notevole resistenza all'inserimento: mentre i cavi pre-assemblati industriali si agganciano applicando una pressione elevata, i cavi crimpati manualmente spesso non riescono a completare lo scatto di blocco9. Lo chassis in lega di alluminio integra un connettore di messa a terra a vite dedicato e garantisce una schermatura elettromagnetica accoppiata a una protezione da fulmini e sovratensioni fino a 4KV sulle porte in rame4.

| Componente / Parametro | Specifica Tecnica Ufficiale | Dettagli di Implementazione |
| :---- | :---- | :---- |
| **Chipset Switch** | Realtek RTL83733 | Controller di commutazione Layer 2 integrato6 |
| **Chipset PHY** | Realtek RTL82243 | Ricetrasmettitore multi-gigabit a basso consumo6 |
| **Configurazione Porte** | 8x 2.5G RJ45 \+ 1x 10G SFP+1 | Tutte le porte sono posizionate sul pannello frontale12 |
| **Capacità di Switching** | 60 Gbps1 | Architettura non bloccante7 |
| **Throughput Massimo** | 44,64 Mpps4 | Prestazioni wire-speed costanti su frame standard |
| **Tabella MAC Address** | 4K voci5 | Supporto per l'apprendimento dinamico e statico13 |
| **Dimensioni Fisiche** | 175 x 73 x 28 mm4 | Involucro metallico compatto fanless con piedi magnetici8 |
| **Protezione Elettrica** | Scarica fino a 4KV4 | Protezione da sovratensioni sulle porte RJ454 |

## **Alimentazione, Assorbimento Elettrico e Comportamento Termico**

L'efficienza energetica dello switch HC-SWTGW218AS è legata direttamente all'utilizzo del silicio Realtek ad alta integrazione6. Il dispositivo viene alimentato tramite un trasformatore esterno da parete certificato CE/EC con uscita a corrente continua (DC) da 12V e un'erogazione massima compresa tra 1A e 1,5A4.
Il consumo elettrico reale dello switch varia in base al carico di traffico e alla tipologia di supporti fisici collegati alle porte12. In condizioni di inattività (idle, senza connessioni attive), il consumo del solo circuito logico si attesta tra i 2W e i 3W12. Ciascun collegamento attivo a 2.5 Gbps genera un incremento marginale dell'assorbimento di circa 0,7W per porta, portando il consumo medio con gran parte delle porte RJ45 occupate a circa 5W11.
La variabile critica nell'economia energetica del dispositivo è rappresentata dalla porta SFP+15. Se popolata con moduli in fibra ottica o cavi DAC passivi, l'assorbimento rimane pressoché invariato, mantenendo lo switch entro la soglia dei 5W \- 5,5W complessivi9. Se invece si installa un ricetrasmettitore SFP+ RJ45 in rame a 10 Gbps (come il modello 10Gtek ASF-10G2-T), il solo modulo richiede un'alimentazione aggiuntiva di circa 2,5W14. Questa configurazione spinge l'assorbimento globale verso il limite massimo di targa di 12W e genera un carico termico critico all'interno dello switch5.
Essendo un apparato a dissipazione totalmente passiva (fanless), lo smaltimento del calore è affidato alla conduzione termica dello chassis1. I pad termici posizionati sotto la scheda logica trasferiscono il calore dei chip direttamente sulla piastra metallica inferiore11.

| Condizione Operativa dello Switch | Consumo Elettrico Rilevato | Temperatura del Case (Ambiente 28-29°C) |
| :---- | :---- | :---- |
| **Standby / Idle (Nessun link attivo)** | 2,0W \- 3,0W12 | \~32°C (Appoggiato su superficie piana)12 |
| **Operativo standard (3 porte attive a 2.5G)** | \~3,5W12 | \~35°C (Montaggio verticale in rack)12 |
| **Carico medio-alto (7-8 porte attive a 2.5G)** | \~5,0W11 | 35°C \- 37°C (Superficie), 39°C \- 40°C (Griglia di espulsione)12 |
| **Carico massimo (Porte 2.5G attive \+ Modulo 10G Copper)** | 10,0W \- 12,0W5 | \>45°C sullo chassis (Il modulo SFP+ supera i 60°C)12 |

L'uso di staffe di montaggio orientate verticalmente consente di sfruttare il moto convettivo dell'aria attraverso le griglie di aerazione laterali dello switch8. Questa installazione riduce la temperatura operativa interna di circa il 40% rispetto al posizionamento orizzontale statico su superfici non conduttive, un fattore fondamentale per prevenire la perdita di pacchetti sotto carichi di rete pesanti e prolungati8.

## **Ecosistema dei Firmware Ufficiali e Revisioni Hardware**

La gestione del firmware originale del modello HC-SWTGW218AS richiede estrema cautela a causa della presenza sul mercato di revisioni hardware non intercambiabili dal punto di vista del codice eseguibile18. La mancata corrispondenza tra la versione della scheda e l'immagine binaria provoca il bootloop distruttivo del dispositivo, caratterizzato dall'accensione fissa del LED di stato verde seguita da una sequenza di lampeggi arancioni di tutte le porte ogni cinque secondi18.

### **Segmentazione delle Revisioni Hardware**

Il parco macchine è diviso in due principali rami di produzione18:

* **Hardware Revision V1.1:** Utilizza il firmware di stock della serie V1.x (tra cui la release diffusa V1.9.1 del 10 Maggio 2024 e la V1.3)19.
* **Hardware Revision V200.x:** Utilizza il firmware nativo della serie V200.x (ad esempio V200.1.10, V200.1.16 o V200.1.30)18. I tentativi di declassare o forzare un firmware V1.x su questa scheda causano il bricking immediato18. Inoltre, in queste unità l'interfaccia di programmazione U-Boot ha rimosso la password standard "Switch321", impedendo il recupero seriale semplificato18.

### **Caratteristiche e Limitazioni del Firmware OEM**

Il firmware originale è accessibile via browser all'indirizzo IP di default 192.168.2.113. Per effettuare il primo accesso, la scheda di rete del computer deve essere configurata manualmente sulla sottorete del dispositivo (impostando ad esempio l'IP 192.168.2.x con subnet mask 255.255.255.0)13.
L'interfaccia di gestione di fabbrica presenta forti limitazioni funzionali9:

* **VLAN di Gestione Fissa:** La configurazione dello switch è bloccata sulla VLAN ID 120. Questo impedisce di isolare il traffico amministrativo all'interno di una VLAN di management sicura, esponendo l'interfaccia a potenziali attacchi di rete21.
* **Configurazione Link Aggregation:** Sebbene il manuale d'uso citi un'opzione per il protocollo dinamico LACP (IEEE 802.3ad)13, le specifiche dei distributori e i test empirici confermano che lo switch supporta esclusivamente l'aggregazione statica dei link (Static Link Aggregation / Trunking)1. L'aggregazione dinamica LACP con negoziazione automatica non è disponibile o risulta instabile sulle porte rame1.
* **Incongruenze della Interfaccia Grafica:** L'interfaccia richiede all'utente di premere in sequenza sia il pulsante "Apply" per applicare la modifica in memoria RAM volatile, sia il pulsante "Save" per scrivere la configurazione nella memoria flash non volatile22. Se non si eseguono entrambi i passaggi, lo switch perde tutte le impostazioni al primo riavvio elettrico22.
* **Negoziazione della Porta SFP+:** In alcune configurazioni di fabbrica, la porta SFP+ viene inizializzata con un profilo rigido a 1G o 10G22. Per consentire il corretto collegamento a schede di rete intermedie a 2.5 Gbps, è necessario forzare manualmente la negoziazione della velocità all'interno della schermata delle impostazioni delle porte22.

| Caratteristica Software | Firmware Ufficiale (OEM) | Firmware Alternativo (RTLPlayground) |
| :---- | :---- | :---- |
| **Gestione VLAN** | Supporto 802.1Q (fino a 32 VLAN)4. Gestione bloccata su VLAN 120. | Supporto completo 802.1Q. VLAN di gestione personalizzabile21. |
| **Aggregazione Link** | Solo aggregazione statica (Static LAG)1. LACP non supportato1. | Supporto avanzato per Link Aggregation Groups (LAG)23. |
| **Risparmio Energetico** | EEE globale on/off4 | EEE configurabile in modo granulare per singola porta23. |
| **Diagnostica SFP** | Assente o limitata a informazioni base | Lettura in tempo reale dei sensori DDMI (Temp, Volt, Tx/Rx Power)23. |
| **Protocolli Spanning Tree** | STP/RSTP base supportati su alcune varianti4 | STP/RSTP non ancora implementati nella build stabile23. |
| **Indirizzamento IP** | Client DHCP o IP Statico su subnet 192.168.2.0/24 \[cite: 4, 13\] | IP Statico predefinito su 192.168.10.247 o impostabile via config.txt23. |

## **Firmware Alternativo: RTLPlayground**

Per risolvere i problemi di invecchiamento precoce della memoria flash legati ad accessi in scrittura errati del firmware originale e per superare i limiti di sicurezza della VLAN 1, la comunità di sviluppatori ha creato il firmware alternativo open-source **RTLPlayground**23. Questo firmware, scritto in C per microcontrollori compatibili con i chipset Realtek RTL8372/RTL8373, sostituisce interamente il sistema operativo OEM dello switch23.

### **Funzionalità Implementate in RTLPlayground**

Il firmware alternativo sblocca un set di strumenti diagnostici e configurazioni di classe enterprise23:

* **Spostamento della VLAN di Gestione:** Consente di definire un ID VLAN personalizzato per l'interfaccia web e la console21.
* **Monitoraggio Ottico DDMI Avanzato:** Estrae i dati fisici dei ricetrasmettitori SFP+ direttamente dal bus I2C, visualizzando temperatura, tensione, corrente di polarizzazione e potenza ottica (TX/RX in dBm) tramite mouse-over nell'interfaccia grafica o da console23.
* **Gestione della MTU e Jumbo Frame:** Permette di impostare dimensioni MTU personalizzate per singola porta, con supporto a frame giganti fino a 16K byte, utile per ottimizzare il throughput verso sistemi NAS4.
* **Controllo Energetico Granulare:** L'Energy Efficient Ethernet (EEE) può essere attivato o disattivato su porte specifiche per stabilizzare i collegamenti con schede di rete che presentano incompatibilità con i protocolli di risparmio energetico dello standard 802.3az8.
* **Interfaccia Web uIP e Console Seriale:** Integra un server web basato sullo stack uIP leggero e una console interattiva accessibile tramite porta seriale UART impostata a 115200 baud, 8N123.

### **Limitazioni Importanti del Firmware Alternativo**

RTLPlayground è un progetto in continuo sviluppo e presenta alcune importanti limitazioni rispetto al software ufficiale23: non dispone del supporto per i protocolli STP/RSTP (Spanning Tree Protocol) per la prevenzione dei loop fisici nella topologia di rete (sebbene i driver di base siano inclusi nel codice sorgente) e non integra un client DHCP maturo, richiedendo la pre-configurazione di un IP statico nel file sorgente prima della compilazione23.

### **Processo di Compilazione del Firmware**

La compilazione dell'immagine binaria deve essere eseguita su un ambiente Linux Debian 12 o Debian 1323. Le distribuzioni basate su Ubuntu 24.04 non sono supportate nativamente poiché includono nei repository una versione obsoleta del compilatore SDCC (Small Device C Compiler); è richiesta tassativamente la versione **sdcc 4.5 o superiore**23.

1. **Installazione dei pacchetti richiesti:**
   Bash
   sudo apt install make gcc sdcc xxd python-is-python3 libjson-c-dev

2. **Definizione della macchina target:** Aprire il file sorgente machine.h con un editor di testo e de-commentare il profilo hardware corrispondente allo switch:
   C
   \#**define** MACHINE\_SWTGW218AS

   Questa direttiva mappa correttamente la piedinatura dei LED fisici della scheda e la disposizione logica delle porte dello switch23.
3. **Personalizzazione dei parametri di rete di avvio:** Modificare il file di configurazione config.txt per definire l'indirizzo IP statico di primo avvio, la subnet mask e il gateway predefinito dello switch, evitando così il blocco dell'interfaccia di rete dopo il primo caricamento23.
4. **Esecuzione della compilazione:** Eseguire il comando make all'interno della cartella principale del progetto per avviare il toolchain23. Il compilatore genererà il file binario finale all'interno della directory di output (ad esempio: output/rtlplayground\_v0.1.0\_MACHINE\_SWTGW218AS.bin)23.
5. **Generazione del file di aggiornamento per l'interfaccia OEM:** Se lo switch monta ancora il firmware di fabbrica e si desidera eseguire l'installazione tramite la pagina di aggiornamento web OEM, posizionarsi nella cartella installer ed eseguire nuovamente make23. Verrà generato il file specifico rtlplayground\_oem\_upgrade.bin23. Questo pacchetto incapsula l'immagine di RTLPlayground in un formato accettato dal validatore del firmware originale dello switch23.

## **Sistemi di Monitoraggio e Telemetria**

Lo switch HC-SWTGW218AS con firmware originale non supporta il protocollo SNMP, rendendo impossibile l'acquisizione automatica dei dati di traffico tramite i tradizionali sistemi di network monitoring28. Per risolvere questa lacuna senza procedere alla riscrittura del firmware del dispositivo, è possibile utilizzare la suite di monitoraggio **Switch Dashboard**24.

### **Architettura di Scraping di Switch Dashboard**

Switch Dashboard è un'applicazione web scritta in Python che monitora le metriche di funzionamento dello switch emulando richieste di login ed estraendo i dati direttamente dalle tabelle delle pagine HTTP CGI del webserver integrato24.

\+------------------+                    \+---------------------+
| Switch Dashboard | \-- HTTP GET/POST \-\> | Switch OEM / IP:    |
| (Host Docker)    |                    | 192.168.2.1         |
|                  | \<- Raw HTML Table- |                     |
|                  |                    | /port.cgi?page=stats|
\+------------------+                    \+---------------------+
        |
  Parsing & Sanitizzazione HTML (BeautifulSoup / Regex)
        |
  Tracciamento Delta dei Contatori (Previene overflow)
        |
  Esposizione REST API / Integrazione Home Assistant \[cite: 24, 29\]

L'engine di monitoraggio si basa su tre pilastri logici24:

* **Sanitizzazione preventiva dell'HTML (Bs4 Parser Fix):** Il firmware Realtek genera tabelle di diagnostica con vistosi errori di marcatura HTML, come tag \<th\> non bilanciati o chiusi in modo errato con tag \</td\>24. Lo scraper di Switch Dashboard esegue un filtraggio preliminare tramite espressioni regolari per correggere la sintassi prima di inoltrare la stringa al parser BeautifulSoup, evitando così eccezioni nel codice24.
* **Algoritmo di tracciamento dei Delta:** I contatori dei byte inviati e ricevuti dallo switch sono allocati in registri a 32 bit che si azzerano frequentemente in presenza di traffico intenso o a seguito di riavvii imprevisti24. Il backend di monitoraggio memorizza l'ultimo valore valido in un database persistente e calcola la differenza (delta) dinamica, ricostruendo l'andamento storico reale della larghezza di banda senza corruzione dei dati storici24.
* **Mappatura degli Endpoint CGI:** Lo scraper interroga ciclicamente specifici endpoint dello switch per estrarre le variabili operative del sistema24.

| Endpoint CGI dello Switch | Dati Estratti dallo Scraper | Utilizzo nella Telemetria |
| :---- | :---- | :---- |
| /info.cgi \[cite: 24\] | Versione firmware, uptime del sistema, indirizzo MAC globale24. | Stato di attività generale del dispositivo24. |
| /port.cgi?page=stats \[cite: 24\] | Contatori di pacchetti trasmessi/ricevuti, pacchetti errati, byte TX/RX24. | Calcolo della velocità di trasferimento istantanea (bps) e grafici storici24. |
| /igmp.cgi?page=dump \[cite: 24\] | Indirizzi IP multicast attivi, porte associate e appartenenza VLAN24. | Monitoraggio del traffico IPTV e flussi multimediali24. |
| /fwd.cgi?page=jumboframe \[cite: 24\] | Stato di abilitazione dei Jumbo Frame e dimensione massima in byte24. | Verifica dell'ottimizzazione del canale per storage locali24. |
| /dhcp\_snooping.cgi?page=dump \[cite: 24\] | Elenco dei server DHCP autorizzati e porte configurate come "trusted"24. | Telemetria di sicurezza contro server DHCP malevoli o errati24. |
| /mac.cgi?page=fwd\_tbl \[cite: 24\] | Tabella di inoltro dei MAC Address (FDB) associati alle rispettive porte logiche24. | Generazione automatica della mappa topologica dei client24. |
| /config\_back.cgi?cmd=conf\_backup \[cite: 24\] | Archivio binario di configurazione dello switch24. | Backup programmato e ripristino in caso di guasto hardware24. |

### **Integrazione di RTLPlayground e API REST dello Switch Dashboard**

L'applicazione Switch Dashboard include un profilo dichiarativo specifico denominato RTLPlayground.yaml24. Questo modulo è configurato per mappare gli indirizzi ip tipici delle reti locali gestite da RTLPlayground (con indirizzo di default 192.168.10.247) e traduce gli endpoint del firmware open-source (come /ports e /stats) nel formato grafico unificato della dashboard24.
I dati raccolti vengono esposti a sistemi esterni tramite una serie di API REST accessibili localmente24:

* GET /api/switches – Restituisce lo stato live di tutti gli switch monitorati e delle relative porte fisiche24.
* GET /api/switches/\<ip\>/transceiver – Fornisce i parametri fisici in formato JSON del modulo SFP+ estratti tramite telemetria DDMI24.
* GET /api/speeds – Fornisce il throughput istantaneo calcolato in bit al secondo (bps)24.
* POST /api/switches/\<ip\>/reboot – Invia una chiamata CGI sicura per forzare il riavvio hardware del dispositivo24.

### **Integrazione con Home Assistant tramite MQTT**

Le API esposte e le variabili catturate dallo Switch Dashboard possono essere collegate a un sistema di automazione domestica basato su Home Assistant29. Il metodo più stabile prevede l'uso del protocollo MQTT, configurando lo switch come sensore nel file configuration.yaml dell'istanza domotica29:

YAML
sensor:
  \- platform: mqtt
    name: "Stato Switch RJ45 Porta 1"
    state\_topic: "home/switch\_link/port1/state"
    value\_template: "{{ value\_json.link\_status }}"

switch:
  \- platform: mqtt
    name: "Controllo Alimentazione Switch"
    state\_topic: "home/switch\_power/get"
    command\_topic: "home/switch\_power/set"
    payload\_on: "ON"
    payload\_off: "OFF"
    qos: 1

Questa integrazione consente di monitorare la stabilità fisica della rete locale direttamente dalla dashboard di Home Assistant29. Ad esempio, è possibile impostare automazioni che modificano la navigazione dei tablet a parete o ripristinano l'alimentazione elettrica di una determinata presa smart qualora si rilevi una disconnessione prolungata dell'uplink a 10G SFP+ dello switch16.

#### **Bibliografia**

1. SODOLA 9 Port 2.5G Smart Web Ethernet Switch,1 10G SFP Slot&8 x 2.5G Base-T Ports,Static Aggregation, QoS/VLAN/IGMP Supported, Metal Fanless Managed Multi-Gigabit Switch, [https://www.sodola-network.com/products/sodola-9-port-2-5g-smart-web-ethernet-switch-1-10g-sfp-slot-8-x-2-5g-base-t-ports-static-aggregation-qos-vlan-igmp-supported-metal-fanless-managed-multi-gigabit-switch-mtwg](https://www.sodola-network.com/products/sodola-9-port-2-5g-smart-web-ethernet-switch-1-10g-sfp-slot-8-x-2-5g-base-t-ports-static-aggregation-qos-vlan-igmp-supported-metal-fanless-managed-multi-gigabit-switch-mtwg)
2. Horaco SWTGW218AS \- device.report, [https://device.report/horaco/swtgw218as](https://device.report/horaco/swtgw218as)
3. RTLPlayground/doc/supported\_devices.md at main \- GitHub, [https://github.com/logicog/RTLPlayground/blob/main/doc/supported\_devices.md](https://github.com/logicog/RTLPlayground/blob/main/doc/supported_devices.md)
4. OPTFOCUS Web Managed 2.5G Network Switch User Manual, [https://eu.manuals.plus/ae/1005006991093051](https://eu.manuals.plus/ae/1005006991093051)
5. Switch'nstor 9 Gen2 Released | ASUSTOR Inc., [https://www.asustor.com/news/news\_detail?id=33001](https://www.asustor.com/news/news_detail?id=33001)
6. Realtek to Announce Full Range of Communications Network, Multimedia, and Consumer Electronics Solutions at 2022 CES, [https://www.realtek.com/Article/NewsDetail?id=4151\&app\_id=18](https://www.realtek.com/Article/NewsDetail?id=4151&app_id=18)
7. Hardware & Packaging \- ASUSTOR NAS, [https://www.asustor.com/en-gb/product/ASW209X\_belonging?tab=3](https://www.asustor.com/en-gb/product/ASW209X_belonging?tab=3)
8. 8-Port 2.5Gb Web Managed Switch with 10G SFP+, Aluminum Alloy Cooling & Magnetic Mounting \- LACP/QoS/VLAN/IGMP Managed Multi-Gigabit Switch for Homelab \- Sodola Networks, [https://www.sodola-network.com/products/8-port-2-5gb-web-managed-switch-with-10g-sfp-aluminum-alloy-cooling-magnetic-mounting-lacp-qos-vlan-igmp-managed-multi-gigabit-switch-for-homelab](https://www.sodola-network.com/products/8-port-2-5gb-web-managed-switch-with-10g-sfp-aluminum-alloy-cooling-magnetic-mounting-lacp-qos-vlan-igmp-managed-multi-gigabit-switch-for-homelab)
9. Horaco 2.5GbE Managed Switch (8 x 2.5GbE \+ 1 10Gb SFP+) | ServeTheHome Forums, [https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-28](https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-28)
10. 24 Port 2.5Gb Web Managed Switch,24 x 2.5G Port,2 x 10G SFP+,160Gbps Bandwidth Smart Managed Network Switch with LACP/VLAN/QoS/DHCP Client,Metal Housing,Ethernet Switch,1U Rack Mounted \- Newegg, [https://www.newegg.com/p/0XP-04WP-00CU0](https://www.newegg.com/p/0XP-04WP-00CU0)
11. The Sodola Multi-Gigabit Managed Switches \- Tao of Mac, [https://taoofmac.com/space/reviews/2024/08/11/1230](https://taoofmac.com/space/reviews/2024/08/11/1230)
12. The Sodola SL902-SWTGW218AS \- Tao of Mac, [https://taoofmac.com/space/reviews/2025/08/03/1900](https://taoofmac.com/space/reviews/2025/08/03/1900)
13. SODOLA SL902-SWTGW218AS Smart Web Switch User Manual \- device.report, [https://device.report/manual/17172261](https://device.report/manual/17172261)
14. Budget 8-port 2.5G switch with fan? : r/HomeNetworking \- Reddit, [https://www.reddit.com/r/HomeNetworking/comments/1dvqnd0/budget\_8port\_25g\_switch\_with\_fan/](https://www.reddit.com/r/HomeNetworking/comments/1dvqnd0/budget_8port_25g_switch_with_fan/)
15. ISO small CHEAP 10GbE switch : r/mikrotik \- Reddit, [https://www.reddit.com/r/mikrotik/comments/1bzyh1b/iso\_small\_cheap\_10gbe\_switch/](https://www.reddit.com/r/mikrotik/comments/1bzyh1b/iso_small_cheap_10gbe_switch/)
16. Upgraded network to 10GbE+2.5GbE, i3perf shows correct speeds, file transfer abysmally slow (2-60MB/s) : r/HomeNetworking \- Reddit, [https://www.reddit.com/r/HomeNetworking/comments/1rm1iy4/upgraded\_network\_to\_10gbe25gbe\_i3perf\_shows/](https://www.reddit.com/r/HomeNetworking/comments/1rm1iy4/upgraded_network_to_10gbe25gbe_i3perf_shows/)
17. ASUSTOR Introduces Switch'nstor 9 Gen2 10GbE \+ 2.5GbE Unmanaged Switch, [https://www.techpowerup.com/326202/asustor-introduces-switchnstor-9-gen2-10gbe-2-5gbe-unmanaged-switch](https://www.techpowerup.com/326202/asustor-introduces-switchnstor-9-gen2-10gbe-2-5gbe-unmanaged-switch)
18. Horaco 2.5GbE Managed Switch (8 x 2.5GbE \+ 1 10Gb SFP+) | ServeTheHome Forums, [https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-31](https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-31)
19. Horaco 2.5GbE Managed Switch (8 x 2.5GbE \+ 1 10Gb SFP+) | ServeTheHome Forums, [https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-27](https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-27)
20. Horaco 2.5GbE Managed Switch (8 x 2.5GbE \+ 1 10Gb SFP+) | ServeTheHome Forums, [https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-3](https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-3)
21. Horaco 2.5GbE Managed Switch (8 x 2.5GbE \+ 1 10Gb SFP+) | ServeTheHome Forums, [https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-40](https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-40)
22. Horaco managed gigabit switches I found them great : r/homelab \- Reddit, [https://www.reddit.com/r/homelab/comments/1tkjjv4/horaco\_managed\_gigabit\_switches\_i\_found\_them\_great/?tl=en](https://www.reddit.com/r/homelab/comments/1tkjjv4/horaco_managed_gigabit_switches_i_found_them_great/?tl=en)
23. logicog/RTLPlayground: A Playground for Firmware development for RTL8372/RTL8373 based 2.5GBit Switches \- GitHub, [https://github.com/logicog/RTLPlayground](https://github.com/logicog/RTLPlayground)
24. A premium, real-time glassmorphic monitoring dashboard for HORACO HC-SWTGW218AS and OEM managed switches. Uses lightweight HTTP CGI scraping (no SNMP needed) and features rolling bandwidth charts, on-demand SFP+ transceiver optical DDMI diagnostics, and searchable MAC address tables. · GitHub, [https://github.com/byte4geek/switch-dashboard](https://github.com/byte4geek/switch-dashboard)
25. Horaco 2.5GbE Managed Switch (8 x 2.5GbE \+ 1 10Gb SFP+) | ServeTheHome Forums, [https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-39](https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-39)
26. RTLPlayground/rtl837x\_stp.c at main \- GitHub, [https://github.com/logicog/RTLPlayground/blob/main/rtl837x\_stp.c](https://github.com/logicog/RTLPlayground/blob/main/rtl837x_stp.c)
27. Horaco 2.5GbE Managed Switch (8 x 2.5GbE \+ 1 10Gb SFP+) | ServeTheHome Forums, [https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-38](https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-38)
28. Horaco 2.5GbE Managed Switch (8 x 2.5GbE \+ 1 10Gb SFP+) | ServeTheHome Forums, [https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-29](https://forums.servethehome.com/index.php?threads/horaco-2-5gbe-managed-switch-8-x-2-5gbe-1-10gb-sfp.41571/page-29)
29. How to create a simple MQTT switch in Home Assistant \- Roelof Jan Elsinga, [https://roelofjanelsinga.com/articles/how-to-create-switch-dashboard-home-assistant/](https://roelofjanelsinga.com/articles/how-to-create-switch-dashboard-home-assistant/)
30. Is this automation possible \- Configuration \- Home Assistant Community, [https://community.home-assistant.io/t/is-this-automation-possible/956723](https://community.home-assistant.io/t/is-this-automation-possible/956723)
31. Action: Dashboard Select \> Target Companion App Device \- Home Assistant Community, [https://community.home-assistant.io/t/action-dashboard-select-target-companion-app-device/450574](https://community.home-assistant.io/t/action-dashboard-select-target-companion-app-device/450574)
32. Switch dashboard when doorbell rings doesn't work \- Home Assistant Community, [https://community.home-assistant.io/t/switch-dashboard-when-doorbell-rings-doesnt-work/845585](https://community.home-assistant.io/t/switch-dashboard-when-doorbell-rings-doesnt-work/845585)
