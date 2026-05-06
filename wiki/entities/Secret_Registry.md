---
title: "Secret Registry (Security Source of Truth)"
last_updated: "2026-05-06"
confidence: "High"
tags:
  - "#security"
  - "#secrets"
  - "#ansible-vault"
  - "#k8s"
provenance:
  - "ansible/vars/secrets.yml"
  - "oauth2-proxy/secrets.yaml"
---

# Secret Registry

Questo documento definisce la gestione, la distribuzione e la rotazione dei segreti nell'ecosistema GEMINI.

> [!CRITICAL]
> **SOURCE OF TRUTH**: Tutti i segreti persistenti risiedono in **Ansible Vault** (`ansible/vars/secrets.yml`). 
> I file manifest di Kubernetes (`secrets.yaml`) sono considerati "volatili" e NON devono mai essere committati in chiaro su Git.

## 1. Governance dei Segreti
L'architettura segue il principio della **Separazione tra Configurazione e Credenziali**:
- **Ansible Vault**: Cifra i dati sensibili a riposo.
- **Gitignore Protection**: Tutti i file che contengono segreti in chiaro o base64 (es. `.json`, `.key`, `secrets.yaml`) devono essere inclusi nel `.gitignore`.
- **Automazione**: I segreti vengono iniettati nel cluster tramite playbook Ansible o applicati manualmente da file locali protetti.

## 2. Matrice dei Segreti (Secrets Mapping)

| Nome Secret (K8s) | Namespace | Sorgente (Vault Key) | Destinazione / Utilizzo |
| :--- | :--- | :--- | :--- |
| `oauth2-proxy` | `oauth2-proxy` | `google_client_id`, `google_client_secret` | Autenticazione Google per accesso esterno |
| `pindaroli-wildcard-tls` | *Multi-NS* | Cloudflare API (per Cert-Manager) | Certificati SSL Let's Encrypt |
| `cloudflare-token-secret` | `cert-manager` | `cloudflare_api_token` | DNS-01 Challenge |

## 3. Procedure Operative

### Rotazione Credenziali OAuth2
Per aggiornare le chiavi di Google OAuth:
1. Ricevere il nuovo file JSON (es. `oauth2-proxy/aouth2-secret-noncommitare.json`).
2. Aggiornare le chiavi corrispondenti in Ansible Vault.
3. Generare i valori base64 e popolare il file locale `oauth2-proxy/secrets.yaml`.
4. Applicare al cluster: `kubectl apply -f oauth2-proxy/secrets.yaml`.
5. Riavviare il servizio: `kubectl rollout restart deployment oauth2-proxy -n oauth2-proxy`.

## 4. File Sensibili Ignorati (Local Inventory)
- `oauth2-proxy/secrets.yaml`: Manifest K8s con credenziali base64.
- `secrets/setEnv.sh`: Script locale per caricare variabili d'ambiente.
- `secrets/google_client_secret.json`: Backup locale credenziali Google.

## Relazioni
- Governa: Accesso a tutti i servizi tramite [[OAuth2_Proxy]].
- Dipende da: Ansible Vault Password (vedi [[todo]] per automazione).
- Impatta: [[Traefik]], [[Talos_Cluster]].
