---
title: "OPNsense (Firewall & Gateway)"
last_updated: "2026-05-03"
confidence: "High"
tags:
  - "#network"
  - "#core"
  - "#opnsense"
provenance:
  - "homelab_notebooklm.md"
  - "incidents/2026-05-03-dns-split-horizon-conflict.md"
---

# OPNsense (Gateway & Security)

Il nodo OPNsense è il cuore della sicurezza e della risoluzione DNS della rete locale.

## 1. Dettagli di Rete
- **IP Gestione (VLAN 20)**: `10.10.20.254`
- **Hostname Accesso Diretto**: `https://firewall-direct.pindaroli.org` (o `10.10.20.1` via Switch).
- **Ruolo DNS**: Autorevole per il dominio interno (`pindaroli.org`). Fornisce risoluzione Split-Horizon.

## 2. Configurazione DNS (Unbound)
Il servizio Unbound gestisce la risoluzione interna per evitare l'uso di DNS pubblici per i record locali.
- **Local Zone Type**: Impostato su `transparent` per permettere la coesistenza di record locali e fallback pubblici.
- **Access Lists (ACL)**: 
  - Affinché i pod Kubernetes possano risolvere i nomi, la subnet `10.244.0.0/16` **DEVE** essere esplicitamente inserita nelle ACL con policy `Allow`.
  - Tensioni Note: In passato l'assenza di questa ACL ha causato il blocco delle richieste provenienti dal [[Talos_Cluster]] (Vedi [[2026-05-03-dns-split-horizon-conflict]]).

## 3. Configurazione DHCP (Kea)
Kea DHCP assegna gli indirizzi dinamici ai client (inclusa la VLAN 20).
- **Option 15 (Domain Name)**: Deve essere impostato su `pindaroli.org` per istruire i client a usare i nomi brevi e dare priorità al resolver locale.

## 4. Protezione Anti-Rebind
Per accedere all'interfaccia web di OPNsense usando un dominio personalizzato (es. `firewall-direct.pindaroli.org`), tale dominio deve essere registrato in `System -> Settings -> Administration -> Alternate Hostnames`.

## Relazioni Architetturali
- Fornisce DNS a: [[Talos_Cluster]]
- Bilancia traffico verso: [[Traefik]]
- Subisce potenziali problemi di routing asimmetrico se non configurato in accordo con lo Switch L3.
