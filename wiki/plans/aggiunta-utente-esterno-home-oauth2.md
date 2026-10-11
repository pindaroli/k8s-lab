---
title: "Aggiunta Nuovo Utente Esterno su home.pindaroli.org (OAuth2-Proxy)"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-08
tags:
  - "#plan"
  - "#oauth2"
  - "#security"
  - "#traefik"
  - "#homepage"
---

# Piano: Aggiunta Nuovo Utente Esterno su home.pindaroli.org (OAuth2-Proxy)

> [!IMPORTANT]
> **Obiettivo**: Definire la procedura operativa completa e test-driven per abilitare un nuovo utente esterno (account Google) all'accesso via internet alla dashboard Homepage (`https://home.pindaroli.org`), protetta da Traefik ForwardAuth e OAuth2-Proxy.

---

## 1. Architettura dell'Accesso Esterno

L'accesso da internet a `https://home.pindaroli.org` segue questa catena di sicurezza:

```
[ Client Esterno / Internet ]
              │
              ▼
   Cloudflare Edge (DNS / Proxy)
              │
              ▼ (Cloudflare Tunnel: cloudflared)
   Traefik IngressRoute (default/homepage-ingress-external)
              │
              ▼ (Middleware: traefik/oauth2-auth)
   OAuth2-Proxy (oauth2-proxy/oauth2-proxy:4180)
         ├── Non Autenticato? ──► Reindirizzamento a Google OAuth2 (auth.pindaroli.org)
         └── Autenticato?
                 ├── Email in allowed.txt? ──► 200 OK + Cookie Sessione (.pindaroli.org) ──► Homepage (default/homepage:3000)
                 └── Email NON in allowed.txt? ──► 403 Forbidden
```

### Componenti Coinvolti:
1. **Google Cloud Console**: Gestisce l'OAuth 2.0 Client ID e la schermata di consenso OAuth (OAuth Consent Screen). Se l'app è in stato *"Testing"*, richiede l'autorizzazione esplicita dell'email nei *Test Users*.
2. **Kubernetes ConfigMap `allowed-emails`** (`namespace: oauth2-proxy`): Contiene il file `allowed.txt` con la lista delle email abilitate (attualmente solo `o.pindaro@gmail.com`).
3. **Deployment `oauth2-proxy`** (`namespace: oauth2-proxy`): Servizio che valida il token Google e verifica la presenza dell'indirizzo in `allowed.txt`.
4. **Traefik ForwardAuth Middleware** (`namespace: traefik`, nome `oauth2-auth`): Intercetta ogni richiesta HTTPS per `home.pindaroli.org` e la valida tramite `oauth2-proxy`.

---

## 2. Prerequisiti Informativi

Prima di procedere all'esecuzione, è necessario definire:
- [ ] **Indirizzo Email del Nuovo Utente**: Indirizzo Google (`@gmail.com` o Google Workspace).
- [ ] **Tipo di Dominio**:
  - Se `@gmail.com`: pienamente supportato dalla configurazione corrente (`--email-domain=gmail.com`).
  - Se dominio custom (es. `@azienda.com` o Google Workspace): richiede l'adeguamento del parametro `--email-domain` in `oauth2-proxy-complete.yaml` (es. `--email-domain=*` o aggiunta del dominio).

---

## 3. Fasi Operative

### Fase 1: Abilitazione su Google Cloud Console (Test Users)
Se l'app OAuth 2.0 è configurata in modalità **Testing** (comune per progetti personali e homelab):
1. Accedere a [Google Cloud Console](https://console.cloud.google.com/) con l'account amministratore (`o.pindaro@gmail.com`).
2. Selezionare il progetto associato a `pindaroli.org`.
3. Navigare in **APIs & Services** > **OAuth consent screen** (Schermata consenso OAuth).
4. Nella sezione **Test users** (Utenti di test), fare clic su **ADD USERS**.
5. Inserire l'indirizzo email del nuovo utente e salvare.
*(Se l'app è già in stato "In produzione" o verificata, questo passaggio non è necessario).*

---

### Fase 2: Aggiornamento Dichiarativo del ConfigMap `allowed-emails`
1. Modificare il manifest `oauth2-proxy/oauth2-proxy-complete.yaml` aggiungendo la nuova email nel blocco ConfigMap:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: allowed-emails
     namespace: oauth2-proxy
   data:
     allowed.txt: |
       o.pindaro@gmail.com
       <nuova-email>@gmail.com
   ```
2. *(Opzionale - se l'email non è `@gmail.com`)*: Aggiornare gli argomenti di deployment per permettere domini addizionali:
   ```yaml
   args:
     - --provider=google
     - --email-domain=*
     - --authenticated-emails-file=/emails/allowed.txt
   ```

---

### Fase 3: Applicazione su Kubernetes e Rollout Restart
Eseguire l'aggiornamento e il riavvio controllato di `oauth2-proxy`:
1. **Applicazione ConfigMap**:
   ```bash
   kubectl apply -f oauth2-proxy/oauth2-proxy-complete.yaml
   ```
2. **Rollout Restart del Deployment**:
   ```bash
   kubectl rollout restart deployment/oauth2-proxy -n oauth2-proxy
   ```
3. **Verifica dello Stato del Pod**:
   ```bash
   kubectl rollout status deployment/oauth2-proxy -n oauth2-proxy
   ```
4. **Ispezione dei Log di Avvio**:
   ```bash
   kubectl logs -l app=oauth2-proxy -n oauth2-proxy --tail=30
   ```

---

### Fase 4: Validazione Test-Driven End-to-End
1. **Test Login Nuovo Utente**:
   - Aprire una finestra di navigazione in incognito.
   - Accedere a `https://home.pindaroli.org`.
   - Verificare il redirect su `https://auth.pindaroli.org/oauth2/start?rd=https://home.pindaroli.org`.
   - Eseguire il login con le credenziali del nuovo account Google.
   - Verificare che il browser venga reindirizzato con successo su `https://home.pindaroli.org` e che la dashboard sia visibile e funzionante.
2. **Test Negativo (Anti-Discrepanza)**:
   - Tentare il login con un account Google terzo NON presente in `allowed.txt`.
   - Verificare che venga restituito l'errore `403 Forbidden` (o `403: access_denied` da Google se in testing mode).

---

## 4. Considerazioni di Sicurezza & Perimetro dei Servizi

> [!WARNING]
> **Dominio del Cookie OAuth2**:
> Il cookie di sessione generato da `oauth2-proxy` è emesso per il dominio wildcard `--cookie-domain=.pindaroli.org`.
> Questo significa che il nuovo utente autenticato avrà una sessione valida anche per **tutti gli altri IngressRoute esterni protetti dal middleware `oauth2-auth`** (ad esempio `jellyfin.pindaroli.org`, `nas.pindaroli.org`, `pve.pindaroli.org`, `radarr.pindaroli.org`, ecc.).
>
> **Nota sui singoli servizi**:
> - Servizi con autenticazione propria (TrueNAS, Proxmox, Jellyfin, OPNsense): l'utente supererà il proxy OAuth2 ma dovrà comunque autenticarsi con username e password interni all'applicazione.
> - Servizi senza autenticazione propria a valle di OAuth2: saranno direttamente accessibili dall'utente.
>
> Se si desidera circoscrivere l'accesso del nuovo utente **esclusivamente ad Homepage**, sarà necessario definire una middleware ForwardAuth o un'istanza OAuth2-Proxy dedicata con cookie ristretto a `home.pindaroli.org`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 0 (Pianificazione e Raccolta Requisiti)
- **Ultima Azione Completata**: Stesura del piano operativo strutturato in `wiki/plans/aggiunta-utente-esterno-home-oauth2.md`
- **Prossimo Passo Operativo**: Acquisizione dell'indirizzo email del nuovo utente e conferma se l'accesso debba essere esteso a tutti i servizi `*.pindaroli.org` o ristretto solo ad Homepage
- **Blocchi/Decisioni Pendenti**: In attesa di approvazione del piano e dettagli dell'utente da parte dell'operatore
