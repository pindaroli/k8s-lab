---
title: "LiteLLM (AI Inference Gateway & Router)"
last_updated: "2026-10-22"
confidence: "High"
tags:
  - "#litellm"
  - "#ollama"
  - "#hermes"
  - "#docker"
  - "#truenas"
provenance:
  - "servarr/truenas-docker/docker-compose.yaml"
  - "servarr/truenas-docker/litellm/config.yaml"
  - "wiki/plans/hermes-agent-truenas-docker-migration.md"
---

# LiteLLM (LLM Inference Gateway & High-Availability Router)

**LiteLLM Proxy** è il gateway di inferenza e load balancer LLM centralizzato del lab. È in esecuzione come container Docker su **TrueNAS SCALE** (`10.10.20.50:4000`), integrato nello stack `servarr/truenas-docker/docker-compose.yaml`. Fornisce un'interfaccia compatibile con le OpenAI API (`/v1/chat/completions`, `/v1/models`, `/v1/embeddings`) con routing ad alta disponibilità e prioritario tra i server Ollama fisici del lab: Mac Studio (`olindo-macstudio.pindaroli.org:11434`, Metal 64GB) e `lxc-ollama` (`lxc-ollama.pindaroli.org:11434`, PVE3 Radeon 890M).

---

## 1. Dettagli di Deployment & Architettura
- **Piattaforma**: Docker su TrueNAS SCALE Bare Metal (`10.10.20.50`).
- **Stack Compose**: `servarr/truenas-docker/docker-compose.yaml` (root `/mnt/stripe/truenas-docker/`).
- **Immagine**: `ghcr.io/berriai/litellm:1.106.2` (con Prisma CLI e schema migration bundlati).
- **File Configurazione**: versionato in `servarr/truenas-docker/litellm/config.yaml` e montato `:ro` in `/app/config.yaml`.
- **Rete Interna Docker**: raggiungibile dai container locali (es. Hermes Agent) all'URL `http://litellm:4000/v1`.
- **Esposizione LAN**: `http://10.10.20.50:4000/` (Admin UI: `http://10.10.20.50:4000/ui`). Servizio esclusivamente interno, senza Ingress/Traefik.

---

## 2. Persistenza & Database Dedicato (litellm-postgres)
- **Container Database**: `postgres:16-alpine` dedicato (`container_name: litellm-postgres`), non esposto sull'host, comunicante via DNS Docker `litellm-postgres:5432`.
- **Dataset ZFS**: dataset ZFS dedicato `/mnt/stripe/truenas-docker/litellm-postgres` con `recordsize=8k`, permessi `700` e ownership `999:999` (utente Postgres).
- **Segreti (SOPS → .env)**: credenziali estratte da `secrets-sops/litellm-secrets.enc.yaml` e `litellm-db-password.enc.yaml` nel file runtime protetto `/mnt/stripe/truenas-docker/.env` (permessi `600`).
- **Virtual Key Hermes**: ricreata in modo deterministico via API (`POST /key/generate`) per l'utente `hermes-agent`.

---

## 3. Modelli & Logica di Routing (Fallback & Priorità)

Insieme standard di 5 modelli con routing prioritario (Order 1: Mac Studio; Order 2: fallback automatico su `lxc-ollama`):

| Alias LiteLLM | Primario (Order 1, Mac Studio) | Fallback (Order 2, `lxc-ollama`) | Tipologia |
|---|---|---|---|
| `big-chat` | `ollama_chat/qwen2.5:32b-instruct-q5_K_M` | `ollama_chat/qwen2.5:32b-instruct-q5_K_M` | Chat / Reasoning |
| `big-alt` | `ollama_chat/gemma4:31b` | `ollama_chat/gemma4:31b` | Chat / Multimodale |
| `vision` | `ollama_chat/qwen3-vl:32b` | `ollama_chat/qwen3-vl:32b` | Vision 32B |
| `vision-light` | `ollama_chat/qwen2.5vl:7b-q4_K_M` | `ollama_chat/qwen2.5vl:7b-q4_K_M` | Vision leggera |
| `embed` | – | `ollama/bge-m3:latest` | Embedding vettoriale |

### Strategia di Cooldown & Failover
- `routing_strategy: simple-shuffle` con `enable_pre_call_checks: true`.
- `timeout: 5`, `stream_timeout: 10`, `allowed_fails: 1`, `cooldown_time: 60`.
- Quando il Mac Studio è spento o non risponde entro il timeout, LiteLLM devia istantaneamente le chiamate su `lxc-ollama` e mantiene il cooldown di 60 secondi prima di ri-testare il Mac.

---

## 4. Integrazione Hermes Agent
- Hermes Agent (`namespace: hermes`) è configurato esclusivamente con provider `litellm` puntando a `http://litellm.litellm.svc.cluster.local:4000/v1`.
- Virtual Key riproducibile pre-generata e sincronizzata automaticamente tramite Job Helm post-install/post-upgrade (`litellm-sync-hermes-key`).
- `LITELLM_API_KEY` montata tramite Secret `hermes-secrets` (crittografato in SOPS).

---

## 5. Eccezione GitOps RAGFlow
- **RAGFlow non è instradato tramite LiteLLM** per preservare l'integrità del database preesistente `rag_flow`. RAGFlow continua a interrogare direttamente `http://10.10.20.100:11434` per embedding `bge-m3:latest` e chat `gpt-4o:latest`.
