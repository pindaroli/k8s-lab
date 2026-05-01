# Ripresa Lavori Tdarr Transcoding

## Stato Attuale
- **DNS**: Operativo (Explicit Mapping).
- **Server**: OK (Pod riavviato, plugin caricati).
- **Nodo Mac**: Configurato in `tdarr/node/Tdarr_Node_Config.json`.
- **Script**: `start_node.sh` include auto-mount e sicurezza `rmdir`.

## Problema da Risolvere
Il mount NFS fallisce con `Permission denied`.
**Azione richiesta**: Verificare su TrueNAS (10.10.10.50) l'esportazione `/mnt/oliraid/arrdata/media`.
Assicurarsi che:
1. L'IP `10.10.20.100` sia autorizzato.
2. `Maproot User` sia `root`.
3. L'opzione `Insecure` (non-privileged ports) sia attiva.

## Obiettivo Finale
Lancio del nodo, configurazione Library Movies con catena di plugin H265 e backup originale in `movies_backup`.
