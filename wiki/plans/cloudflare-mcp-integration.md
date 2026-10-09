---
title: "Piano: Integrazione MCP Server Cloudflare (SaaS Ufficiale)"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-09
tags:
  - "#plan"
  - "#mcp"
  - "#cloudflare"
  - "#saas"
  - "#dns"
---

# Piano: Integrazione MCP Server Cloudflare (SaaS Ufficiale)

Questo piano definisce l'integrazione del server Model Context Protocol (**MCP**) ufficiale di Cloudflare (`https://mcp.cloudflare.com/mcp`) come provider SaaS gestito in `~/.gemini/antigravity/mcp_config.json`, in conformità alle policy homelab e ai principi di [[MCP_Platform]].

---

## 🎯 Obiettivo Architetturale

1. **Adozione Endpoint Ufficiale SaaS (`https://mcp.cloudflare.com/mcp`)**: Sfruttare la tecnologia nativa **Code Mode** di Cloudflare per accedere a oltre 2.500 endpoint API (DNS, Zone, Cloudflare Tunnel, Zero Trust, WAF, Workers) con un costo di contesto minimo (~1.100 token) e zero overhead di risorse hardware locali (0 MB RAM / 0 CPU).
2. **Autenticazione Sicura**: Utilizzo di un Cloudflare User API Token dedicato (`cfut_...`) archiviato in modo sicuro in SOPS (`secrets-sops/cloudflare-mcp-credentials.enc.yaml`) e proiettato in `~/.gemini/antigravity/mcp_config.json`.
3. **Piena Integrazione con l'Homelab**: Consentire all'agente Antigravity la gestione, ispezione e troubleshooting declarativo del dominio `pindaroli.org`, record DNS e tunnel `cloudflared`.

---

## 🗺️ Matrice Architetturale Server MCP

| Server MCP | Provider / Runtime | Transport | URL Endpoint | Auth Header | Ruolo Primario |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`cloudflare`** | SaaS Ufficiale Cloudflare | Streamable HTTP | `https://mcp.cloudflare.com/mcp` | `Bearer cfut_...` | Gestione DNS `pindaroli.org`, Tunnels, Zone & Zero Trust |

---

## 📋 Fasi Operative

### FASE 1: Generazione & Validazione Token API Cloudflare
- [x] Generazione User API Token (`cfut_...`) su Cloudflare Dashboard con permessi `User Details: Read`, `Account Settings: Read`, `Zone: Read`, `DNS: Edit`.
- [x] Test di validazione connettività e verifica token (`/client/v4/user/tokens/verify`) completato con esito `active`.

### FASE 2: Archiviazione Sicura Secret via SOPS
- [x] Creazione del manifesto secret cifrato `secrets-sops/cloudflare-mcp-credentials.enc.yaml`.
- [x] Test di decifratura e coerenza Age (`sops -d`) superato con successo.

### FASE 3: Configurazione Centralizzata MCP Client
- [x] Aggiornamento di `~/.gemini/antigravity/mcp_config.json` con la voce `"cloudflare"` (`serverUrl` + header `Authorization: Bearer cfut_...`).
- [x] Verifica formattazione JSON e validazione schema (`json.tool` OK).

### FASE 4: Validazione Test-Driven End-to-End
- [x] Esecuzione handshake MCP JSON-RPC (`initialize`, `tools/list`) verso `https://mcp.cloudflare.com/mcp` con codice 200 OK.
- [x] Smoke test `whoami`: autenticazione confermata per `o.pindaro@gmail.com` (`user:11123dc9a28ef4bf40d4a5fb1a6233f7`).
- [x] Smoke test `execute`: lettura confermata della zona `pindaroli.org` (`e05352b0ab4ba627604859f84ebbdf80`) e record DNS reali.

### FASE 5: Consolidamento Documentale & Knowledge Base
- [x] Aggiornamento di [[MCP_Platform]] con il nuovo server SaaS.
- [x] Aggiornamento di `todo.md` e indice `GEMINI.md`.
- [x] Ricompilazione automatica del contesto wiki (`python3 scripts/wiki/build_wiki_context.py`).

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Completato ✅
- **Ultima Azione Completata**: Fase 1-5 completate, test end-to-end superati e documentazione consolidata
- **Prossimo Passo Operativo**: Nessuno (Servizio operativo e pronto all'uso)
- **Blocchi/Decisioni Pendenti**: Nessuno
