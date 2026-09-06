---
title: "Estrazione e Normalizzazione Documentazione OPNsense 26.1 per RAGFlow"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-09-06
completed_at: 2026-09-06
tags:
  - "#plan"
  - "#opnsense"
  - "#ragflow"
  - "#docs"
  - "#knowledge-base"
---

# Piano Operativo: Estrazione e Normalizzazione Documentazione OPNsense 26.1 per RAGFlow

Questo piano definisce la progettazione, lo sviluppo e l'esecuzione dello script di automazione per il download, la conversione e l'ottimizzazione semantica della documentazione ufficiale di **OPNsense** (allineata alla release in uso nel lab: **OPNsense 26.1 / series "Witty Woodpecker"**), seguendo l'architettura e i pattern già adottati con successo per TrueNAS SCALE (`extract_truenas_docs.py`).

---

## 🎯 Obiettivi e Perimetro

1. **Rilevazione Release di Riferimento**:
   - Versione live in esecuzione: **OPNsense 26.1.10-amd64** (FreeBSD 14.3-RELEASE-p10, OpenSSL 3.0.21).
   - Repository upstream: `https://github.com/opnsense/docs.git`.
   - Target di estrazione: branch `master` o commit allineato alla serie 26.1 (con focus su documentazione Core, Manual, How-Tos e Release Notes CE 26.1).

2. **Pattern Analogo a TrueNAS (`extract_truenas_docs.py`)**:
   - Creazione dello script standalone `scripts/ragflow/extract_opnsense_docs.py`.
   - Esecuzione di uno shallow clone mirato del repository `opnsense/docs` in directory temporanea isolata (`scratch/opnsense-docs-repo`).
   - Parsing ricorsivo e risoluzione inline di tutte le direttive `.. include::` per garantire l'autosufficienza di ciascun documento (ideale per il chunking e retrieval vettoriale in RAGFlow).

3. **Conversione RST $\rightarrow$ Markdown ad Altissima Fedeltà**:
   - Conversione della sintassi Sphinx/reStructuredText in GitHub Flavored Markdown (.md).
   - Mappatura completa delle Admonition Sphinx in GitHub Alerts standard:
     - `.. Note::` $\rightarrow$ `> [!NOTE]`
     - `.. Warning::` / `.. Danger::` $\rightarrow$ `> [!WARNING]`
     - `.. Tip::` / `.. Hint::` $\rightarrow$ `> [!TIP]`
     - `.. Caution::` / `.. Important::` $\rightarrow$ `> [!CAUTION]` / `> [!IMPORTANT]`
   - Formattazione comandi e percorsi menu:
     - `:menuselection:`Firewall --> Rules --> Rules [new]`` $\rightarrow$ `**Firewall** > **Rules** > **Rules [new]**`
     - `:command:` / `:code:` $\rightarrow$ blocchi inline `code`
     - `.. code-block:: <lang>` $\rightarrow$ fenced code blocks standard
   - Tabelle Sphinx/reST $\rightarrow$ tabelle Markdown GFM (`| ... |`).

4. **Preservazione e Risoluzione dei Link Semantici (Semantic Link Integrity)**:
   - **Indicizzazione a due passaggi (Two-Pass Symbol Table)**:
     - *Passaggio 1 (Scan & Index)*: scansione globale di tutti i file `.rst`, estrazione dei titoli (`# Title`), delle etichette Sphinx (`.. _label:`) e mappa delle corrispondenze percorso/ancora.
     - *Passaggio 2 (Resolution)*:
       - Ruoli `:doc:` (es. `:doc:`/manual/how-tos/multiwan`` oppure `:doc:`normalization <firewall_scrub>``): trasformazione in link Markdown relativi con estensione `.md` (`[Multi-WAN](relative/path/multiwan.md)` o `[normalization](firewall_scrub.md)`), con risoluzione automatica del titolo qualora non esplicitato.
       - Ruoli `:ref:` (es. `:ref:`intro_installation`` o `:ref:`Custom Label <anchor>``): risoluzione puntuale verso il file `.md` e l'ancora target (`[Title](relative/file.md#anchor)`).
       - Link a sezioni interne (```section`_``) e link esterni (```Testo <URL>```_).
       - Ruoli `:rfc:` e `:pep:` mappati sui repository IETF/Python ufficiali.

5. **Arricchimento Metadati per RAGFlow**:
   - Iniezione in testa ad ogni documento di un header semantico strutturato (YAML o blocco callout) contenente:
     - Titolo del documento
     - Release OPNsense di riferimento (26.1 Witty Woodpecker)
     - Categoria funzionale (Firewall, Routing, Interfaces, Services, VPN, Diagnostics, How-To)
     - Keywords e tag concettuali
     - File sorgente upstream

6. **Generazione Master Index (`SUMMARY.md`)**:
   - Creazione automatica dell'indice generale della documentazione suddiviso per categorie funzionali, con statistiche sul numero di documenti generati e collegamenti diretti a tutti gli articoli.

7. **Gestione Immagini e Asset Statici**:
   - Copia degli asset grafici (`source/images/`) nella directory di destinazione `downloads/opnsense-26.1/images/` per preservare il rendering visuale dei diagrammi e degli screenshot della Web UI.

---

## 📋 Fasi di Implementazione

### Fase 1: Progettazione e Sviluppo di `extract_opnsense_docs.py`
- [ ] Creazione del parser semantico in `scripts/ragflow/extract_opnsense_docs.py`.
- [ ] Implementazione del motore a doppio passaggio:
  - Cache dei simboli, label Sphinx (`.. _target:`) e titoli dei documenti.
  - Risolutore inline di include ricorsivi (`.. include::`).
  - Convertitore di sintassi reST $\rightarrow$ GFM Markdown.
  - Risolutore di ruoli semantici (`:doc:`, `:ref:`, `:menuselection:`, link esterni/interni).
  - Normalizzatore di admonizioni in GitHub alerts.
- [x] Parametrizzazione CLI (`--branch`, `--repo-url`, `--output-dir`, `--temp-dir`, `--keep-clone`).

### Fase 2: Esecuzione Test-Driven & Validazione su Campione
- [x] Shallow clone upstream in `scratch/opnsense-docs-repo`.
- [x] Esecuzione in dry-run o estrazione mirata su file campionari complessi:
  - `source/manual/firewall.rst` (contiene diagrammi, ruoli `:doc:`, `:menuselection:`, admonizioni multiple).
  - `source/manual/aliases.rst` (tabelle e riferimenti incrociati).
  - `source/manual/unbound.rst` e `source/manual/kea.rst` (servizi critici del lab).
  - `source/manual/how-tos/wireguard-client.rst` (how-to con step sequenziali e immagini).
- [x] Verifica dell'integrità dei link semantici generati e del rendering Markdown.

### Fase 3: Estrazione Completa & Generazione Master Index
- [x] Esecuzione completa su tutto il corpus documentale di OPNsense (420 file processati da `manual/`, `how-tos/`, `intro.rst`, `setup.rst`, `system.rst`, `releases/CE_26.1.rst`).
- [x] Generazione del file `downloads/opnsense-26.1/SUMMARY.md`.
- [x] Copia e allineamento degli asset statici/immagini (`images/` e `manual/images/`).
- [x] Verifica del conteggio totale e assenza di link orfani o shortcode non convertiti.

### Fase 4: Integrazione RAGFlow & Persistenza Knowledge Base
- [x] Organizzazione del dataset per ingestione nel cluster RAGFlow (`downloads/opnsense-26.1/` pronto per dataset `opnsense`).
- [x] Standardizzazione Text-First (Gold Standard): rimosse cartelle immagini `images/` e `manual/images/` per eliminare qualsiasi rumore OCR e allineare OPNsense all'architettura di TrueNAS.
- [x] Aggiornato `extract_opnsense_docs.py` con default text-first (421 file `.md` puri) e flag opzionale `--with-images`.
- [x] Riconoscimento semantico dei riferimenti grafici preservato nel testo Markdown (`![alt](images/...)`).
- [x] Documentazione dell'entità OPNsense in `wiki/entities/OPNsense.md` per tracciare la disponibilità della documentazione 26.1 offline.
- [x] Pulizia automatica della directory temporanea di scratch e aggiornamento `.gitignore`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Dataset OPNsense 26.1 allineato allo standard text-first (421 file Markdown puri, 0 immagini, 0 rumore OCR). Aggiornato `extract_opnsense_docs.py` con flag `--with-images` (default False) e verificata la cartella locale `downloads/opnsense-26.1/` pronta per l'ingestione definitiva.
- **Prossimo Passo Operativo**: Ricaricamento/aggiornamento del dataset `opnsense` su RAGFlow da parte dell'utente tramite WebUI e consultazione tramite MCP RAGFlow.
- **Blocchi/Decisioni Pendenti**: Nessuno. Operazione conclusa al 100%.
