---
title: "DNSBL Filtering Failure (AdBlock Bypass)"
date: "2026-05-03"
status: "Resolved"
severity: "Medium"
tags:
  - "#dns"
  - "#opnsense"
  - "#security"
entities:
  - "[[OPNsense]]"
---

# Incident Report: DNSBL Filtering Failure

## Descrizione
Il filtro per la pubblicità e il tracciamento (DNSBL/AdBlock) su OPNsense sembrava non funzionare per alcuni domini principali (es. `doubleclick.net`), permettendo la risoluzione degli IP reali nonostante le liste di blocco fossero attive.

## Diagnosi
Il problema è stato identificato come una combinazione di due fattori tecnici:
1.  **Mancanza di Wildcard**: Le liste esterne (come OISD) spesso includono sottodomini specifici ma non i domini "root". Senza la configurazione esplicita delle "Wildcard Domains", le query per i domini base (es. `doubleclick.net` o `www.doubleclick.net`) passavano il filtro.
2.  **Cache Stale di Unbound**: Anche dopo aver attivato le wildcard, Unbound continuava a rispondere con gli IP reali salvati nella cache interna (TTL > 0), ignorando le nuove regole di blocco.

## Azioni Correttive
1.  **Wildcard Configuration**: Aggiunti i domini root principali (`doubleclick.net`, `google-analytics.com`, ecc.) nella colonna "Wildcard Domains" delle impostazioni DNSBL.
2.  **Cache Flush**: Eseguito il flush della cache di Unbound e il riavvio del servizio per forzare il ricaricamento del database DNSBL.
3.  **Automation (SSoT)**: Sviluppato uno script Python (`opnsense_dnsbl_config.py`) e un playbook Ansible per automatizzare l'inserimento delle wildcard. La lista dei domini da bloccare è stata centralizzata in `rete.json` alla voce `opnsense.outbound.blocked-domain` (Single Source of Truth), e lo script la legge dinamicamente.
4.  **Manual Sync**: Identificata la necessità di un trigger manuale "Download & Update" dalla UI di OPNsense per forzare la rigenerazione fisica dei file di blocco, poiché il comando API `reconfigure` potrebbe non essere sufficiente per il download delle liste esterne.

## Verifica Finale
Il comando `dig @10.10.20.254 doubleclick.net` ora restituisce correttamente `0.0.0.0` con flag Authoritative (`aa`).

## Lezioni Apprese
*   In OPNsense, il tester di Unbound esegue un "Exact Match". Se il tester dà `Pass`, verificare sempre i sottodomini.
*   Le modifiche alle Blocklist richiedono sempre un flush della cache per essere visibili immediatamente ai client.
*   **API Limitation**: L'API di OPNsense (`/api/unbound/settings/set`) aggiorna il `config.xml` ma non sempre scatena il download asincrono delle liste. Il tasto "Download & Update" nella UI rimane il metodo più affidabile per la sincronizzazione finale.
