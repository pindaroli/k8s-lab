# Piano: Deployment di Vaultwarden

**Target**: Cluster GEMINI (`pindaroli.org`) · **Data**: 2026-05-08
**Autore**: Antigravity AI Engineering

> [!IMPORTANT]
> Vaultwarden è un password manager critico. I dati NON devono mai andare persi.
> Architettura: **PostgreSQL** (`postgres-main`) per il database + **NFS TrueNAS** per i file binari (`/data`).

---

## Decisioni Architetturali

| Aspetto | Scelta | Motivazione |
| :--- | :--- | :--- |
| **Database** | PostgreSQL su `postgres-main` (CloudNativePG) | Backup WAL automatici su MinIO, già usato da n8n/prefect/arr stack |
| **Storage `/data`** | PVC NFS 10Gi via `csi-nfs-stripe-arr-conf` | ZFS + snapshot TrueNAS per attachments, RSA keys, icon cache |
| **Secrets** | **SOPS** (coerente con `sops-secret-sovereignty`) | `vaultwarden-secrets.enc.yaml` in `secrets-sops/` |
| **Accesso esterno** | **Cloudflare senza OAuth2 — Opzione A** | Vaultwarden ha auth propria robusta (account login + 2FA TOTP). OAuth2 in front rompe `/api/` e `/identity/` usati dalla browser extension anche senza app mobile |
| **Registrazioni** | `SIGNUPS_ALLOWED=false` | Disabilitare dopo il primo account |
| **Admin panel** | Protetto da `ADMIN_TOKEN` bcrypt | Token generato con `htpasswd -bnBC 10 "" token \| tr -d ":"` |

### Nota su OAuth2 e Vaultwarden

Anche senza usare l'app mobile, **OAuth2 non può essere messo in front dell'intera applicazione** perché:
- La **browser extension** (uso primario del password manager) comunica programmaticamente con `/api/` e `/identity/` — non può seguire redirect OAuth2.
- Il WebSocket `/notifications/hub` richiede connessione diretta.

L'unica superficie ragionevole per OAuth2 sarebbe `/admin` (opzione B, non scelta). Per ora `ADMIN_TOKEN` bcrypt è sufficiente.

---

## Architettura

```
Vaultwarden Pod (namespace: vaultwarden)
  ├── DATABASE_URL → postgres-main-rw.cnpg-system.svc.cluster.local:5432/vaultwarden
  └── /data        → PVC NFS → TrueNAS /mnt/stripe/k8s-vaultwarden
                     (RSA keys, attachments, icon cache, sends)

Ingress:
  vaultwarden.pindaroli.org          → Traefik → port 80  (Web Vault + API)
  vaultwarden.pindaroli.org/notifications/hub → port 3012 (WebSocket)
  vaultwarden-internal.pindaroli.org → Traefik → port 80  (LAN only, no auth layer)
```

---

## File da Creare

```
vaultwarden/
├── namespace.yaml
├── vaultwarden-pvc.yaml          ← StorageClass: csi-nfs-stripe-arr-conf, 10Gi
├── vaultwarden-db.yaml           ← Oggetto Database CloudNativePG
├── vaultwarden-deployment.yaml   ← Image: vaultwarden/server:latest
├── vaultwarden-service.yaml      ← ClusterIP: 80 + 3012
└── vaultwarden-ingressroute.yaml ← Traefik IngressRoute + TLS wildcard

secrets-sops/
└── vaultwarden-secrets.enc.yaml  ← DATABASE_URL + ADMIN_TOKEN (SOPS cifrato)
```

---

## File da Modificare

| File | Modifica |
| :--- | :--- |
| `postgres/cluster.yaml` | Aggiungere ruolo `vaultwarden` in `managed.roles` |
| `storage.json` | Aggiungere entry `k8s_vaultwarden` nella sezione `exports` |
| `rete.json` | Aggiungere `vaultwarden` e `vaultwarden-internal` agli `aliases` del nodo `traefik-lb` (IP `10.10.20.56`) |
| `homepage/` | Aggiungere widget Vaultwarden |

---

## Prerequisiti Manuali (TrueNAS)

> [!WARNING]
> Prima di eseguire i manifest K8s, creare su TrueNAS:
> 1. Dataset ZFS: `stripe/k8s-vaultwarden`
> 2. NFS Export del dataset accessibile da `10.10.10.0/24` e `10.10.20.0/24`

---

## Secrets Necessari

File: `secrets-sops/vaultwarden-secrets.enc.yaml`

```yaml
# Template in chiaro (MAI committare — cifrare subito con SOPS)
apiVersion: v1
kind: Secret
metadata:
  name: vaultwarden-secrets
  namespace: vaultwarden
type: Opaque
stringData:
  DATABASE_URL: "postgresql://vaultwarden:<PASSWORD>@postgres-main-rw.cnpg-system.svc.cluster.local/vaultwarden"
  ADMIN_TOKEN: "<BCRYPT_HASH>"  # htpasswd -bnBC 10 "" <token> | tr -d ":"
```

---

## Ordine di Esecuzione

1. ✅ Piano approvato
2. ⬜ Creare dataset NFS su TrueNAS: `stripe/k8s-vaultwarden` **(manuale)**
3. ⬜ Aggiungere ruolo `vaultwarden` in `postgres/cluster.yaml` + creare `vaultwarden-db.yaml`
4. ⬜ Creare `vaultwarden/namespace.yaml` + `vaultwarden-pvc.yaml`
5. ⬜ Generare e cifrare i secrets con SOPS → `secrets-sops/vaultwarden-secrets.enc.yaml`
6. ⬜ Creare `vaultwarden-deployment.yaml` + `vaultwarden-service.yaml`
7. ⬜ Creare `vaultwarden-ingressroute.yaml`
8. ⬜ Aggiornare `rete.json` + sync DNS: `ansible-playbook ansible/playbooks/opnsense_sync_dns.yml`
9. ⬜ Aggiornare `storage.json`
10. ⬜ Test: curl, login browser, browser extension, admin panel
11. ⬜ Aggiornare Homepage widget

---

## Verifica

```bash
# Pod running
kubectl get pods -n vaultwarden

# NFS montato
kubectl exec -n vaultwarden deploy/vaultwarden -- df -h /data

# DB connesso (log Vaultwarden)
kubectl logs -n vaultwarden deploy/vaultwarden | grep -i "database\|connected"

# DB presente su postgres-main
kubectl exec -n cnpg-system postgres-main-3 -- psql -U postgres -c "\l" | grep vaultwarden

# HTTPS accessibile
curl -I https://vaultwarden.pindaroli.org

# Admin panel: https://vaultwarden.pindaroli.org/admin
```

---

## Relazioni Wiki

- Dipende da: [[Talos_Cluster]], [[TrueNAS]], [[Traefik]], [[Storage_Registry]]
- Usa: `postgres-main` (CloudNativePG), `csi-nfs-stripe-arr-conf`, `pindaroli-wildcard-tls`
- Secrets gestiti da: [[sops-secret-sovereignty]]

---
*Piano redatto da Antigravity AI Engineering — 2026-05-08*
