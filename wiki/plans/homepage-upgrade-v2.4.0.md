---
title: "Aggiornamento Homepage v2.4.0 (K8s & Docker TrueNAS)"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-26
tags:
  - "#homepage"
  - "#upgrade"
  - "#k8s"
  - "#docker"
  - "#truenas"
  - "#mcp"
  - "#sops"
---

# Aggiornamento Homepage v2.4.0 (K8s & Docker TrueNAS)

Questo piano definisce la procedura operativa controllata e test-driven per:
1. **Dismissione e rimozione a monte** della vecchia implementazione di failover/Git Backup (`servarr/compose/`), non più utilizzata. *(Completata ✅)*
2. **Aggiornamento di tutte le istanze Homepage** alla versione stabile **v2.4.0** (`ghcr.io/gethomepage/homepage:v2.4.0`) su [[Talos_Cluster]] (Kubernetes) *(Completata ✅)* e su [[TrueNAS]] bare-metal (Docker Compose) *(Completata ✅)*.
3. **Abilitazione selettiva del protocollo MCP (Opzione 1 - Hardening)**:
   - **Abilitato** esclusivamente sui canali interni fidati: `homepage-local` (K8s) *(Verificato HTTP 200 con 7 tool MCP)* e `homepage` (Docker TrueNAS) *(Verificato HTTP 200 con 7 tool MCP)*.
   - **Disabilitato** sull'istanza esposta all'esterno (`homepage` su K8s / `home.pindaroli.org`) per minimizzare la superficie d'attacco.
4. **Sicurezza dei Segreti (SOPS + GitIgnore)**:
   - Secret K8s cifrato in `secrets-sops/homepage-mcp-credentials.enc.yaml` con Age.
   - Compose TrueNAS sanitizzato con `${HOMEPAGE_MCP_TOKEN}` caricato da `.env` protetto e non tracciato su Git.

---

## 🎯 Obiettivi & Perimetro
1. **Bonifica Preliminare (A Monte - FASE 0 - COMPLETATA ✅)**:
   - Rimozione completa dell'albero `servarr/compose/` (stack failover orfano/non usato).
2. **Kubernetes (`default` namespace - FASE 1 - COMPLETATA ✅)**:
   - Aggiornamento di `homepage` (`homepage/homepage.yaml`) esposta su `https://home.pindaroli.org` a `v2.4.0` con `HOMEPAGE_MCP_ENABLED: "false"`.
   - Aggiornamento di `homepage-local` (`homepage/homepage-local.yaml`) esposta su `https://home-internal.pindaroli.org` a `v2.4.0` con `HOMEPAGE_MCP_ENABLED: "true"` e iniezione del token di sicurezza `HOMEPAGE_MCP_TOKEN`.
   - Secret K8s cifrato con SOPS in `secrets-sops/homepage-mcp-credentials.enc.yaml` applicato al cluster.
3. **Docker Compose su TrueNAS (`10.10.20.50` - FASE 2 - COMPLETATA ✅)**:
   - Aggiornamento del servizio `homepage` nello stack principale `/mnt/stripe/truenas-docker/docker-compose.yaml` (dichiarativo in `servarr/truenas-docker/docker-compose.yaml`), esposto su `http://10.10.20.50:3000` con `HOMEPAGE_MCP_ENABLED=true` e `HOMEPAGE_MCP_TOKEN=${HOMEPAGE_MCP_TOKEN}` via `.env`.

---

## 🛡️ Modello di Sicurezza MCP & Gestione Segreti

| Componente | Storage Segreto | Metodo di Iniezione | Visibilità Git |
| :--- | :--- | :--- | :--- |
| **K8s Secret** | `secrets-sops/homepage-mcp-credentials.enc.yaml` | `secretKeyRef` nel Deployment | Cifrato SOPS (Age `age1x5pm...`) |
| **TrueNAS Docker** | `/mnt/stripe/truenas-docker/.env` | Interpolazione `${HOMEPAGE_MCP_TOKEN}` | Escluso via `.gitignore` (`.env.example` tracciato) |

---

## 📋 FASI OPERATIVE & PROTOCOLLO TEST-DRIVEN

### 🧹 FASE 0: Rimozione A Monte Implementazione Git Backup (Failover Compose) [COMPLETATA ✅]

#### Azioni
1. [x] Rimuovere l'intero albero orfano `servarr/compose/`:
   ```bash
   rm -rf servarr/compose/
   ```
2. [x] Verificare che non rimangano riferimenti pendenti in stato Git:
   ```bash
   git status --short servarr/
   ```

---

### ☸️ FASE 1: Aggiornamento Dichiarativo e Rollout su Kubernetes [COMPLETATA ✅]

#### Azioni
1. [x] Creazione manifest secret cifrato con SOPS in `secrets-sops/homepage-mcp-credentials.enc.yaml` e apply su `default`.
2. [x] Aggiornamento `homepage/homepage.yaml` (v2.4.0, MCP false).
3. [x] Aggiornamento `homepage/homepage-local.yaml` (v2.4.0, MCP true, `secretKeyRef`).
4. [x] Rollout restart e monitoraggio: `deployment/homepage` e `deployment/homepage-local`.
5. [x] Collaudo HTTP: internal 200 OK, external 302 OAuth2, probe MCP internal 200 JSON-RPC con 7 tool.

---

### 🐳 FASE 2: Aggiornamento Docker Compose su TrueNAS [COMPLETATA ✅]

#### Azioni
1. [x] Sanitizzazione `servarr/truenas-docker/docker-compose.yaml` con `${HOMEPAGE_MCP_TOKEN}` e creazione `.env.example`.
2. [x] Inserimento token in `/mnt/stripe/truenas-docker/.env` su TrueNAS bare-metal.
3. [x] Pre-pull immagine `ghcr.io/gethomepage/homepage:v2.4.0`.
4. [x] Sync compose ed esecuzione `docker compose up -d --force-recreate --no-deps homepage`.
5. [x] Collaudo: container `Up (healthy)`, HTTP :3000 200 OK, probe MCP POST 200 OK con 7 tool.

---

### 📚 FASE 3: Consolidamento Documentale & Chiusura [IN CORSO]

#### Azioni
1. [x] Aggiornare l'entità [[Homepage]] (`wiki/entities/Homepage.md`).
2. [x] Aggiornare `todo.md` marcando come completati i task del piano.
3. [ ] Eseguire validazione rete e compilazione contesto Wiki:
   ```bash
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```
4. [ ] Commit Git delle modifiche con messaggio semantico:
   ```bash
   git add homepage/ servarr/ secrets-sops/ wiki/ todo.md
   git commit -m "chore(homepage): upgrade to v2.4.0, enable mcp on internal channels, sops encryption, and purge obsolete compose failover"
   ```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 3 / Consolidamento Documentale & Chiusura
- **Ultima Azione Completata**: Bonifica di sicurezza completata: Secret SOPS `homepage-mcp-credentials.enc.yaml` creato, compose sanitizzato con `${HOMEPAGE_MCP_TOKEN}`, `.env` aggiornato su TrueNAS e container ricaricato con successo.
- **Prossimo Passo Operativo**: Esecuzione di `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py` e commit Git finale.
- **Blocchi/Decisioni Pendenti**: Nessuno.
