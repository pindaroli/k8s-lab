---
title: "Xray Proxy"
last_updated: "2026-05-03"
confidence: "Medium"
tags:
  - "#network"
  - "#proxy"
  - "#xray"
provenance:
  - "xray/README.md"
---

# Xray Proxy

Xray è configurato come servizio di tunneling per instradare traffico specifico (es. verso OCI - Oracle Cloud Infrastructure).

## 1. Sicurezza e Segreti
Le credenziali sensibili (UUID, Private Key, Public Key, ShortId) sono salvate localmente nel file **git-ignored** `xray/xray_secrets.yml`.
Nel cluster, questi dati vengono iniettati tramite il Kubernetes Secret `xray-secrets` nel namespace `xray`.

## 2. Stato
*Deprecated / Standby*: In passato, i client torrent utilizzavano Xray come sidecar VPN. Attualmente, per massimizzare le performance e la connettività degli indexer, la stack [[Servarr]] instrada il traffico direttamente senza proxy.

## Relazioni
- Namespace: `xray`
- Secret correlato: `xray-secrets`
