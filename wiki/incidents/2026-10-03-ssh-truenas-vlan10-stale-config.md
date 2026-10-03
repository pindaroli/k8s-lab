---
title: "INC-2026-10-03: TrueNAS SSH Connection Failure & SSH Config Stale IP Mismatch"
type: incident
status: archived
certified_for_ai: false
date: 2026-10-03
severity: P3
resolved: true
resolved_at: 2026-10-03T22:14:00+02:00
tags:
  - "#incident"
  - "#network"
  - "#truenas"
  - "#ssh"
---

# INC-2026-10-03: TrueNAS SSH Connection Failure & SSH Config Stale IP Mismatch

## Descrizione dell'Incidente
L'operatore ha riscontrato un comportamento apparentemente discordante nell'accesso a TrueNAS da Mac Studio:
- `ping truenas` rispondeva regolarmente con esito positivo (0% packet loss) su `truenas.pindaroli.org (10.10.20.50)` (VLAN 20).
- `ssh olindo@truenas` falliva immediatamente con errore:
  `ssh: connect to host 10.10.10.50 port 22: Network is unreachable.`

L'utente ipotizzava un disallineamento all'interno di `rete.json` o un cambio anomalo di VLAN tra i protocolli.

## Analisi della Root Cause
1. **Migrazione Precedente su VLAN 20**: In data 2026-09-25 ([[truenas-vlan20]]), TrueNAS e lo stack applicativo Docker/NFS/MCP sono stati migrati da `10.10.10.50` (VLAN 10 Server) a `10.10.20.50` (VLAN 20 Client) su LACP `bond0`.
2. **Risoluzione DNS di Sistema**: `ping truenas` interrogava il resolver di sistema (Unbound su OPNsense), che risolveva correttamente `truenas.pindaroli.org` a `10.10.20.50`.
3. **Override Statico in `~/.ssh/config`**: Il comando `ssh` sul client Mac Studio non utilizzava la risoluzione DNS in quanto in `~/.ssh/config` (righe 19–22) era ancora presente una direttiva statica hardcoded:
   ```sshconfig
   Host truenas 10.10.10.50 truenas.pindaroli.org
       HostName 10.10.10.50
   ```
   Questa direttiva forzava il traffico SSH verso la vecchia interfaccia dismessa `10.10.10.50` su VLAN 10, provocando `Network is unreachable`.
4. **Disallineamenti Residui in `rete.json`**: Durante l'ispezione sono state rilevate e corrette discrepanze residue in `rete.json`:
   - Porte 4 e 8 dello switch Extreme ancora censite con `pvid: 10` e label `VLAN 10`, anziché `pvid: 20` untagged (client) e VLAN 10 tagged (per PBS).
   - Nodo `truenas` ancora etichettato come `"type": "VM"` / `"vm_id": "1100"` anziché `"type": "Bare Metal"`.

## Azioni Correttive Adottate
1. **Aggiornamento `~/.ssh/config`**:
   Sostituito `HostName 10.10.10.50` con `10.10.20.50` nel blocco `Host truenas 10.10.20.50 truenas.pindaroli.org`.
2. **Verifica Risoluzione SSH**:
   Validata la corretta risoluzione tramite:
   ```bash
   ssh -G truenas | head -n 4
   # Output: hostname 10.10.20.50, port 22, user olindo
   ```
3. **Allineamento `rete.json`**:
   - Aggiornato `type` di TrueNAS a `Bare Metal` (rimosso `vm_id: 1100`).
   - Aggiornate le porte 4 e 8 dello switch Extreme a `pvid: 20` e ruolo LACP VLAN 20 untagged / VLAN 10 tagged.
   - Validata la configurazione con `python3 scripts/network/validate_network.py` e rigenerato `wiki_context.md`.

## Stato
**RISOLTO**.
