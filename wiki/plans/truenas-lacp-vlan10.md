---
title: "TrueNAS LACP VLAN 10"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-09-25
completed_at: 2026-09-25
tags:
  - "#plan"
  - "#network"
  - "#extreme"
  - "#truenas"
---

# TrueNAS: LACP dei due NIC sulla VLAN 10

> [!NOTE]
> **Eseguito il 2026-09-25.** `bond0` è up con `10.10.10.50/24`. Sullo switch Extreme il LAG LACP (master porta 4, membro porta 8) ha entrambi i membri Collecting/Distributing. `primary.cfg` è salvato. La VM PBS è su `bond0` e risponde su `10.10.10.100`.

I due NIC 10G di TrueNAS entrano in un LAG LACP 802.3ad sullo switch Extreme, access untagged sulla VLAN 10. L'indirizzo resta `10.10.10.50`. Sostituisce il dual-home verso la VLAN 20. [[dual-homing-vlan10-vlan20]] resta scartato.

Un solo indirizzo, `10.10.10.50/24`, sul bond. I client della VLAN 20 continuano a raggiungerlo dalla SVI dello switch, sullo stesso percorso simmetrico di oggi. Non c'è una seconda rotta connessa, quindi non nasce il ritorno sull'altra scheda.

Il LAG è 802.3ad (LACP). Sullo switch è una porta access untagged della VLAN server (VID 10), non un trunk 802.1Q.

## Stato di partenza

- `enp1s0f0np0` UP, `10.10.10.50/24`, default `10.10.10.1`. MAC `8c:fd:18:f7:f5:92`.
- `enp1s0f1np1` UP a 10 Gbit/s, DAC, senza indirizzo. MAC `8c:fd:18:f7:f5:93`.
- FDB Extreme (2026-09-25): `8c:fd:18:f7:f5:92` sulla porta 4, VLAN `server`. `8c:fd:18:f7:f5:93` sulla porta 8, VLAN `client`, unico MAC su quella porta. Il LAG usa la porta 4 come master e la porta 8 come membro.
- OOB `enp8s0` `192.168.100.50/24`. La sessione di taglio sta qui: durante il LAG l'indirizzo `10.10.10.50` si stacca dalla scheda fisica.
- `macvtap0` della VM PBS è figlio di `enp1s0f0np0`. Va riagganciato al bond, altrimenti PBS perde la rete (`10.10.10.100`).
- `rete.json` non fa fede sui cavi. Le due porte si leggono dalla FDB.

Un flusso TCP resta su un solo link: l'hash è L3+L4. Il secondo link serve agli altri flussi e al guasto di un cavo.

## Fase 1 — Cavo e porte

Si collega il DAC su `enp1s0f1np1` e si alza l'interfaccia senza indirizzo. Dallo switch si legge la FDB:

- `8c:fd:18:f7:f5:92` è la porta già in uso
- `8c:fd:18:f7:f5:93` è la porta nuova

La porta nuova deve essere libera. Non si riusa una porta che ha già un MAC di un altro host. Le porte di Proxmox non entrano nel LAG.

Rollback: interfaccia down e cavo staccato.

## Fase 2 — LAG sullo switch

Playbook Ansible sul gruppo `switches`, salvato nel repository, poi `save configuration primary`. Sulle due porte lette in fase 1:

- `enable sharing <master> grouping <master>,<seconda> algorithm address-based L3_L4 lacp`
- la porta master untagged nella VLAN `server` (VID 10)
- la porta membro non resta access su un'altra VLAN

LACP timeout lungo su entrambi i lati (default EXOS). Il playbook si applica nella stessa finestra della fase 3, con la sessione su `192.168.100.50`: finché TrueNAS non manda LACP, la porta viva smette di inoltrare.

Rollback del playbook: `disable sharing <master>` e la porta originale di nuovo untagged nella VLAN server.

## Fase 3 — LAGG su TrueNAS

Sempre da OOB, nello stesso intervallo:

- interfaccia `bond0`, protocollo LACP, membri `enp1s0f0np0` e `enp1s0f1np1`, hash layer3+4
- alias `10.10.10.50/24` e gateway `10.10.10.1` sul bond; le due schede fisiche restano senza indirizzo
- NIC della VM PBS spostato da `enp1s0f0np0` a `bond0` (`macvtap` sul bond)
- OOB `192.168.100.50` invariato

NFS, SMB, Docker, NUT e l'UI restano su `10.10.10.50`. Nessun export, PV, Endpoint o record DNS cambia.

Verifica: `https://10.10.10.50` risponde; da un nodo Talos gli NFS sono `rw`; PBS `10.10.10.100` risponde; `show sharing` e `show lacp` sullo switch vedono i due membri Collecting/Distributing. Si stacca un cavo alla volta e l'indirizzo resta raggiungibile.

Rollback: indirizzo di nuovo su `enp1s0f0np0`, bond rimosso, NIC PBS riagganciato a quella scheda, sharing disabilitato sullo switch.

## Fase 4 — Registry

- `rete.json`: i due NIC nel LAG, porta master e membro letti in fase 1, `management_ip` `10.10.10.50`.
- [[TrueNAS]] e [[Network_Registry]].
