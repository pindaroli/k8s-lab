# Piano: Sovranità dei Segreti con SOPS + Age

**Target**: Cluster GEMINI (`pindaroli.org`) · **Data**: 2026-05-07  
**Autore**: Antigravity AI Engineering

> [!IMPORTANT]
> Questo piano sostituisce il workflow manuale basato su `gitignore + secrets.yaml locale`.  
> Al termine, **NESSUN segreto** viaggerà mai più in chiaro nel repository, né come Base64.

---

## Inventario Completo dei Segreti (Audit 2026-05-07)

> [!NOTE]
> Audit eseguito live sul cluster. Segreti di sistema (Helm releases, CA interne, TLS auto-generati) esclusi — non richiedono gestione manuale.

### 🔴 Priorità Alta — Segreti Applicativi con Credenziali Esterne

| Secret (K8s) | Namespace | Chiavi | Stato Attuale | Target SOPS File |
| :--- | :--- | :--- | :--- | :--- |
| `oauth2-proxy` | `oauth2-proxy` | `client-id`, `client-secret`, `cookie-secret` | 🔴 File locale in `.gitignore` (già leaked) | `secrets-sops/oauth2-proxy.enc.yaml` |
| `cloudflare-api-token-secret` | `cert-manager` | `api-token` | 🟡 File locale in `.gitignore` | `secrets-sops/cloudflare-token.enc.yaml` |
| `servarr-api-keys` | `arr` | `lidarr-api-key`, `prowlarr-api-key`, `radarr-api-key`, `qbittorrent-user`, `qbittorrent-pass` | 🔴 Nessun file sorgente in repo | `secrets-sops/servarr-api-keys.enc.yaml` |
| `xray-secrets` | `xray` | `private-key`, `public-key`, `short-id`, `uuid` | 🔴 Nessun file sorgente in repo | `secrets-sops/xray-secrets.enc.yaml` |
| `alertmanager-telegram-secret` | `monitoring` | `chat_id`, `token` | 🔴 Nessun file sorgente in repo | `secrets-sops/alertmanager-telegram.enc.yaml` |
| `grafana-admin-secret` | `monitoring` | `admin-user`, `admin-password` | 🔴 Nessun file sorgente in repo | `secrets-sops/grafana-admin.enc.yaml` |
| `tunnel-credentials` | `default` | `credentials.json` | 🟡 Nessun file sorgente in repo | `secrets-sops/cloudflare-tunnel.enc.yaml` |

### 🟡 Priorità Media — Segreti Infrastrutturali

| Secret (K8s) | Namespace | Chiavi | Stato Attuale | Target SOPS File |
| :--- | :--- | :--- | :--- | :--- |
| `minio-creds` | `cnpg-system` | `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY` | 🔴 Nessun file sorgente in repo | `secrets-sops/minio-creds.enc.yaml` |
| `velero` | `velero` | `cloud` (AWS-format per MinIO) | 🟡 Nessun file sorgente in repo | `secrets-sops/velero-creds.enc.yaml` |
| `basic-auth-secret` | `traefik` | `users` (htpasswd) | 🟡 Nessun file sorgente in repo | `secrets-sops/traefik-basic-auth.enc.yaml` |
| `dashboard-auth-secret` | `traefik` | `username`, `password` | 🟡 Nessun file sorgente in repo | `secrets-sops/traefik-dashboard-auth.enc.yaml` |
| `kasmweb-secret` | `kasmweb` | `password` | 🟡 Nessun file sorgente in repo | `secrets-sops/kasmweb.enc.yaml` |
| `xray-client-config` | `arr` | `config.json` (JSON config Xray client) | 🔴 Nessun file sorgente in repo | `secrets-sops/xray-client-config.enc.yaml` |
| `n8n-encryption-key-secret-v2` | `n8n` | `N8N_ENCRYPTION_KEY` | 🔴 Nessun file sorgente in repo | `secrets-sops/n8n-encryption-key.enc.yaml` |
| `n8n-db-secrets` | `n8n` | `DB_POSTGRESDB_PASSWORD` | 🔴 Nessun file sorgente in repo | `secrets-sops/n8n-db-secrets.enc.yaml` |

### 🟢 Priorità Bassa — Segreti DB (Gestiti da CNPG o auto-derivati)

| Secret (K8s) | Namespace | Note |
| :--- | :--- | :--- |
| `postgres-main-app` | `cnpg-system` | Auto-generato da CloudNativePG. Non gestire manualmente. |
| `n8n-db-password` | `cnpg-system` / `n8n` | Auto-generato da CNPG, sincronizzato. Non gestire manualmente. |
| `n8n-postgresql` | `n8n` | Credenziali DB derivate. Non gestire manualmente. |
| `prefect-server-postgresql-connection` | `prefect` | Connection string — valutare se gestire manualmente o lasciare a CNPG. |

### ⚪ Esclusi (Nessuna Azione Necessaria)

| Tipo | Motivo |
| :--- | :--- |
| `pindaroli-wildcard-tls` (tutti i NS) | Gestito da cert-manager + Cloudflare. Auto-rinnovato. |
| `sh.helm.release.v1.*` | Metadati Helm interni. Non contengono segreti utente. |
| `*-ca`, `*-webhook-cert`, `*-tls` interni | Certificati auto-generati dagli operatori. |

### 💡 Logica di Esclusione (Master vs Managed)
La "Sovranità dei Segreti" via SOPS si applica esclusivamente ai **Master Secrets** (credenziali statiche fornite dall'utente). I segreti **Managed** sono esclusi per i seguenti motivi:
- **Automazione Cert-Manager**: I certificati TLS vengono rinnovati ogni 60-90 giorni. Salvarli in Git richiederebbe commit manuali continui, rompendo l'automazione.
- **Integrità Helm**: Le release di Helm sono metadati di stato volatili; la loro persistenza è gestita dal database interno di Helm, non dalla configurazione dichiarativa dell'utente.
- **Sicurezza Interna (mTLS)**: I certificati CA e Webhook sono effimeri e gestiti dagli operatori per la comunicazione sicura inter-pod. Non sono asset da migrare in caso di disaster recovery.


---

## Architettura Target (TO-BE)

```
Git Repository
├── .sops.yaml                              ← Regole di cifratura globali [✅ FATTO]
├── secrets-sops/
│   ├── oauth2-proxy.enc.yaml              ← 🔴 Priorità 1
│   ├── cloudflare-token.enc.yaml          ← 🔴 Priorità 2
│   ├── servarr-api-keys.enc.yaml          ← 🔴 Priorità 3
│   ├── xray-secrets.enc.yaml              ← 🔴 Priorità 4
│   ├── alertmanager-telegram.enc.yaml     ← 🔴 Priorità 5
│   ├── grafana-admin.enc.yaml             ← 🔴 Priorità 6
│   ├── cloudflare-tunnel.enc.yaml         ← 🟡 Priorità 7
│   ├── minio-creds.enc.yaml               ← 🟡 Priorità 8
│   ├── velero-creds.enc.yaml              ← 🟡 Priorità 9
│   ├── traefik-basic-auth.enc.yaml        ← 🟡 Priorità 10
│   ├── traefik-dashboard-auth.enc.yaml    ← 🟡 Priorità 11
│   └── kasmweb.enc.yaml                   ← 🟡 Priorità 12
└── [Fase 4] flux/                         ← GitOps automatico (futuro)
    └── clusters/gemini/kustomization.yaml

Cluster K8s (Talos)
└── [Fase 4] flux-system/
    └── sops-age (Secret)                  ← Chiave privata age, solo nel cluster
        └── Flux kustomize-controller
            └── Decripta automaticamente (Reconciliation loop)
```

---

## Fase 1: Setup Strumenti Locali
**Obiettivo**: Installare e configurare gli strumenti sul Mac Studio.  
**Tempo stimato**: ~30 minuti

### 1.1 Installazione

```bash
brew install age sops pre-commit
helm plugin install https://github.com/jkroepke/helm-secrets
```

### 1.2 Generazione Chiave Age

```bash
age-keygen -o ~/.config/sops/age/keys.txt
# Output: Public key: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> [!CAUTION]
> **`~/.config/sops/age/keys.txt` è la master key.**  
> Fare un backup offline (es. file cifrato su TrueNAS o su carta fisica).  
> Perderla = perdere accesso a TUTTI i segreti cifrati.

### 1.3 Configurazione Variabile d'Ambiente

```bash
# Aggiungere a ~/.zshrc
export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
```

---

## Fase 2: Configurazione Repository
**Obiettivo**: Definire le regole di cifratura e strutturare le cartelle.  
**Tempo stimato**: ~1 ora

### 2.1 File `.sops.yaml` nella Root del Progetto

```yaml
# k8s-lab/.sops.yaml
creation_rules:
  - path_regex: secrets-sops/.*\.enc\.yaml$
    encrypted_regex: ^(data|stringData|password|secret|token|key|apiKey|client.*)$
    age: <PUBKEY_AGE_QUI>

  - path_regex: helm-charts/.*/secrets\.enc\.yaml$
    encrypted_regex: ^(password|secret|token|key|apiKey|client.*)$
    age: <PUBKEY_AGE_QUI>
```

> [!NOTE]
> `encrypted_regex` cifra solo i **valori** sensibili, lasciando leggibili le chiavi YAML.  
> I `git diff` rimangono significativi e i conflitti di merge gestibili.

### 2.2 Aggiornamento `.gitignore`

```
secrets-sops/**/*.yaml
!secrets-sops/**/*.enc.yaml
```

---

## Fase 3: Migrazione Segreti Esistenti
**Obiettivo**: Cifrare con SOPS TUTTI i segreti operativi del cluster.  
**Tempo stimato**: ~3-4 ore  
**Metodo Generale**:
```bash
# Template: Crea in /tmp → Cifra → Cancella /tmp → Committa
sops --encrypt /tmp/<secret>-plain.yaml > secrets-sops/<secret>.enc.yaml && rm /tmp/<secret>-plain.yaml
# Test decifratura
sops --decrypt secrets-sops/<secret>.enc.yaml | kubectl apply -f -
```

### 3.1 — OAuth2 Proxy 🔴
**Secret K8s**: `oauth2-proxy/oauth2-proxy`  
**Keys**: `client-id`, `client-secret`, `cookie-secret`
```bash
sops --encrypt /tmp/oauth2-proxy-plain.yaml > secrets-sops/oauth2-proxy.enc.yaml
```

### 3.2 — Cloudflare API Token 🔴
**Secret K8s**: `cert-manager/cloudflare-api-token-secret`  
**Keys**: `api-token`  
**Nota**: Leggere il token attuale da `cert-manager/cloudflare-token-secret.yaml` locale.
```bash
sops --encrypt /tmp/cloudflare-token-plain.yaml > secrets-sops/cloudflare-token.enc.yaml
```

### 3.3 — Servarr API Keys 🔴
**Secret K8s**: `arr/servarr-api-keys`  
**Keys**: `lidarr-api-key`, `prowlarr-api-key`, `radarr-api-key`, `qbittorrent-user`, `qbittorrent-pass`  
**Nota**: Valori leggibili dal cluster attuale tramite `kubectl get secret servarr-api-keys -n arr -o jsonpath=...`
```bash
sops --encrypt /tmp/servarr-api-keys-plain.yaml > secrets-sops/servarr-api-keys.enc.yaml
```

### 3.4 — Xray Secrets 🔴
**Secret K8s**: `xray/xray-secrets`  
**Keys**: `private-key`, `public-key`, `short-id`, `uuid`
```bash
sops --encrypt /tmp/xray-secrets-plain.yaml > secrets-sops/xray-secrets.enc.yaml
```

### 3.5 — Alertmanager Telegram 🔴
**Secret K8s**: `monitoring/alertmanager-telegram-secret`  
**Keys**: `chat_id`, `token`
```bash
sops --encrypt /tmp/alertmanager-telegram-plain.yaml > secrets-sops/alertmanager-telegram.enc.yaml
```

### 3.6 — Grafana Admin 🔴
**Secret K8s**: `monitoring/grafana-admin-secret`  
**Keys**: `admin-user`, `admin-password`
```bash
sops --encrypt /tmp/grafana-admin-plain.yaml > secrets-sops/grafana-admin.enc.yaml
```

### 3.7 — Cloudflare Tunnel 🟡
**Secret K8s**: `default/tunnel-credentials`  
**Keys**: `credentials.json` (JSON completo del tunnel Cloudflare)
```bash
sops --encrypt /tmp/cloudflare-tunnel-plain.yaml > secrets-sops/cloudflare-tunnel.enc.yaml
```

### 3.8 — MinIO Credentials 🟡
**Secret K8s**: `cnpg-system/minio-creds`  
**Keys**: `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`
```bash
sops --encrypt /tmp/minio-creds-plain.yaml > secrets-sops/minio-creds.enc.yaml
```

### 3.9 — Velero Credentials 🟡
**Secret K8s**: `velero/velero`  
**Keys**: `cloud` (AWS-format credentials per MinIO)
```bash
sops --encrypt /tmp/velero-creds-plain.yaml > secrets-sops/velero-creds.enc.yaml
```

### 3.10 — Traefik Basic Auth 🟡
**Secret K8s**: `traefik/basic-auth-secret` e `traefik/dashboard-auth-secret`  
**Keys**: `users` (htpasswd format)
```bash
sops --encrypt /tmp/traefik-basic-auth-plain.yaml > secrets-sops/traefik-basic-auth.enc.yaml
sops --encrypt /tmp/traefik-dashboard-auth-plain.yaml > secrets-sops/traefik-dashboard-auth.enc.yaml
```

### 3.11 — Test Decifratura e Apply
```bash
# Test decifratura (output su stdout — MAI redirigere su file)
sops --decrypt secrets-sops/oauth2-proxy.enc.yaml

# Apply diretto al cluster senza file intermedi
sops --decrypt secrets-sops/<secret>.enc.yaml | kubectl apply -f -

# Commit finale
git add secrets-sops/
git commit -m "feat(security): migrate all cluster secrets to SOPS encryption"
```

---

## Fase 4: Automazione GitOps con Flux CD
**Obiettivo**: Eliminare completamente l'apply manuale.  
**Tempo stimato**: ~3-4 ore

> [!WARNING]
> **Flux CD è un cambiamento architetturale significativo.**  
> Eseguire `velero backup create backup-pre-flux --wait` prima di procedere.

### 4.1 Installazione Flux CD

```bash
brew install fluxcd/tap/flux
flux check --pre

flux bootstrap github \
  --owner=pindaroli \
  --repository=k8s-lab \
  --branch=main \
  --path=./flux \
  --personal
```

### 4.2 Iniezione Chiave Age nel Cluster

```bash
cat ~/.config/sops/age/keys.txt | \
  kubectl create secret generic sops-age \
    --namespace=flux-system \
    --from-file=age.agekey=/dev/stdin
```

### 4.3 Kustomization Flux con Decifratura Automatica

```yaml
# flux/clusters/gemini/kustomization.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: secrets
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: k8s-lab
  path: ./secrets-sops
  prune: true
  decryption:
    provider: sops
    secretRef:
      name: sops-age
```

> [!NOTE]
> Da questo momento ogni `git push` di un `.enc.yaml` viene automaticamente  
> decrittografato e applicato da Flux. **Zero `kubectl apply` manuali.**

### 4.4 Integrazione helm-secrets

```bash
helm secrets upgrade --install oauth2-proxy \
  helm-charts/oauth2-proxy/ \
  -f helm-charts/oauth2-proxy/values.yaml \
  -f helm-charts/oauth2-proxy/secrets.enc.yaml \
  -n oauth2-proxy
```

---

## Fase 5: Guardrail Anti-Leak (Pre-Commit Hooks)
**Obiettivo**: Impedire fisicamente il commit di segreti in chiaro.  
**Tempo stimato**: ~30 minuti

```yaml
# k8s-lab/.pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: secrets-sops/.*\.enc\.yaml$

  - repo: local
    hooks:
      - id: sops-check
        name: Check SOPS encryption
        language: script
        entry: scripts/check-sops-encrypted.sh
        files: ^secrets-sops/.*\.enc\.yaml$
```

```bash
pre-commit install
pre-commit run --all-files
```

---

## Piano di Rollout e Priorità

| Priorità | Fase | Azione | Rischio | Dipendenze |
| :--- | :--- | :--- | :--- | :--- |
| 🔴 Alta | 1 | Setup tools locali | Zero | Nessuna |
| 🔴 Alta | 2 | `.sops.yaml` + struttura | Zero | Fase 1 |
| 🔴 Alta | 3.1 | Migrare `oauth2-proxy` | Basso | Fase 2 |
| 🟡 Media | 3.2 | Migrare altri segreti | Basso | Fase 2 |
| 🟡 Media | 5 | Pre-commit hooks | Zero | Fase 2 |
| 🟢 Bassa | 4 | Flux CD | **Alto** | Velero Backup |

---

## Confronto Workflow: Prima vs Dopo

| Azione | AS-IS (Oggi) | TO-BE (SOPS + Flux) |
| :--- | :--- | :--- |
| Aggiornare un segreto | Modifica locale → `kubectl apply` manuale | `sops --edit file.enc.yaml` → `git push` |
| Vedere le modifiche | Impossibile (Base64 opaco) | `git diff` (struttura visibile, valori cifrati) |
| Rollback segreto | Ripristino manuale | `git revert` → Flux riconcilia automaticamente |
| Prevenzione leak | `.gitignore` (fallibile) | Pre-commit hook (blocco fisico) |
| Audit trail | Nessuno | Git history + Flux events log |
| Dipendenza da Ansible | Manuale per ogni deploy K8s | Eliminata per i segreti K8s |

---
*Piano redatto da Antigravity AI Engineering — 2026-05-07*
