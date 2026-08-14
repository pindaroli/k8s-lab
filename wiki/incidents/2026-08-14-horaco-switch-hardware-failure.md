---
status: archived
certified_for_ai: false
resolved: true
resolved_at: 2026-08-14T19:00:00+02:00
---
# Incident Report: Guasto Hardware Switch Horaco (switch-25g-server)

## Data Evento
14 Agosto 2026

## Descrizione del Problema
Lo switch managed a 2.5G Horaco (modello HC-SWTGW218ASHC), impiegato come `switch-25g-server`, ha smesso di gestire correttamente il traffico sulle connessioni di trunk e uplink. 
Durante i successivi test diagnostici fuori dalla rete (da banco) tramite Mac Studio, si è rilevato che:
- Le porte dalla 1 alla 4 si accendevano ma rimanevano confinate nella VLAN 99 (vecchia configurazione isolata).
- Le porte 7 e 8 (utilizzate in precedenza per l'uplink trunk e l'accesso alla VLAN 1 di gestione) non stabilivano il link fisico (luci spente) con nessun apparato, inclusi adattatori USB 1G e connessioni verso altri switch.
- La porta SFP+ 10G (Porta 9) non negoziava alcun link tramite cavo DAC verso lo switch Extreme Networks.
- Il pulsante hardware di factory reset risultava non funzionante e inefficace, anche impiegando cicli di power-cycle prolungati e metodi di U-Boot recovery.

## Root Cause Analysis
Guasto hardware catastrofico interno allo switch. Si ipotizza la "morte" termica o elettrica (bruciatura) del chip PHY (Physical Layer Controller) preposto alla gestione del blocco porte 5-8 e del bus SFP+, associata a una probabile mancata o errata implementazione hardware del tasto di reset fisico.

## Risoluzione
L'apparato è stato giudicato irrecuperabile e ritirato definitivamente dalla produzione.
- Lo stato del dispositivo nel database `rete.json` è stato aggiornato da `operativo` a `dismesso`.
- Nessuna ulteriore azione di troubleshooting richiesta.
