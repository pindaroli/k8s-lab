---
title: "Jellyfin Classic - Setup & Scelte di Configurazione"
last_updated: "2026-05-21"
confidence: "High"
tags:
  - "#jellyfin"
  - "#classical"
  - "#metadata"
provenance:
  - "dual-pipeline-gitops-integration.md"
---

# Jellyfin Classic - Setup & Scelte di Configurazione

Questo documento memorizza in modo permanente le scelte effettuate durante l'inizializzazione dell'istanza Jellyfin Classic (`jellyfin-classic`) per l'Isola Classica.

---

## ⚙️ Scelte di Inizializzazione (Setup Wizard)

*   **Data di Setup**: 21 Maggio 2026
*   **Lingua Interfaccia (UI)**: **Italiano**
    *   *Rapporto Tecnico*: La scelta della lingua italiana per l'interfaccia non interferisce con l'elaborazione dei tag. È ottimale per la gestione quotidiana della dashboard.
*   **Lingua Metadati Preferita**: **Italiano (Italian) / Italia (Italy)**
    *   *Rapporto Tecnico*: Indifferente a livello di scraper web in quanto tutte le query esterne sono disattivate, ma impostati su Italiano/Italia per coerenza estetica e conformità con l'interfaccia utente.

---

## 🎵 Libreria: "Musica Classica"

*   **Nome della Libreria**: `Musica classica`
*   **Tipo di Contenuto**: Musica (`Music`)
*   **Percorso Cartella**: `/media/music/classical`
    *   *Mounting Fisico*: Dataset ZFS su TrueNAS `/mnt/oliraid/arrdata/classical/library` (montato in Sola Lettura nel container).
*   **Abilita monitoraggio in tempo reale (Real-time monitoring)**: **ABILITATO** (Attivo).
    *   *Nota*: Permette a Jellyfin di rilevare tempestivamente le modifiche fisiche operate da Beets sul dataset, sebbene l'affidabilità su mount NFS dipenda dalle notifiche del kernel.

---

## 🛡️ Hardening dei Metadati & Scrapers (Prevenzione Inquinamento)

Per garantire la segregazione dell'Isola Classica e forzare Jellyfin a leggere unicamente i perfetti metadati Vorbis/ID3 taggati da Beets, sono state applicate le seguenti regole:

### 1. Metadata Settings (Impostazioni dei Metadati)
*   **Preferred download language**: **Italian** (Italiano).
*   **Country/Region**: **Italy** (Italia).
*   **Embedded file metadata (Metadati incorporati nei file)**: **ABILITATO** (Spuntato).
*   **Prefer embedded titles over server titles**: **ABILITATO** (Spuntato).
    *   *Obiettivo*: Impedisce a Jellyfin di sostituire i titoli formattati da Beets con i titoli standard dei database esterni.

### 2. Metadata Downloaders (Scaricatori Metadati)
*   **Artist Metadata Downloaders**:
    *   `MusicBrainz`: **DISABILITATO** (Deselezionato).
    *   `TheAudioDB`: **DISABILITATO** (Deselezionato).
*   **Album Metadata Downloaders**:
    *   `MusicBrainz`: **DISABILITATO** (Deselezionato).
    *   `TheAudioDB`: **DISABILITATO** (Deselezionato).

### 3. Image Fetchers (Scaricatori Immagini)
*   **Artist Image Fetchers**:
    *   Tutte le opzioni (MusicBrainz, Fanart.tv, ecc.): **DISABILITATE** (Deselezionate).
*   **Album Image Fetchers**:
    *   Tutte le opzioni (MusicBrainz, Fanart.tv, ecc.): **DISABILITATE** (Deselezionate).
    *   *Nota*: Jellyfin utilizzerà solo file di immagine locali (es. `cover.jpg`, `folder.jpg`) presenti nelle cartelle o immagini incorporate nei tag audio.

### 4. Cartelle Media & Artwork (Opzioni di Scrittura)
*   **Save artwork into media folders (Salva le immagini nelle cartelle dei media)**: **DISABILITATO** (Deselezionato).
    *   *CRUCIALE*: Poiché la cartella `/media/music/classical` è montata in **Sola Lettura** (`readOnly: true`), Jellyfin fallirebbe sistematicamente qualsiasi tentativo di scrittura dei file delle immagini sul disco TrueNAS. Disabilitando questa opzione, Jellyfin salverà in modo pulito tutte le copertine e le cache internamente nella sua directory `/config`.

---

## 🌍 Opzioni di Rete e Accesso Remoto (Fasi Finali del Wizard)

*   **Lingua Globale dei Metadati del Server**: **Italiano (Italian) / Italia (Italy)**
*   **Accesso Remoto (Allow remote connections to this server)**: **ABILITATO** (Attivo).
    *   *Nota*: Permette al Traefik IngressRoute esterno (`jellyfin-classic.pindaroli.org`) di convogliare le connessioni protette da OAuth2 verso il pod in totale sicurezza.
*   **Port Mapping Automatico (UPnP)**: **DISABILITATO** (Spento).
    *   *Nota*: Inutile e disabilitato per motivi di sicurezza, poiché non utilizziamo l'apertura porte UPnP dinamica per Jellyfin Classic; l'instradamento è interamente governato in modo dichiarativo e centralizzato da Traefik.

---

## 🏛️ Decisione Architetturale: Setup Wizard vs ConfigMap

*   **Scelta**: Configurazione persistente via Web UI salvata direttamente sul dataset TrueNAS (`csi-nfs-stripe-arr-conf`).
*   **Motivazione**: L'approccio originario di montare `options.xml` como ConfigMap statico e read-only in Kubernetes è stato **rifiutato**. Jellyfin richiede permessi di scrittura completi sulla cartella `/config` per aggiornare lo stato interno, i database e le preferenze. Il blocco in sola lettura di una porzione di `/config` causerebbe crash di sistema o instabilità.
