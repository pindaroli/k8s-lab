---
title: "Headlamp (Kubernetes Web UI Dashboard)"
last_updated: "2026-10-14"
confidence: "High"
tags:
  - "#kubernetes"
  - "#dashboard"
  - "#headlamp"
  - "#helm"
  - "#traefik"
provenance:
  - "headlamp/headlamp-values.yaml"
  - "wiki/plans/headlamp-kubernetes-integration.md"
---

# Headlamp (Kubernetes Cluster Web UI & Management)

**Headlamp** è la dashboard e interfaccia utente estendibile ufficiale per Kubernetes (`kubernetes-sigs`), adottata nel cluster Talos `k8s-lab` come interfaccia web unificata per il monitoraggio, l'ispezione e la gestione dei carichi di lavoro.

---

## 1. Dettagli di Deployment
- **Namespace**: `headlamp` (namespace dedicato isolato).
- **Chart Ufficiale**: `headlamp/headlamp` (Repo: `https://kubernetes-sigs.github.io/headlamp/`).
- **File Valori Dichiarativo**: [`headlamp/headlamp-values.yaml`](file:///Users/olindo/prj/k8s-lab/headlamp/headlamp-values.yaml).
- **Service Type**: `ClusterIP` su porta 80 (`targetPort: 4466`).
- **CoreDNS Interno**: `http://headlamp.headlamp.svc.cluster.local:80/`.

---

## 2. Autenticazione & Sicurezza RBAC
- **ServiceAccount**: `headlamp` nel namespace `headlamp`.
- **ClusterRoleBinding**: `headlamp-admin` associato al ruolo `cluster-admin` per la gestione completa del cluster.
- **In-Cluster Token Automatico**: `config.unsafeUseServiceAccountToken: true`. Il pod monta il token del ServiceAccount (`/var/run/secrets/kubernetes.io/serviceaccount/token`) e lo utilizza direttamente per autenticare le richieste dell'utente verso l'API Server (`https://kubernetes.default.svc`). Non viene richiesto alcun inserimento manuale di token nella UI.

---

## 3. Instradamento e Split-Horizon (Traefik)
L'`IngressRoute` di Traefik è gestito in modo 100% dichiarativo tramite la chiave `extraManifests` di Helm (*Golden Pattern / Anti-Loose-YAML Guard*):

1. **Accesso Interno LAN (Senza Auth)**:
   - **Hostname**: `https://headlamp-internal.pindaroli.org` (e alias breve `https://headlamp`).
   - Instradamento diretto al service `headlamp:80` senza richieste di autenticazione esterna.
2. **Accesso Esterno Internet (Protetto da Google OAuth2)**:
   - **Hostname**: `https://headlamp.pindaroli.org`.
   - Protetto dal middleware Traefik `oauth2-auth` (in namespace `traefik`), che richiede il login con account Google autorizzato in whitelist.
3. **Terminazione TLS**:
   - Certificato Wildcard Let's Encrypt `pindaroli-wildcard-tls` gestito da `cert-manager`.

---

## 4. Monitoraggio & Integrazione Dashboard
- **Homepage**: Registrato nella categoria `Kubernetes Services` sia in `homepage/homepage.yaml` che in `homepage/homepage-local.yaml`.
- **Healthcheck in Tempo Reale**: monitorato via `siteMonitor: http://headlamp.headlamp.svc.cluster.local:80/`.

---

## 5. Maintenance & Troubleshooting

### Verifica stato del carico:
```bash
kubectl get pods,svc,ingressroute -n headlamp -o wide
```

### Ispezione log:
```bash
kubectl logs -n headlamp -l app.kubernetes.io/name=headlamp --tail=50 -f
```

### Aggiornamento dichiarativo via Helm:
```bash
helm upgrade --install headlamp headlamp/headlamp --namespace headlamp --create-namespace -f headlamp/headlamp-values.yaml
```

### Riavvio del pod:
```bash
kubectl rollout restart deployment/headlamp -n headlamp
```

---

## Relazioni Architetturali
- Eseguito su: [[Talos_Cluster]] (`talos-cp-01`).
- Instradato da: [[Traefik]] (VIP MetalLB `10.10.20.56`).
- Protetto esternamente da: [[OAuth2_Proxy]].
- Visualizzato su: [[Homepage]].
