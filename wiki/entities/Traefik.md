---
title: "Traefik (Ingress Controller)"
last_updated: "2026-05-03"
confidence: "High"
tags:
  - "#network"
  - "#ingress"
  - "#traefik"
provenance:
  - "traefik/traefik-values.yaml"
---

# Traefik (Edge Router)

Traefik è l'Ingress Controller del cluster, responsabile del routing del traffico HTTP/HTTPS e della terminazione SSL.

## 1. Configurazione di Rete
- **Entrypoints**: `web` (80) e `websecure` (443).
- **Service Type**: `LoadBalancer` via MetalLB.
- **IP Esterno (MetalLB)**: `10.10.20.56`.
- **Policy Traffico**: Impostata su `externalTrafficPolicy: Local` per preservare l'IP sorgente del client (necessario per i log e la sicurezza).

## 2. Sicurezza e Certificati
- **SSL/TLS**: Gestiti tramite `cert-manager` con la Cloudflare DNS Challenge.
- **Wildcard**: Supporta `*.pindaroli.org`.
- **OAuth2**: Tutti i servizi esterni devono passare attraverso il middleware `oauth2-auth` (Google Login) configurato su Traefik.

## 3. Strategia Split-Horizon
- Traefik risponde sia alle richieste provenienti dal Tunnel Cloudflare (Esterno) che a quelle dirette via [[OPNsense]] (Interno).
- Gli IngressRoute per l'interno non utilizzano il middleware OAuth2 per permettere un accesso rapido e fidato dalla LAN.

## 4. Maintenance & Troubleshooting
Per aggiornare l'installazione tramite Helm:
```bash
helm upgrade traefik traefik/traefik --namespace traefik -f traefik/traefik-values.yaml
```

**Diagnostica base**:
- **Log**: `kubectl logs -n traefik -l app.kubernetes.io/name=traefik`
- **Errori 404**: Verificare lo stato dell'IngressRoute (`kubectl describe ingressroute <name> -n <ns>`).
- **Riavvio Forzato**: `kubectl rollout restart deployment/traefik -n traefik`

## Relazioni
- Riceve traffico da: [[OPNsense]] e Cloudflare Tunnel.
- Smista traffico verso: Tutti i pod del [[Talos_Cluster]].
- Autenticazione via: [[OAuth2_Proxy]].
