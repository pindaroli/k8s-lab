# Piano: Sovranità dei Segreti con SOPS + Age

**Target**: Cluster GEMINI (`pindaroli.org`) · **Data**: 2026-05-07  
**Autore**: Antigravity AI Engineering

> [!IMPORTANT]
> Questo piano sostituisce il workflow manuale basato su `gitignore + secrets.yaml locale`.  
> Al termine, **NESSUN segreto** viaggerà mai più in chiaro nel repository, né come Base64.

---

## Analisi della Situazione Attuale (AS-IS)

| Componente | Stato Attuale | Rischio |
| :--- | :--- | :--- |
| `oauth2-proxy/secrets.yaml` | Base64 in chiaro, rimosso dopo leak | 🔴 Leak già avvenuto |
| `ansible/vars/secrets.yml` | Ansible Vault AES256 ✅ | 🟡 Non integrato con K8s |
| `cert-manager/cloudflare-token-secret.yaml` | In `.gitignore`, non committato | 🟡 Manuale, no automazione |
| `helm-charts/` | Nessuna cifratura valori Helm | 🔴 Potenziale leak futuro |
| Git History | Contiene trace dei vecchi segreti | 🟡 Chiavi revocate, ma cronologia sporca |

---

## Architettura Target (TO-BE)

```
Git Repository
├── .sops.yaml                       ← Regole di cifratura globali
├── secrets-sops/
│   ├── oauth2-proxy.enc.yaml        ← Cifrato con SOPS/Age ✅
│   ├── cloudflare-token.enc.yaml    ← Cifrato con SOPS/Age ✅
│   └── cert-manager.enc.yaml        ← Cifrato con SOPS/Age ✅
└── helm-charts/
    └── <chart>/secrets.enc.yaml     ← Valori Helm cifrati ✅

Cluster K8s (Talos)
└── flux-system/
    └── sops-age (Secret)            ← Chiave privata age, solo nel cluster
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
**Obiettivo**: Cifrare con SOPS tutti i segreti attualmente gestiti manualmente.  
**Tempo stimato**: ~2 ore

### 3.1 OAuth2 Proxy (Priorità: Alta — già soggetto a leak)

```bash
# 1. Creare il manifest in chiaro (solo in /tmp, MAI committare)
cat > /tmp/oauth2-proxy-plain.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: oauth2-proxy
  namespace: oauth2-proxy
type: Opaque
stringData:
  client-id: "REDACTED_GOOGLE_CLIENT_ID"
  client-secret: "REDACTED_GOOGLE_CLIENT_SECRET"
  cookie-secret: "<VALORE_COOKIE_SECRET>"
EOF

# 2. Cifrare
sops --encrypt /tmp/oauth2-proxy-plain.yaml > secrets-sops/oauth2-proxy.enc.yaml

# 3. Eliminare il file in chiaro
rm /tmp/oauth2-proxy-plain.yaml

# 4. Ora è sicuro committare ✅
git add secrets-sops/oauth2-proxy.enc.yaml
git commit -m "feat(security): add sops-encrypted oauth2-proxy secret"
```

### 3.2 Cloudflare Token e cert-manager

```bash
sops --encrypt /tmp/cloudflare-token-plain.yaml > secrets-sops/cloudflare-token.enc.yaml
```

### 3.3 Test Decifratura Locale

```bash
# Output su stdout — MAI redirigere su file
sops --decrypt secrets-sops/oauth2-proxy.enc.yaml

# Applicazione diretta al cluster senza file intermedi
sops --decrypt secrets-sops/oauth2-proxy.enc.yaml | kubectl apply -f -
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
