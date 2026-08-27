Se l'interfaccia dell'applicazione non mostra il riquadro speciale del documento, ti riporto qui di seguito l'intero **Piano di Implementazione Semplificato per MCP Hub su Kubernetes** direttamente in testo standard, così potrai leggerlo, copiarlo o salvarlo senza problemi.

---

# Valutazione Architetturale e Piano di Implementazione Semplificato per MCP Hub su Kubernetes

## Visione Architetturale Semplificata (Streamable HTTP + Micro-Pod)

A seguito della rivalutazione dei requisiti e della riduzione della complessità infrastrutturale per l'ambiente Homelab, l'architettura target abbandona il modello legacy basato su Server-Sent Events (SSE) e la gestione dello stato distribuito tramite Redis/Valkey.

La nuova architettura si fonda su due pilastri essenziali:

1. **Trasporto Streamable HTTP**: Transizione completa a transazioni HTTP stateless dirette per l'esecuzione dei comandi JSON-RPC. Questa scelta elimina la necessità di mantenere stream TCP a lungo termine, rendendo superfluo il bus di messaggistica Redis Pub/Sub ed eliminando i problemi di buffering dell'Ingress Controller.


2. **Isolamento dei Runtime (Micro-Pod)**: Scissione del Pod multi-container originario in due Deployment distinti ed indipendenti: uno dedicato ai servizi Python FastMCP ed uno agli scraper Node.js. Ciò garantisce un isolamento perfetto dei guasti ed evita che picchi di memoria o errori di scraping impattino i servizi di gestione del lab.

L'adozione di questa combinazione rende superflua l'introduzione di Kubernetes Gateway API o di controller/gateway MCP dedicati (come Microsoft MCP Gateway o Kong), consentendo di sfruttare appieno l'infrastruttura Traefik già presente nel cluster Talos Linux (pienamente compatibile out-of-the-box con la versione **v3.6.14** in uso).

---

## Dettaglio della Topologia Target

### 1. Risorse di Computazione (Deployment Separati)

* **`homelab-mcp-python`**: Deployment gestito per le funzionalità core del lab (`arrstack-mcp`, `truenas-mcp`, `opnsense-mcp`, `talos-mcp`). Esegue il runtime FastMCP in modalità Streamable HTTP sulla porta `:8001` con un'impronta di memoria stimata in ~50 MB RAM.
* **`homelab-mcp-scrapers`**: Deployment dedicato agli scraper web (Subito, Vinted, Wallapop). Esegue il runtime Node.js in modalità Streamable HTTP sulla porta `:8002` con un'impronta di memoria stimata in ~60 MB RAM.

### 2. Ingress & Routing (Traefik v3.6.14)

Il routing viene gestito nativamente tramite due risorse standard `IngressRoute` di Traefik, senza bisogno di middleware per il disattivamento del buffering o configurazioni custom di idle timeout:

* `[https://mcp.pindaroli.org/lab](https://mcp.pindaroli.org/lab)` -> Inoltra al servizio `homelab-mcp-python`
* `[https://mcp.pindaroli.org/scrapers](https://mcp.pindaroli.org/scrapers)` -> Inoltra al servizio `homelab-mcp-scrapers`

---

## Piano di Implementazione Operativo

Il seguente piano operativo riduce le fasi di configurazione ed azzera le dipendenze esterne.

| Fase | Attività Operativa | Componenti Coinvolti | Output e Criteri di Verifica |
| --- | --- | --- | --- |
| **Fase 1: Adattamento Applicativo** | Riconfigurare i server FastMCP (Python) e Node.js per esporre gli endpoint in modalità **Streamable HTTP** su percorsi stabili (`/lab` e `/scrapers`) anziché transport SSE.

 | Codice sorgente Python FastMCP & Node.js | I server rispondono correttamente a chiamate HTTP POST/GET su endpoint locali di test.

 |
| **Fase 2: Containerizzazione** | Creazione di due `Dockerfile` separati ed ottimizzati per ciascun runtime. Generazione e push delle immagini sul container registry. | Docker, Registry Locale / GHCR | Immagini `homelab-mcp-python:v1` e `homelab-mcp-scrapers:v1` pronte ed isolate. |
| **Fase 3: Deploy Micro-Pod** | Creazione delle risorse Kubernetes `Deployment` e `Service` distinte nel namespace `mcp-system`. Iniezione dei Secret per le credenziali del lab. | Manifesti YAML Kubernetes (`Deployment`, `Service`, `Secret`) | Pod `mcp-python` e `mcp-scrapers` attivi ed in stato `Running` in namespace dedicato. |
| **Fase 4: Configurazione Ingress** | Creazione della risorsa Traefik `IngressRoute` con terminazione TLS (Let's Encrypt / Cert-Manager) e routing basato sui prefissi di path `/lab` e `/scrapers`. | Traefik `IngressRoute` (v3.6.14) | Gli endpoint esterni `[https://mcp.pindaroli.org/lab](https://mcp.pindaroli.org/lab)` e `/scrapers` rispondono correttamente. |
| **Fase 5: Autoscaling (HPA)** | Applicazione dell'HorizontalPodAutoscaler calibrato sulle risorse dei singoli deployment (target RAM/CPU standard). | K8s `HorizontalPodAutoscaler` | Scalabilità orizzontale trasparente da 1 a N repliche gestita da K8s. |
| **Fase 6: Migrazione Client AI** | Aggiornamento dei file di configurazione (`mcp_config.json`) di Antigravity, Hermes Agent e client remoti con i nuovi URL Streamable HTTP. | Antigravity, Hermes Agent, Bot Telegram | Esecuzione riuscita dei comandi e dei workflow dagli agenti AI senza disconnessioni. |

---

## Matrice Comparativa: Piano Originario vs Piano Semplificato Target

| Indicatore | Piano Originario (Multi-Container + SSE + Redis) | Nuovo Piano Target (Micro-Pod + Streamable HTTP) |
| --- | --- | --- |
| **Componenti Infrastrutturali** | Pod Multi-Container, Traefik, Redis/Valkey Cluster | 2 Deployment Micro-Pod, Traefik Ingress Standard |
| **Gestione dello Stato** | Distribuita via Redis Pub/Sub | **100% Stateless** nativa su HTTP

 |
| **Isolamento dei Guasti** | Basso (Crash del container Node riavvia il Pod condiviso) | **Elevato** (I deployment sono completamente indipendenti) |
| **Complessità Ingress/Proxy** | Elevata (Buffering OFF, Timeout estesi, gestione SSE) | **Minima** (Routing HTTP standard senza tuning custom su Traefik 3.6.14) |
| **Dipendenze Esterne** | Database Redis per la sincronizzazione eventi | **Nessuna**<br> |
| **Manutenzione Homelab** | Media (Rischio disallineamento Redis/SSE) | **Bassissima** (Pila software minimale e standard) |