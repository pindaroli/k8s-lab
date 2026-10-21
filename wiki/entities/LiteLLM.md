---
title: "LiteLLM (AI Inference Gateway & Router)"
last_updated: "2026-10-21"
confidence: "High"
tags:
  - "#litellm"
  - "#ollama"
  - "#hermes"
  - "#kubernetes"
  - "#helm"
  - "#traefik"
  - "#cnpg"
provenance:
  - "litellm/litellm-values.yaml"
  - "wiki/plans/litellm-proxy-kubernetes-deployment.md"
---

# LiteLLM (LLM Inference Gateway & High-Availability Router)

**LiteLLM Proxy** è il gateway di inferenza e load balancer LLM centralizzato del cluster `k8s-lab`. Fornisce un'interfaccia compatibile con le OpenAI API (`/v1/chat/completions`, `/v1/models`, `/v1/embeddings`) con routing ad alta disponibilità e prioritario tra i server Ollama fisici del lab: Mac Studio (`olindo-macstudio.pindaroli.org:11434`, Metal 64GB) e `lxc-ollama` (`lxc-ollama.pindaroli.org:11434`, PVE3 Radeon 890M).

---

## 1. Dettagli di Deployment & Architettura
- **Namespace**: `litellm`.
- **Chart Ufficiale Upstream**: `oci://ghcr.io/berriai/litellm-helm` versione `1.106.2`.
- **Immagine**: `ghcr.io/berriai/litellm:1.106.2` (con Prisma CLI e schema migration bundlati).
- **File Valori Dichiarativo**: [`litellm/litellm-values.yaml`](file:///Users/olindo/prj/k8s-lab/litellm/litellm-values.yaml).
- **CoreDNS Interno**: `http://litellm.litellm.svc.cluster.local:4000/`.
- **Esposizione LAN / IngressRoute**: `https://litellm-internal.pindaroli.org/` (Traefik VIP `10.10.20.56`, TLS Wildcard `pindaroli-wildcard-tls`).
- **Admin Console**: `https://litellm-internal.pindaroli.org/ui`.
- **Affinity**: Programmato esclusivamente su nodi control-plane ad alta capacità (`talos-cp-01` e `talos-cp-02`), escludendo `talos-cp-03` (4 GB RAM vincolati).

---

## 2. Persistenza & Database (CloudNativePG)
- **Cluster PostgreSQL**: `postgres-main` (`postgres-main-rw.cnpg-system.svc.cluster.local:5432`) in namespace `cnpg-system`.
- **Database & Ruolo Dedicato**: `litellm` gestito da CNPG CRD (`Database` e `managed.roles` in `postgres/cluster.yaml`).
- **Segreti (SOPS)**:
  - `secrets-sops/litellm-db-password.enc.yaml` (namespace `cnpg-system`).
  - `secrets-sops/litellm-secrets.enc.yaml` (namespace `litellm`, contiene master key, salt key, UI password e virtual key Hermes).

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
