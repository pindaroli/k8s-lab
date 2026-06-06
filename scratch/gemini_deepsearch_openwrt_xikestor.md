# Deep Research: OpenWrt su XikeStor SKS8300-8X (Realtek RTL9303)

## Contesto

Possiedo uno switch L3 managed **XikeStor SKS8300-8X** (venduto anche come **ONTi ONT-S508cl-8S**), basato sul SoC **Realtek RTL9303** con 8 porte 10G SFP+. Attualmente esegue il firmware stock proprietario.

Lo switch è il **core della mia rete homelab** e gestisce:
- Inter-VLAN routing L3 tra VLAN 10 (Server, `10.10.10.0/24`) e VLAN 20 (Client/K8s, `10.10.20.0/24`)
- Rete di transito verso OPNsense (`192.168.2.0/24`)
- Uplink a 2 switch 2.5G satellite (GoodTop e LIAGUO) via DAC/SFP+
- Connessioni dirette a 3 nodi Proxmox (PVE1, PVE2, PVE3) tramite DAC 10G
- VLAN tagging 802.1Q su tutte le porte (trunk e access)

Il firmware stock **non offre** REST API, SNMP, né SSH. L'unica gestione è via Web UI HTTP e una porta console seriale. Vorrei valutare la migrazione a **OpenWrt** per ottenere:
- Accesso SSH e gestione programmatica (Ansible, script)
- SNMP per monitoraggio (Prometheus/Grafana)
- UCI per configurazione dichiarativa
- Eventualmente LLDP, NetFlow/sFlow, ACL avanzate

## Domande di Ricerca

### 1. Compatibilità e Supporto Hardware
- Lo **XikeStor SKS8300-8X** è ufficialmente supportato da OpenWrt? Qual è lo stato del supporto nella tabella hardware (ToH)?
- Qual è il livello di maturità del driver **Realtek RTL9303** in OpenWrt? Tutte le 8 porte SFP+ funzionano? A quale velocità (1G/10G)?
- Ci sono limitazioni note? (es. hardware offloading, jumbo frame, numero massimo di VLAN, routing L3, LACP)
- Lo switch ha **512 MiB DDR3 RAM e 32 MiB SPI-NOR Flash**: è sufficiente per OpenWrt con pacchetti aggiuntivi (SNMP, LLDP, collectd)?

### 2. Procedura di Flash
- Qual è la procedura esatta per flashare OpenWrt su questo specifico modello? (TFTP via U-Boot? Flash via seriale? Web UI upgrade?)
- È necessario aprire lo switch e collegare un cavo seriale TTL alla console?
- Qual è il **rischio di brick**? Esiste una procedura di recovery (failsafe mode, TFTP boot)?
- È possibile fare **dual-boot** o mantenere il firmware stock come fallback?
- Quali immagini firmware scaricare? (sysupgrade vs factory? initramfs per test?)

### 3. Configurazione Post-Flash
- Come si configurano le **VLAN 802.1Q** in OpenWrt/UCI per replicare esattamente la configurazione attuale (VLAN 10, VLAN 20, Transit 192.168.2.0/24)?
- Come si configura il **routing L3 inter-VLAN** in OpenWrt? È equivalente al routing hardware del firmware stock?
- Quali pacchetti installare per: SSH (default), SNMP (`snmpd`), LLDP (`lldpd`), NetFlow/sFlow, monitoring?
- Come si integra con **Ansible** per la gestione dichiarativa? Esistono moduli Ansible per UCI?

### 4. Performance e Rischi
- Il passaggio a OpenWrt comporta **perdita di performance** nel forwarding L3? (software routing vs hardware ASIC offloading)
- Quali sono i **rischi operativi** per un ambiente di produzione homelab? (downtime cluster Kubernetes, perdita di connettività VLAN, impossibilità di rollback)
- Quali **test** eseguire prima di mettere in produzione? (throughput iperf3, latenza inter-VLAN, stabilità sotto carico)

### 5. Alternative
- Se OpenWrt non è maturo abbastanza, ci sono **firmware alternativi** per RTL9303? (es. progetti community specifici)
- Sarebbe più pragmatico fare **web scraping della WebUI stock** per il monitoraggio base, senza rischiare il flash?
- Un **proxy SNMP esterno** (es. un container che interroga la WebUI e espone metriche SNMP/Prometheus) sarebbe un compromesso accettabile?

## Output Atteso
Fornisci un report strutturato con:
1. **Verdetto**: Raccomandazione chiara (Flash / Non flashare / Attendere)
2. **Procedura step-by-step** se il flash è consigliato
3. **Configurazione UCI** equivalente alla mia configurazione VLAN attuale
4. **Piano di rollback** in caso di problemi
5. **Fonti**: Link a wiki OpenWrt, thread forum, repository GitHub rilevanti
