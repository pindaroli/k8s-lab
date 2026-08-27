---
title: "OPNsense (Firewall & Gateway)"
last_updated: "2026-08-22"
confidence: "High"
tags:
  - "#network"
  - "#core"
  - "#opnsense"
provenance:
  - "homelab_notebooklm.md"
  - "incidents/2026-05-03-dns-split-horizon-conflict.md"
  - "incidents/2026-05-16-dnsbl-automation-payload-mismatch.md"
  - "incidents/2026-08-22-vlan20-asymmetric-routing-l3-alignment.md"
---

# OPNsense (Gateway & Security)

Il nodo OPNsense è il cuore della sicurezza e della risoluzione DNS della rete locale.

## 1. Dettagli di Rete
- **Interfaccia Transit IP**: `192.168.2.254` (usata come server DNS principale per il cluster e lo switch).
- **Interfaccia OOB IP**: `192.168.100.1` (gestione diretta fuori banda).
- **Hostname Accesso Diretto**: `https://firewall-direct.pindaroli.org` (reindirizzato su IP OOB via Traefik).
- **Ruolo DNS**: Autorevole per il dominio interno (`pindaroli.org`). Fornisce risoluzione Split-Horizon su `192.168.2.254`.
- **Nessun IP su VLAN 10/20 (Symmetric Routing L3)**: Le interfacce gateway logiche di OPNsense su VLAN 10 (`igc1_vlan10` / `opt1`) e VLAN 20 (`igc1_vlan20` / `opt2`) sono configurate con `IPv4 Configuration Type: None`. Il routing verso queste subnet è delegato allo Switch Core Extreme L3 (`192.168.2.1`) tramite rotte statiche dedicate (`10.10.10.0/24` e `10.10.20.0/24 -> 192.168.2.1`) su interfaccia `TRANSIT` (`igc1`).

## 2. Configurazione DNS (Unbound)
Il servizio Unbound gestisce la risoluzione interna per evitare l'uso di DNS pubblici per i record locali.
- **Local Zone Type**: Impostato su `transparent` per permettere la coesistenza di record locali e fallback pubblici.
- **Access Lists (ACL)**:
  - Affinché i pod Kubernetes e i client possano risolvere i nomi, le subnet `10.244.0.0/16`, `10.10.10.0/24`, `10.10.20.0/24` e `192.168.100.0/24` sono esplicitamente inserite nelle ACL con policy `Allow` (`VLANs_Allow`).
  - Tensioni Note: In passato l'assenza di questa ACL ha causato il blocco delle richieste provenienti dal [[Talos_Cluster]] (Vedi [[2026-05-03-dns-split-horizon-conflict]]).

## 3. Configurazione DHCP (Kea con DHCP Relay)
Kea DHCP gestisce centralmente i pool di indirizzi dinamici e le prenotazioni statiche.
- **VLAN 20 Client**: Riceve le richieste DHCP inoltrate dallo Switch Extreme tramite **Bootprelay / DHCP Relay** su `TRANSIT` (`192.168.2.254:67`).
- **Opzioni Distribuite per VLAN 20**:
  - **Option 3 (Routers / Gateway)**: `10.10.20.1` (Switch Extreme L3 SVI).
  - **Option 6 (DNS Servers)**: `192.168.2.254` (Unbound su OPNsense).
  - **Option 15 (Domain Name)**: `pindaroli.org`.

## 4. Filtraggio Pubblicitario (DNSBL / AdBlock)
OPNsense usa il modulo nativo di Unbound per il blocco dei domini traccianti.
- **Troubleshooting Base**: Le liste pubbliche spesso mancano i domini *root* (es. `doubleclick.net`). In caso di mancato blocco, verificare sempre le **Wildcard Domains**. (Vedi [[2026-05-03-dnsbl-filtering-failure]]).
- **Automazione & SSoT**: La lista dei domini da bloccare in wildcard (telemetria, tracking aggressivo) è centralizzata in `rete.json` sotto la chiave `opnsense.outbound.blocked-domain`.
- **Applicazione Modifiche**: Le modifiche si applicano eseguendo lo script Ansible dedicato:
  `ansible-playbook ansible/playbooks/opnsense_adblock_automation.yml`
- **Importante**: Per attivare le nuove wildcard DNS, lo script esegue un **`service/restart`** di Unbound (Vedi [[2026-05-16-dnsbl-automation-payload-mismatch]]).

## 5. Protezione Anti-Rebind
Per accedere all'interfaccia web di OPNsense usando un dominio personalizzato (es. `firewall-direct.pindaroli.org`), tale dominio deve essere registrato in `System -> Settings -> Administration -> Alternate Hostnames`.

## Relazioni Architetturali
- Fornisce DNS a: [[Talos_Cluster]], Dispositivi Client VLAN 20
- Bilancia traffico verso: [[Traefik]]
- Instradamento simmetrico con: [[Ansible_Extreme_EXOS]] su rete di TRANSIT.
