---
title: "Workflow: TLS Certificate Management"
last_updated: "2026-05-03"
confidence: "High"
tags:
  - "#security"
  - "#tls"
  - "#cert-manager"
provenance:
  - "lesencript.md"
---

# Gestione Certificati SSL/TLS

Il cluster utilizza `cert-manager` per emettere e rinnovare automaticamente i certificati Let's Encrypt tramite la DNS-01 Challenge di Cloudflare.

## 1. Architettura
- **ClusterIssuer**: `cloudflare-issuer`. Utilizza un token API di Cloudflare (salvato come Secret K8s).
- **Wildcard**: Generiamo un unico certificato per `*.pindaroli.org`.
- **Certificati Interni**: Anche i servizi `-internal` usano certificati validi emessi tramite la stessa challenge, garantendo il lucchetto verde anche in LAN.

## 2. Rinnovo Automatico
Cert-manager controlla la scadenza ogni ora. Se mancano meno di 30 giorni, avvia il rinnovo.
- **Verifica Stato**: `kubectl get certificate -A`
- **Troubleshooting**: Se un certificato è bloccato in `False`, controllare i log di cert-manager: `kubectl logs -n cert-manager -l app=cert-manager`.

## 3. DNS Challenge
Perché funzioni, cert-manager deve poter creare record TXT temporanei su Cloudflare. 
- **Problema Storico**: In passato, la risoluzione DNS locale interferiva con la verifica della challenge.
- **Soluzione**: Con il nuovo setup DNS (Vedi [[OPNsense]]), il cluster risolve correttamente i record esterni durante la fase di validazione.

## Relazioni
- Gestito da: [[Talos_Cluster]] (cert-manager addon/helm).
- Utilizzato da: [[Traefik]] per terminare le connessioni HTTPS.
- Dipende da: Cloudflare API.
