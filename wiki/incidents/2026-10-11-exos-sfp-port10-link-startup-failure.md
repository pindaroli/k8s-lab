---
title: "INC-2026-10-11: EXOS SFP+ Port 10 Link Failure at Startup (GoodTop Uplink)"
type: incident
status: archived
certified_for_ai: false
date: 2026-10-11
severity: P2
resolved: true
resolved_at: 2026-10-11T19:31:00+02:00
post_mortem: [[exos-port10-sfp-boot-recovery]]
tags:
  - "#incident"
  - "#network"
  - "#exos"
  - "#sfp"
---

# INC-2026-10-11: EXOS SFP+ Port 10 Link Failure at Startup (GoodTop Uplink)

## Descrizione dell'Incidente
Ad ogni riavvio o ciclo di accensione dello Switch Core Extreme Networks Summit X620-10x (`192.168.2.1`), la connettività 10 GbE sulla **Porta 10** (uplink trunk verso lo switch GoodTop GT-ST024M `192.168.2.2` nella stanza da letto) non si stabiliva automaticamente.

**Sintomo Operativo:**
- L'host client Mac Studio (collegato allo switch GoodTop) perdeva l'accesso a tutta l'infrastruttura della sala server (VLAN 1, 10, 20, 99).
- Il link sulla porta 10 di EXOS rimaneva bloccato nello stato `Ready / Link Down`.
- Per ripristinare il link, l'operatore doveva estrarre e reinserire manualmente l'adattatore SFP+ in rame dalla porta 10 dello switch Extreme.

---

## Analisi della Root Cause
Dall'ispezione diagnostica dell'hardware e dei log di avvio (`10/11/2026 08:24:57`) sono emersi i seguenti elementi:
1. **Transceiver 10GBASE-T Attivo in Rame**:
   - Modulo nella porta 10: `10G-T30-CSC` (OEM copper RJ45 SFP+, emulato via EEPROM come `SF+_SR (Unsupported)` a 850 nm).
   - Temperatura operativa: ~61 °C (dovuta al DSP/PHY Aquantia/Marvell interno).
2. **Boot Timing Race Condition**:
   - All'avvio di EXOS, le porte da 1 a 9 (cavi DAC passivi) si agganciavano in pochi secondi (<14s).
   - Il modulo in rame 10G-T30 nella porta 10 richiede 2–3 secondi per il boot del proprio microcontrollore e 8–10 secondi per il link training PAM16 10GBASE-T sul cavo Cat6A verso GoodTop.
3. **Mancato Clock/Data Recovery (CDR) Continuo su EXOS**:
   - Con la porta 10 configurata su `auto off speed 10000 duplex full`, l'ASIC Broadcom di EXOS controllava la portante 10GBASE-R fin dal primo istante. Trovando il PHY rame ancora in fase di training, la SerDes di EXOS andava in timeout e non ritentava la sincronizzazione continua.
4. **Effetto del Reseat Fisico**:
   - La disconnessione fisica azionava il pin hardware `MOD_ABS`, scatenando un interrupt di hot-plug su EXOS che reimpostava da zero lo stack della porta quando il modulo era già caldo e allineato.

---

## Azioni Correttive Adottate
1. **Script di Boot Idempotente Python (`bounce_port10.py`)**:
   - Creato [`scripts/network/exos/bounce_port10.py`](file:///Users/olindo/prj/k8s-lab/scripts/network/exos/bounce_port10.py) su EXOS.
   - Attende 15 secondi all'avvio; interroga lo stato live della porta tramite `exsh.clicmd("show ports 10 information", True)`.
   - **Idempotenza**: se la porta è già `active`, esce immediatamente (`sys.exit(0)`) senza provocare flap. Se la porta è bloccata in `ready` o `down`, esegue il reset SerDes (`disable ports 10` -> 2s -> `enable ports 10`).
2. **Autoexec EXOS (`autoexec.xsf`)**:
   - Creato [`scripts/network/exos/autoexec.xsf`](file:///Users/olindo/prj/k8s-lab/scripts/network/exos/autoexec.xsf) per eseguire automaticamente lo script al termine del boot di EXOS.
3. **Playbook Ansible IaC Permanente**:
   - Creato ed eseguito [`ansible/playbooks/infrastructure/exos_port10_boot_recovery.yml`](file:///Users/olindo/prj/k8s-lab/ansible/playbooks/infrastructure/exos_port10_boot_recovery.yml) che distribuisce e convalida i file nella memoria flash di EXOS.
4. **Validazione Test-Driven a Caldo**:
   - Testata l'esecuzione live dello script su porta attiva: verificata la corretta uscita con status `0` e zero pacchetti persi verso EXOS e GoodTop.

---

## Stato
**RISOLTO**. Gestito tramite il piano [[exos-port10-sfp-boot-recovery]].
