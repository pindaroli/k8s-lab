# Checklist Operativa: Onboarding MCP Server su K8s

Questa checklist deve essere verificata punto per punto prima di considerare concluso l'onboarding di un nuovo server MCP.

---

## 📋 1. Pre-Flight & Selezione Pattern
- [ ] Il tipo di sorgente è stato verificato (npm, PyPI, o Git upstream).
- [ ] È stata ricercata l'**ultima release stabile ufficiale** (nessun uso di `latest`).
- [ ] È stata verificata l'eventuale ambiguità di versione o assenza di tag (con fallback mono-branch + warning all'utente o richiesta esplicita).
- [ ] È stato scelto il pattern corretto (`mcp-registry-package-pattern` o `mcp-upstream-tracking-pattern`).

## 🐳 2. Containerizzazione & Hardening Monorepo
- [ ] La cartella `docker/<app>/` contiene il `Dockerfile` standardizzato.
- [ ] È presente `ARG <PKG>_VERSION` o `ARG UPSTREAM_REF` esplicito.
- [ ] Viene rilasciato l'accesso root impostando `USER node` (UID 1000) o `USER appuser` (UID 1000).
- [ ] È verificata la piena compatibilità con `securityContext.readOnlyRootFilesystem: true` (nessuna scrittura su disco tranne `/tmp`).
- [ ] È presente il workflow `.github/workflows/docker-<app>.yml` con path filter selettivo e buildx `linux/amd64`.
- [ ] L'immagine è compilata e pubblicata su `ghcr.io/pindaroli/<app>:<version>` con tag semantico fisso.

## 🔐 3. Gestione Credenziali (SOPS)
- [ ] Se presenti stringhe scalari (token/password), sono cifrate in `secrets-sops/` e collegate a ToolHive `spec.secrets`.
- [ ] Se presenti file complessi o mTLS, sono montati come volume read-only in `/etc/<app>/` senza estrazione scriptata a runtime.

## ☸️ 4. Integrazione GitOps (mcp-gateway)
- [ ] Il blocco del server è aggiunto alla lista `servers` in `mcp-gateway/mcp-gateway-values.yaml`.
- [ ] L'immagine fa riferimento al tag semantico fisso (es. `:1.0.0`), **NON** a `:latest`.
- [ ] Sono impostati limiti e richieste di risorse (default `requests: 50m/64Mi`, `limits: 300m/256Mi`).
- [ ] È stato incrementato il versionamento SemVer in `helm-charts/mcp-gateway/Chart.yaml`.
- [ ] È stato eseguito `helm upgrade mcp-gateway helm-charts/mcp-gateway -f mcp-gateway/mcp-gateway-values.yaml -n mcp-system`.
- [ ] I pod StatefulSet (`<app>-mcp-0`) e proxy runner (`mcp-<app>-mcp-proxy`) sono in stato `Running`.

## 🌐 5. Networking & DNS
- [ ] È stato registrato l'Host Override su OPNsense Unbound (`<app>-mcp-internal.pindaroli.org` -> `10.10.20.56`).
- [ ] È stato eseguito `python3 scripts/network/validate_network.py` con esito 100% positivo.

## 💻 6. Integrazione Client Antigravity
- [ ] Il server è censito in `~/.gemini/antigravity/mcp_config.json` con `serverUrl: https://<app>-mcp-internal.pindaroli.org/mcp`.
- [ ] È stato eseguito un test reale (chiamata di un tool esposto) con esito positivo.

## 📚 7. Wiki & Tracciabilità
- [ ] Aggiornata la tabella in `wiki/entities/MCP_Platform.md`.
- [ ] Aggiornato l'elenco `in_use_by` nel pattern utilizzato.
- [ ] Eseguito `python3 scripts/wiki/build_wiki_context.py` per rigenerare il contesto LLM.
