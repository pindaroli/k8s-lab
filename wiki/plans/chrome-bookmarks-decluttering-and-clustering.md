---
title: Piano di Decluttering e Clusterizzazione Tassonomica dei Segnalibri Chrome
status: active
certified_for_ai: true
author: Gemini
created_at: 2026-10-13
category: operational_plan
tags:
  - chrome
  - bookmarks
  - decluttering
  - taxonomy
  - mcp
---

# Piano di Decluttering e Clusterizzazione Tassonomica dei Segnalibri Chrome

> [!IMPORTANT]
> **Current Status**: **FASE 1 (PIANIFICAZIONE & APPROVAZIONE UTENTE)**  
> **Contesto**: Google Chrome Profile 5 (`o.pindaro@gmail.com`).  
> **Obiettivo**: Ristrutturare i 237 segnalibri rimanenti attraverso decluttering semantico, bonifica dei duplicati (29 copie da vecchi import) e posizionamento prioritario dei **Top 10 Daily Drivers** direttamente alla radice della Barra dei Preferiti (`Bookmarks Bar`).

---

## 1. Architettura & Requisiti Fondamentali

1. **Top 10 Link Diretti (Indici 0..9 sulla Barra dei Preferiti):**
   I primi 10 slot devono essere dedicati ai servizi homelab ad uso quotidiano più frequente:
   - `[0]` **Homepage K8s**: `https://home-internal.pindaroli.org/`
   - `[1]` **Homepage TrueNAS**: `http://10.10.20.50:3000/`
   - `[2]` **OPNsense Firewall**: `https://10.10.20.254/`
   - `[3]` **Proxmox PVE1**: `https://10.10.10.11:8006/`
   - `[4]` **Proxmox PVE2**: `https://10.10.10.21:8006/`
   - `[5]` **Proxmox PVE3**: `https://10.10.10.31:8006/`
   - `[6]` **TrueNAS SCALE**: `https://10.10.10.50/`
   - `[7]` **PBS Backup**: `http://10.10.10.100:8007/`
   - `[8]` **Grafana**: `https://grafana-internal.pindaroli.org/`
   - `[9]` **Jellyfin**: `https://jellyfin.pindaroli.org/`

2. **Bonifica Duplicati (Decluttering):**
   Eliminazione di 29 link ridondanti generati da vecchie cartelle importate:
   - `Bookmarks Bar / Imported / Homelab Pindaroli / ...`
   - `Bookmarks Bar / Imported (1) / Homelab Pindaroli / ...`

3. **Alberatura Tematica (7 Cartelle Principali sulla Barra):**
   - 📁 **1. Homelab & Infrastruttura** (`Direct Management`, `Servizi Web & Media`)
   - 📁 **2. AI & LLM Ecosystem** (`Tool & API`, `Model Context Protocol (MCP)`, `Corsi & Mastermind`)
   - 📁 **3. Kubernetes & DevOps** (`CKAD & Lab`, `Architettura & GitOps`)
   - 📁 **4. Cloud Architecture** (`Google Cloud`, `OCI`)
   - 📁 **5. Hardware & Audio** (`Casse Hi-Fi KEF`, `Modem 5G ZTE`, `Surplus & Switch`)
   - 📁 **6. PA, Scuola & Professionale** (`POLIS MIUR`, `Graduatorie`, `PA`)
   - 📁 **7. Shopping, Casa & Personale** (`Shopping`, `Casa & Arredo`)
   - 📁 *(In Other Bookmarks)*: **8. Archivio Storico & Reference**

---

## 2. Fasi Operative

### Fase 1: Progettazione Tassonomia e Approvazione Utente (Completata ✅)
- Censimento dei 237 nodi e mappatura in 208 URL univoci.
- Generazione dell'artefatto di dettaglio: [chrome_bookmarks_decluttering_plan.md](file:///Users/olindo/.gemini/antigravity/brain/a1655fc2-584d-4853-b1be-9a400ce070b5/chrome_bookmarks_decluttering_plan.md).
- Approvazione utente ricevuta con direttiva di escludere l'estrazione dei 10 link diretti (Punto 1) e mantenere sulla barra i 2 collegamenti `Homepage` e `homepage-truenas`, seguiti immediatamente dalle 7 cartelle tematiche create dal Punto 2.

### Fase 2: Creazione delle Cartelle Strutturali via MCP (Completata ✅)
- Creazione delle 7 cartelle radice su `Bookmarks Bar` (ID `590`):
  - `[1323]` 📁 **Homelab & Infrastruttura**
  - `[1324]` 📁 **AI & LLM Ecosystem**
  - `[1325]` 📁 **Kubernetes & DevOps**
  - `[1326]` 📁 **Cloud Architecture**
  - `[1327]` 📁 **Hardware & Audio**
  - `[1328]` 📁 **PA, Scuola & Professionale**
  - `[1329]` 📁 **Shopping, Casa & Personale**
- Creazione della cartella archivio su `Other Bookmarks` (ID `591`):
  - `[1330]` 📁 **Archivio Storico & Reference**
- Creazione delle 15 sottocartelle tematiche dedicate (`1331`..`1345`).

### Fase 3: Spostamento & Ricollocazione dei Segnalibri (Completata ✅)
- Spostamento atomico di tutti i 207 segnalibri candidati nelle rispettive nuove cartelle tramite chiamate MCP `bookmarks_move`.
- Mantenimento all'indice 0 di `Homepage` e all'indice 1 di `homepage-truenas`.

### Fase 4: Bonifica Cartelle Obsolete & Duplicati (Completata ✅)
- Rimozione sicura delle vecchie cartelle legacy svuotate su `Bookmarks Bar` (`ai`, `devops`, `home`, `Surplus Elettronico e Networking`, `Nuova cartella`, `Diso`, `p2p`, `job`) e `Other Bookmarks` (`Soluzione giochi`) tramite `bookmarks_remove_tree`.
- Zero perdite di dati: 209 segnalibri attuali preservati al 100%.

### Fase 5: Validazione Test-Driven & Rigenerazione Indici (Completata ✅)
- Verifica live dello stato dell'albero dei preferiti: confermati 209 segnalibri attivi su Chrome e salvati su disco.
- Creazione backup post-ristrutturazione: `backups/chrome-bookmarks/Bookmarks_Profile5_post_restructure_20261013_182750.json`.
- Rigenerazione degli artefatti cronologici: [chrome_bookmarks_chronological.md](file:///Users/olindo/.gemini/antigravity/brain/a1655fc2-584d-4853-b1be-9a400ce070b5/chrome_bookmarks_chronological.md) e [chrome_bookmarks_chronological_overview.md](file:///Users/olindo/.gemini/antigravity/brain/a1655fc2-584d-4853-b1be-9a400ce070b5/chrome_bookmarks_chronological_overview.md).

### Fase 6: Bonifica Link Morti (404/DNS) & Vecchi IP LAN Dismessi (Completata ✅)
- Diagnostica concorrente su tutti i 209 link: identificati 11 link web morti (404, DNS NXDOMAIN, portali chiusi) e 6 vecchi IP/hostname LAN dismessi pre-migrazione.
- Eliminazione atomica dei 17 link non funzionanti via MCP `bookmarks_remove`.
- Conteggio finale ridotto da 209 a **192 segnalibri validi**.
- Verifica cartelle vuote: nessuna cartella utente svuotata (tutte mantengono link validi).
- Backup post-bonifica: `backups/chrome-bookmarks/Bookmarks_Profile5_post_deadlinks_cleanup_20261013_184803.json`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Bonifica di 17 link morti e vecchi IP; totale finale a 192 segnalibri attivi e funzionanti su Chrome.
- **Prossimo Passo Operativo**: Nessuno, segnalibri perfettamente declutterati, organizzati e privi di link rotti.
- **Blocchi/Decisioni Pendenti**: Nessuno.


