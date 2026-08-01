---
status: active
certified_for_ai: true
---

# Piano: Implementazione Gestione Scaling su Homepage Local via OliveTin (Iframe)

## Obiettivo
Fornire un'interfaccia robusta e nativa per accendere e spegnere le applicazioni del cluster (es. Radarr, Sonarr) dalla dashboard `homepage-local`. Al posto di hack Javascript o link grezzi, utilizzeremo **OliveTin** (un tool web leggero per l'esecuzione di script/comandi predefiniti) integrato direttamente nella Homepage tramite un **Iframe Widget**.

## Dettagli Architetturali
- **Frontend (Homepage)**: Utilizzo del widget `iframe` nativo di Homepage per incorporare la UI di OliveTin direttamente in un pannello dedicato della dashboard.
- **Middleware (OliveTin)**:
  - Deployment di un pod leggero per OliveTin nel cluster.
  - Configurazione (`config.yaml` tramite ConfigMap) per generare automaticamente i bottoni "Start" e "Stop" per ciascuna app.
  - Al click, OliveTin eseguirà una chiamata `curl` in background verso il webhook di `n8n`.
- **Backend (n8n)**:
  - Un workflow in n8n (attivato tramite Webhook HTTP POST).
  - Il manifesto RBAC (`n8n/rbac-n8n-scaler.yaml`) già configurato fornisce a n8n i permessi di eseguire patch sulle repliche dei deployment.

## Fasi Operative (To Do)
1. **Deployment OliveTin**:
   - Creare un manifest (Deployment + Service + Ingress/ConfigMap) per OliveTin in un namespace appropriato (es. `default` o `n8n`).
   - Definire i bottoni in `config.yaml` per invocare il webhook `n8n` per ogni app.
2. **Integrazione Homepage**:
   - Aggiungere il widget `iframe` nel `widgets.yaml` (o `services.yaml`) di `homepage-local` puntando all'URL interno/esterno di OliveTin.
3. **Workflow n8n**:
   - Creare e attivare il workflow su n8n in attesa dei payload generati da OliveTin (`app`, `action`/`replicas`).
4. **Collaudo**:
   - Riavvio dei pod e test end-to-end cliccando sui bottoni dentro l'iframe di Homepage.

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Congelato (Progetto in Pausa).
- **Ultima Azione Completata**: Stesura del piano per l'integrazione di OliveTin tramite Iframe.
- **Prossimo Passo Operativo**: Riprendere dalla Fase 1 (Deployment OliveTin) quando il task verrà sbloccato dal todo.
- **Blocchi/Decisioni Pendenti**: Il progetto è stato esplicitamente messo in pausa dall'utente in attesa di future priorità.
