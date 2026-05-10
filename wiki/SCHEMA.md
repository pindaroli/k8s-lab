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
## 6. Infrastructure as Code (IaC) - Implementation
In attuazione alla regola in [[GEMINI]], ogni modifica segue questo protocollo tecnico:

1.  **HELM First**: Ogni modifica alla configurazione delle applicazioni (IP, variabili d'ambiente, volumi) deve essere effettuata aggiornando il corrispondente file `values.yaml` e lanciando un `helm upgrade`.
2.  **Talos Configs**: Utilizzare i file specifici `talos-config/controlplane-cp-XX.yaml` e `talosctl apply-config`.
3.  **Sincronizzazione**: Il cluster deve essere lo specchio fedele del repository Git.

## 7. Network & DNS Standards
Per mantenere la coerenza tra l'inventario `rete.json` e la risoluzione dei nomi:

1.  **DNS Sources**: Solo i campi `id`, `hostname`, `aliases` e `name` (interfacce logiche) sono fonti valide per record DNS.
2.  **Sanitization**: Mai usare descrizioni testuali (es. "Client LAN") o nomi fisici delle interfacce (`en0`, `eth1`) come hostnames.
3.  **Consistency**: Ogni record DNS deve essere riconducibile a un'entrata esplicita in `rete.json`.

## 8. Storage & NFS Standards (TrueNAS)
Ogni export NFS destinato al cluster Kubernetes o a nodi di calcolo (es. Tdarr) deve rispettare questi requisiti:

1.  **Maproot**: Impostare `Maproot User: root`.
2.  **Security**: Abilitare l'opzione `Insecure` per permettere connessioni da porte non privilegiate.
3.  **Access Control**: Autorizzare gli IP specifici o la subnet.

## 9. Manutenzione Helm: Soft Stop vs Uninstall
Se è necessario fermare temporaneamente un'applicazione senza distruggere la release:

1.  **Soft Stop**: `kubectl scale deployment -n <namespace> --all --replicas=0`.
2.  **Ripristino**: `kubectl scale deployment -n <namespace> --all --replicas=1`.

## 10. Strategia di Indirizzamento (Tecnica)
Per garantire l'Alta Affidabilità (HA) definita in [[GEMINI]]:

1.  **Ingress/External**: Puntare i record DNS esterni (Cloudflare) o interni (OPNsense) sempre al **VIP** (es. `10.10.10.100`) o al nome host logico (es. `k1`).
2.  **Pod-to-Pod**: Usare sempre il Service Name `svc.cluster.local`. È vietato usare l'IP del VIP o l'IP fisico del nodo per la comunicazione interna tra container.
3.  **Stateful Awareness**: L'indirizzamento logico non sposta lo storage locale. La resilienza dei dati deve essere gestita a livello applicativo (replicazione DB).
