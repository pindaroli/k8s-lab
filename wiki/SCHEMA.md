# GEMINI LLM Wiki: Governance Schema

Questo documento definisce le regole strutturali che l'agente (IA) e l'utente devono rispettare per mantenere l'integrità del Wiki.

## 1. Frontmatter Obbligatorio (YAML)
Ogni file all'interno di `wiki/entities/`, `wiki/workflows/` e `wiki/incidents/` **DEVE** iniziare con il seguente blocco YAML:

```yaml
---
title: "Nome dell'Entità o Evento"
last_updated: "YYYY-MM-DD"
confidence: "High|Medium|Low" # Livello di affidabilità dell'informazione
tags:
  - "#tag1"
  - "#tag2"
provenance: # Riferimenti ai file RAW o incidenti originali
  - "nomefile_raw.md"
---
```

## 2. Sintassi di Collegamento (Wikilinks)
- Utilizzare sempre i doppi bracket per collegare le entità: `[[NomeEntita]]`.
- Non utilizzare link Markdown standard per file interni (es. `[testo](file.md)`), ma usare i wikilinks per mantenere la compatibilità con la Graph View di Obsidian.

## 3. Principio di Non-Distruzione (Tensione Dialettica)
- **Mantenimento**: Ogni volta che un'entità cambia (nuovo IP, nuova policy), aggiorna il file corrispondente.

## 4. Cosa NON includere nel Wiki
> [!CAUTION]
> **NO TRANSIENT DATA**: Non inserire nel Wiki dump temporanei, log grezzi o liste di record DNS (es. `pindaroli.org.txt`). 
> Il Wiki deve contenere solo **conoscenza curata, universale e strutturata**. I dati transienti devono restare nella root o in cartelle di log/audit dedicate, per non "sporcare" la base di conoscenza degli agenti.

Se nuove informazioni contraddicono il contenuto esistente:
1. NON sovrascrivere o eliminare il vecchio blocco se non si è assolutamente certi che fosse errato.
2. Creare una sezione `## Evoluzione / Tensioni Note`.
3. Annotare: *"Precedentemente configurato in modo X, modificato in modo Y per risolvere il problema Z (Vedi [[Incidente_XYZ]])"*.

## 5. Tassonomia dei Tag
Usare i seguenti tag per standardizzare la ricerca:
- Livello: `#core`, `#app`, `#network`, `#storage`
- Stato: `#active`, `#deprecated`, `#pending_hardware`
- Piattaforma: `#opnsense`, `#talos`, `#truenas`, `#proxmox`
