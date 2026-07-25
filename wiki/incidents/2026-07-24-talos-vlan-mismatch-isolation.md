---
title: "Talos Node 2 Isolation due to VLAN Tagging Mismatch"
date: "2026-07-24"
status: archived
certified_for_ai: false
resolved: true
resolved_at: "2026-07-24T13:10:00Z"
tags: [incident, talos, proxmox, networking, vlan, switch]
---

# Incident: Talos Node 2 Network Isolation (VLAN Tagging Mismatch)

## Sintesi
Il nodo Kubernetes `talos-cp-02` (in esecuzione su PVE2) ha perso improvvisamente la connettività di rete (Livello 2 e 3) dopo un riavvio fisico dello switch di rete 10G principale. Un'analisi iniziale tramite Gemini Deepsearch aveva erroneamente attribuito il problema a un bug noto del driver `virtio` relativo al checksum hardware (TSO/GSO) causato da un link flap.

## Root Cause
L'analisi del traffico di rete (tramite `tcpdump` sull'interfaccia fisica e virtuale in Proxmox) ha smentito la teoria del bug `virtio` e rivelato la vera causa: **un disallineamento della configurazione VLAN (VLAN Tagging Mismatch) sullo switch fisico.**

1. Al riavvio, la porta dello switch 10G collegata a PVE2 (Porta 2, `enp1s0f1np1`) ha perso la configurazione *Access* (Untagged VLAN 20) ed è tornata alla configurazione di default *Trunk*.
2. Il traffico in ingresso verso la VM arrivava taggato con `VLAN 20 (802.1Q)`.
3. L'interfaccia `eth0` di Talos, non essendo VLAN-aware, scartava i pacchetti taggati in ingresso (drop).
4. Talos inviava pacchetti untagged (ARP request) che uscivano correttamente da PVE2, ma lo switch in modalità Trunk li instradava nella Native VLAN sbagliata, impedendo al Gateway di rispondere.

## Risoluzione
L'utente ha riconfigurato la porta sullo switch fisico impostandola nuovamente in modalità **ACCESS** (PVID 20 / Untagged per la VLAN 20).
Immediatamente, i pacchetti hanno smesso di essere taggati, Talos ha ripreso a ricevere e inviare il traffico correttamente sulla rete nativa, e il nodo è tornato allo stato `Ready` nel cluster Kubernetes. 
La scheda di rete della VM è stata ripristinata con successo al driver standard `virtio`, confermando definitivamente che non vi era alcun bug di offloading.

## Lezioni Apprese
- Un'ispezione dei pacchetti L2/L3 (tcpdump) direttamente sulle interfacce di bridge di Proxmox è fondamentale per identificare disallineamenti di VLAN.
- Non assumere che bug complessi del kernel/driver (es. checksum dropping) siano la causa senza prima aver escluso problemi di routing di base (Layer 2).
