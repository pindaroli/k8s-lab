# Technical Incident: 2026-05-06-GOOGLE-OAUTH2-CREDENTIAL-LEAK

**Status**: RESOLVED
**Incident Date**: 2026-05-06
**Resolution Date**: 2026-05-06
**Component**: Security / OAuth2 Proxy / Git Governance

## 1. Incident Description
Un file sensibile contenente le credenziali in chiaro di Google OAuth2 (`client-id` e `client-secret`) è stato accidentalmente tracciato e committato nel repository Git. Il leak è stato rilevato da **GitGuardian**, che ha generato un'allerta di sicurezza critica. Le credenziali esposte permettevano potenzialmente l'intercettazione del flusso di autenticazione per tutti i servizi esterni del cluster `pindaroli.org`.

## 2. Technical Findings
1.  **Git Misconfiguration**: Il file `oauth2-proxy/secrets.yaml` non era incluso nel `.gitignore`, permettendo il commit di valori sensibili in base64 (facilmente decifrabili).
2.  **Manual Secrets Management**: La mancanza di un registro centralizzato dei segreti ha portato alla proliferazione di file helper locali (es. `setEnv.sh`, `google_client_secret.json`) non coordinati.
3.  **Credential Exposure**: Le chiavi sono rimaste esposte nella cronologia di Git, rendendole vulnerabili anche dopo l'eventuale cancellazione del file dal commit corrente.

## 3. Corrective Actions Taken
- **Credential Rotation**: Generate nuove credenziali su Google Cloud Console. Le vecchie chiavi sono state invalidate.
- **Cluster Update**: Aggiornato il secret Kubernetes `oauth2-proxy` nel namespace `oauth2-proxy` e riavviato il deployment per rendere operative le nuove chiavi.
- **Repository Hardening**: 
    - Aggiunto `oauth2-proxy/secrets.yaml` al `.gitignore`.
    - Eseguito `git rm --cached` per rimuovere il file dall'indice Git mantenendo la copia locale.
- **Local Alignment**: Aggiornati i file locali `secrets/setEnv.sh` e `secrets/google_client_secret.json` con le nuove credenziali.
- **Validation**: Eseguito test di accesso esterno tramite l'agente AI (fetcher esterno) confermando il corretto reindirizzamento al login Google con il nuovo `client_id`.

## 4. Hardening & Prevention
- **Secret Registry**: Creato `wiki/entities/Secret_Registry.md` come Single Source of Truth per la mappatura di tutti i segreti del cluster.
- **Governance Update**: Aggiornato `GEMINI.md` per includere il Secret Registry nelle mappe concettuali obbligatorie.
- **Vault Automation Task**: Inserito nel `todo.md` l'obiettivo di automatizzare l'accesso ad Ansible Vault (`.vault_pass`) per eliminare la gestione manuale dei file YAML sensibili.
- **GitGuardian Sync**: L'incidente deve essere segnato come "Resolved (Revoked)" sulla dashboard di GitGuardian.

---
*Reported by Antigravity AI Engineering*
