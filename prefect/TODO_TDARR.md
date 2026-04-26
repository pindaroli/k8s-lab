# TODO: Integrazione Tdarr & Prefect

Documento per la raccolta dei parametri necessari alla Fase 3 e 4.

## 1. Storage & Percorsi NFS
- [ ] **Media Source**: Identificare la share TrueNAS corretta (es. `/mnt/oliraid/arrdata/media`).
- [ ] **Transcode Cache**: Definire se usare storage locale veloce (Talos nodes) o share NFS temporanea.
- [ ] **Output Logic**: Sovrascrittura file sorgente o spostamento in cartella di staging.

## 2. Risorse & Hardware
- [ ] **Transcoding Mode**: Scegliere tra solo CPU o abilitazione GPU Passthrough/Intel QuickSync.
- [ ] **Limiti Risorse**: Definire CPU/Memory limits per i pod Tdarr-Node per evitare di saturare il cluster.

## 3. Architettura K8s
- [ ] **Namespace**: Decidere tra `arr` (consolidato) o `tdarr` (dedicato).
- [ ] **Tdarr Server**: Deployment con persistenza per il DB MongoDB interno.
- [ ] **Tdarr Nodes**: 
    - [ ] Configurazione nodi statici (sempre attivi).
    - [ ] Integrazione con Prefect per attivazione nodi "on-demand" (Phase 4).

## 4. Networking & Sicurezza
- [ ] **Internal API**: Porta 8266 per comunicazione Server <-> Nodes.
- [ ] **External UI**: Porta 8265 via Traefik IngressRoute.
- [ ] **OAuth2**: Abilitazione middleware `google-auth` per accesso esterno.

## 5. Workflow Prefect (Fase 4)
- [ ] **Trigger**: Definizione degli eventi che scatenano la scansione Tdarr.
- [ ] **Schedules**: Orari di esecuzione per le operazioni di manutenzione libreria.
