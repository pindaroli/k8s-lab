---
status: active
certified_for_ai: true
---
# Piano: CoreDNS Hard Anti-Affinity (Disable & Replace)

## 1. Obiettivo
Garantire che le repliche di CoreDNS vengano posizionate rigorosamente su nodi Control Plane differenti (Hard Anti-Affinity) per assicurare un RTO < 30s in caso di guasto hardware di un singolo nodo.

## 2. Strategia Architetturale: "Disable & Replace"
Alla luce dei limiti architetturali di Talos sui manifesti built-in, la modifica avverrà in modo 100% dichiarativo tramite il pattern *Disable & Replace* nei file `talos-config/controlplane-cp-0*.yaml`.

- Disabilitazione del CoreDNS nativo: `cluster.coreDNS.disabled: true`.
- Iniezione del manifesto custom: tramite `cluster.inlineManifests`.

## 3. Parametri Chiave del Manifesto Custom
- **Hard Anti-Affinity:** Sostituzione di `preferredDuringSchedulingIgnoredDuringExecution` con `requiredDuringSchedulingIgnoredDuringExecution`.
- **Rolling Update:** Modifica da `maxSurge: 1` a `maxUnavailable: 1, maxSurge: 0` per prevenire il deadlock dello scheduler sui cluster in cui Nodi == Repliche.

## 4. Guardia Procedurale (Post-Upgrade)
> [!WARNING]
> **BLOCCO PRE-UPGRADE (CORE-DNS OVERRIDE ATTIVO)**: Prima di aggiornare Talos OS, controllare le Release Notes di Sidero Labs. Se la nuova versione di Talos aggiorna l'immagine di CoreDNS, è **OBBLIGATORIO** aggiornare manualmente il campo `image:` all'interno del blocco `inlineManifests` nei file `talos-config/controlplane-cp-0*.yaml` e fare un `talosctl apply-config` prima di riavviare i nodi.

## 5. Passi di Esecuzione (TODO)
- [ ] 1. Inserimento del warning di upgrade nelle procedure.
- [ ] 2. Aggiornamento dei file `talos-config/controlplane-cp-0*.yaml`.
- [ ] 3. Esecuzione script di validazione rete: `python3 scripts/validate_network.py`.
- [ ] 4. Applicazione a caldo: `talosctl apply-config -n <IP> -f talos-config/controlplane-cp-0*.yaml`.
- [ ] 5. Verifica Riconciliazione: `kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide`.

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: 1. Aggiornamento Configurazione
- **Ultima Azione Completata**: Materializzazione del piano nel wiki.
- **Prossimo Passo Operativo**: Aggiornamento dei manifesti YAML in `talos-config/` e creazione della guardia nel wiki.
- **Blocchi/Decisioni Pendenti**: Nessuna.
