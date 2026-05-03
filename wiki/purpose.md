---
title: "Progetto GEMINI: Purpose & Core Principles"
last_updated: "2026-05-03"
confidence: "High"
tags:
  - "#core"
  - "#philosophy"
---

# La Bussola del Progetto GEMINI (Homelab)

Questo documento definisce gli obiettivi architetturali immutabili del cluster Kubernetes e dell'infrastruttura Homelab. L'Agente IA deve consultare questo file prima di proporre modifiche strutturali.

## 1. Sicurezza e Accesso Esterno (The Premium Shield)
- **Regola Zero**: TUTTI i servizi esposti su internet (`<servizio>.pindaroli.org`) tramite Cloudflare Tunnel **DEVONO** essere protetti da OAuth2 (Google Login). Nessuna eccezione.
- **Eccezione Interna**: I servizi esposti sulla rete LAN o VPN (`<servizio>-internal.pindaroli.org`) **NON** devono richiedere OAuth2, in quanto la rete LAN è considerata "Trusted".

## 2. Naming Convention e DNS (Split-Horizon)
- Ogni servizio ha tre endpoint mnemonici:
  1. `<service>.pindaroli.org` (Premium External, OAuth, Cloudflare)
  2. `<service>-internal.pindaroli.org` (Premium Internal, Trusted, OPNsense Unbound)
  3. `<service>-direct.pindaroli.org` (Direct Node/IP Bypass)
- **Golden Rule DNS**: La risoluzione DNS interna è gestita da [[OPNsense]]. L'uso di record "Black Hole" (es. 0.0.0.0 su Cloudflare) è severamente vietato in quanto causa distruzione del contesto e caching asimmetrico sui client (Vedi [[2026-05-03-dns-split-horizon-conflict]]).

## 3. Gestione dello Storage
- Il repository centrale dei dati (`arrdata`, `k8s-arr`) vive su [[TrueNAS]] (`10.10.10.50`).
- Si predilige il protocollo **NFS** per i mount nei container e sui nodi fisici.

## 4. Filosofia Operativa (Symmetrical Routing)
- Il traffico inter-VLAN interno (es. VLAN 20 verso VLAN 10) deve essere gestito preferibilmente dallo Switch L3 per mantenere la simmetria del routing (Symmetrical Routing).
- I fallback verso OPNsense devono essere mappati attentamente nelle Access List e regole NAT.

## 5. Automation First
- Le modifiche all'infrastruttura DNS e DHCP devono essere sincronizzate tramite Ansible.
- Le configurazioni fisiche dei nodi Talos vivono nei file YAML nella cartella `talos-config/`. Le patch temporanee sono sconsigliate; aggiornare sempre il file originale e fare `apply-config`.
