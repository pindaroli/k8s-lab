---
title: "INC-2026-08-22: VLAN 20 Asymmetric Routing and L3 Core Switch Alignment"
type: incident
status: archived
certified_for_ai: false
date: 2026-08-22
severity: P2
resolved: true
resolved_at: 2026-08-22T19:40:00Z
tags:
  - "#incident"
  - "#network"
  - "#opnsense"
  - "#core"
---

# Incident: VLAN 20 Asymmetric Routing and L3 Core Switch Alignment

**Data**: 2026-08-22  
**Stato**: RISOLTO (Allineamento completato: Routing simmetrico L3 su Switch Extreme + DHCP Relay verso Kea su OPNsense)  
**Severità**: P2 (I client della VLAN 20 perdevano la connettività Internet al rinnovo del lease o all'apertura di nuove connessioni TCP)  

---

## 🔍 Diagnosi e Root Cause Analysis (RCA)

Durante la serata del 22 Agosto 2026, è stata segnalata la perdita progressiva della connettività Internet per i dispositivi attestati sulla **VLAN 20 (`LAN_CLIENT`, 10.10.20.0/24)**.

L'ispezione dei log del firewall *pf*, della tabella degli stati e delle rotte su **[[OPNsense]]** e sullo **Switch Core Extreme Networks (X620-10X)** ha evidenziato due cause concomitanti:

1. **Routing Asimmetrico e Violazione di Stato (*pf State Violation*):**
   * Lo Switch Extreme manteneva l'interfaccia SVI `10.10.20.1/24` e instradava il traffico verso Internet inoltrandolo sulla rete di **TRANSIT** (`192.168.2.1` $\rightarrow$ `192.168.2.254` su `igc1`).
   * Contemporaneamente, OPNsense aveva la sotto-interfaccia `igc1_vlan20` (`opt2`) configurata con IP `10.10.20.254/24`, creando una rotta locale diretta `10.10.20.0/24 -> link#10`.
   * Quando OPNsense riceveva le risposte da Internet, le reinviava direttamente su `igc1_vlan20` anziché sullo switch. I successivi pacchetti ACK del client rientravano su `igc1` (TRANSIT), provocando lo scarto del pacchetto da parte del firewall *pf*:
     ```text
     BLOCK igc1 tcp 10.10.20.213:55686 -> 172.217.118.4:443 | RID: 02f4bab031b57d1e30553ce08e0ec131 (Default deny / state violation rule)
     ```
2. **Ciclo di Rinnovo DHCP (Kea DHCP):**
   * Al rinnovo periodico del lease DHCP (Kea `valid_lifetime: 4000s`), i dispositivi acquisivano come Default Gateway `10.10.20.254` (OPNsense) anziché `10.10.20.1`. Inviando il traffico direttamente su `LAN_CLIENT` (`opt2`), i pacchetti venivano bloccati a causa della mancanza di una regola `Allow to Any` su tale interfaccia.

---

## 🛠️ Azioni Correttive e Risoluzione (Architettura Routed L3)

Per risolvere definitivamente il problema e uniformare la VLAN 20 al modello architetturale già impiegato con successo per la VLAN 10 (Server), è stata implementata l'**Architettura Routed L3 con DHCP Relay**:

```mermaid
flowchart LR
    Client["Client VLAN 20 (10.10.20.x)"] <== L2 Tag 20 ==> Switch["Switch Extreme L3 (10.10.20.1)"]
    Switch <== Link TRANSIT (192.168.2.0/24) ==> OPN["OPNsense (192.168.2.254)"]
    OPN <== NAT WAN ==> Internet((Internet))
    Client -.->|DHCP Discover (Relay)| Switch
    Switch -.->|Bootprelay Unicast| OPN
```

### 1. Configurazione Switch Extreme (EXOS)
* **DHCP Relay (Bootprelay):** Abilitato `bootprelay` globale per il virtual router `VR-Default` e specificamente per la VLAN `client` (VID 20) verso il server DHCP su OPNsense:
  ```text
  enable bootprelay ipv4
  enable bootprelay ipv4 vlan client
  configure bootprelay add 192.168.2.254
  ```
* **IP Forwarding & SVI:** Verificata la presenza dell'IP `10.10.20.1/24` con flag `f` (IP Forwarding Enabled).
* **Persistenza:** Salvata la configurazione in `primary.cfg`.

### 2. Configurazione OPNsense
* **Rimozione IP da `LAN_CLIENT`:** Impostato `IPv4 Configuration Type: None` sull'interfaccia `igc1_vlan20` (`opt2`), disattivando la rotta locale diretta.
* **Rotta Statica:** Creata la rotta statica:
  * **Rete:** `10.10.20.0/24`
  * **Gateway:** `SWITCH_L3_GW` (`192.168.2.1` su `TRANSIT` / `igc1`).
* **Kea DHCP Subnet:** Definita la subnet `10.10.20.0/24` (pool `10.10.20.201-10.10.20.253`) distribuendo:
  * **Option 3 (Routers):** `10.10.20.1` (Switch Extreme L3)
  * **Option 6 (DNS Servers):** `192.168.2.254` (Unbound su OPNsense)
* **Riavvio Servizio:** Riavviato il servizio `kea` su OPNsense.

### 3. Allineamento Repository & Infrastructure as Code
* **`rete.json`**:
  * Aggiornata la definizione della VLAN 20 con `mode: "relay"`, `relay_agent: "10.10.20.1"` e `dhcp_server: "192.168.2.254"`.
  * Aggiornata l'interfaccia logica `gw-vlan20` di OPNsense con `ip: "None"` e `dhcp: "relay"`.

---

## 🧪 Risultati dei Test e Verifiche

1. **Routing su OPNsense:**
   * `interfaceGetRoutes` conferma la presenza della rotta:
     `10.10.20.0/24 -> 192.168.2.1 via igc1 (TRANSIT)` con flag `UGS`.
2. **Connettività dello Switch L3:**
   * Ping da Switch verso `1.1.1.1`: 4/4 pacchetti ricevuti (0% packet loss, avg 31ms).
   * Ping da Switch verso Mac Studio (`10.10.20.100`): 4/4 pacchetti ricevuti (0% packet loss, avg 3ms).
3. **Flussi di Traffico Client (Stati *pf* attivi):**
   * Pixel 9 (`10.10.20.217`), iPad (`10.10.20.215`), Google Nest (`10.10.20.203`) e Smart Devices (`10.10.20.206`) scambiano regolarmente traffico DNS e HTTPS su WAN con instradamento 100% simmetrico attraverso il link TRANSIT.

---

## 🔗 Riferimenti
* [[OPNsense]]
* [[Network_Registry]]
* [[Ansible_Extreme_EXOS]]
* [[Talos_Cluster]]
* [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json)
