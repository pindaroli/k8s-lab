---
title: "OAuth2 Proxy (Security Shield)"
last_updated: "2026-05-03"
confidence: "High"
tags:
  - "#security"
  - "#auth"
  - "#oauth2"
provenance:
  - "oauth2-proxy/oauth2-proxy-values.yaml"
---

# OAuth2 Proxy (Google Authentication)

OAuth2 Proxy è il componente responsabile della protezione dei servizi esposti su internet tramite Google OAuth.

## 1. Funzionamento
Agisce come un guardiano davanti a [[Traefik]]. Quando un utente tenta di accedere a un servizio esterno (es. `n8n.pindaroli.org`), Traefik interroga OAuth2 Proxy per verificare se l'utente ha una sessione valida.
- Se l'utente non è loggato, viene reindirizzato al login di Google.
- Se il login ha successo, Google restituisce un token che OAuth2 Proxy valida e memorizza in un cookie sicuro.

## 2. Configurazione Critica
- **Provider**: Google.
- **Domini Autorizzati**: Solo gli utenti con email autorizzate (Whitelisting) possono accedere.
- **Middleware Traefik**: Il middleware `oauth2-auth` di tipo `ForwardAuth` è quello che attiva questa protezione sugli IngressRoute.

## 3. Strategia di Esclusione
Come definito in [[purpose]], i servizi interni (`-internal.pindaroli.org`) **saltano** questo proxy per facilitare l'uso domestico e l'automazione locale.

## Relazioni
- Protegge l'accesso a: [[Traefik]].
- Si integra con: Google Cloud Console (Client ID & Secret).
- Fornisce identità a: App che non hanno un sistema di auth nativo.
