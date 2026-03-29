# 🚀 Prompt per Migrazione n8n su postgres-main

Copia e incolla questo prompt in una nuova conversazione quando vuoi migrare il database di `n8n` sull'istanza principale e attivare il monitoraggio.

---

### Prompt da usare:

> "Ciao! Dobbiamo migrare il database di **n8n** dal suo cluster dedicato (`n8n/postgres-n8n`) al cluster principale del lab (`cnpg-system/postgres-main`).
> 
> **Piano d'azione:**
> 1.  **Backup**: non è necessario.
> 2.  **Preparazione**: Crea un nuovo database `n8n` e un utente dedicato nel cluster `postgres-main` (usa CloudNativePG).
> 3.  **Ripristino**: non e necessario
> 4.  **Configurazione**: Aggiorna il deployment di `n8n` per puntare a `postgres-main-rw.cnpg-system.svc.cluster.local`.
> 5.  **Verifica**: Assicurati che n8n funzioni correttamente con i nuovi dati.
> 6.  **Cleanup**: Una volta confermato, elimina il vecchio cluster `n8n/postgres-n8n`.
> 7.  **Monitoring**: Attiva lo scraping per n8n assicurandoti che le metriche siano ora incluse nel monitoraggio di `postgres-main`.
>
> Procedi pure con l'analisi e l'esecuzione."

---

### Stato Attuale (Rilevato il 2026-03-29):
- **n8n Namespace**: `n8n`
- **DB Host Attuale**: `postgres-n8n-rw`
- **Cluster Principale Target**: `postgres-main` in `cnpg-system`
- **Monitoring**: Già attivo su `postgres-main` (VMServiceScrape `postgres-main` in `monitoring`).
