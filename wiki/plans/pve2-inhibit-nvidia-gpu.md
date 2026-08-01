---
title: "Procedura: Inibizione Riconoscimento GPU NVIDIA su PVE2"
type: plan
status: active
certified_for_ai: true
created_at: 2026-07-31
tags:
  - "#plan"
  - "#proxmox"
  - "#hardware"
  - "#power-saving"
---

# Procedura: Gestione Dinamica Alimentazione GPU NVIDIA su PVE2 (ON/OFF Scripts)

> [!IMPORTANT]
> **Nodo Target**: `PVE2` (Minisforum 795S7 / AMD 7945HX)
> **Obiettivo**: Fornire due script (`gpu_on.sh` e `gpu_off.sh`) per spegnere logicamente (rimuovere dal bus) e riaccendere la GPU dedicata NVIDIA RTX 4060 Ti in base all'esigenza (es. per usarla con la VM gaming), riducendo i consumi quando non serve.

---

## 1. Analisi dei Vincoli (Constraints)

Creare script di accensione/spegnimento "a caldo" è assolutamente fattibile sfruttando i comandi di `remove` e `rescan` del sottosistema PCI di Linux, ma su questo hardware ci sono **3 vincoli fondamentali da rispettare rigorosamente**:

1. **Stato della VM Gaming**: È **assolutamente vietato** lanciare lo script `gpu_off.sh` mentre la VM Gaming (o qualsiasi altra VM che usa la GPU) è accesa. Rimuovere a caldo il dispositivo PCI mentre è mappato alla memoria di una VM causerà un **Kernel Panic immediato dell'host Proxmox**. Lo script dovrà includere un controllo di sicurezza per impedire l'esecuzione se la VM è in stato "running".
2. **Bug ACPI/BIOS del Minisforum**: Abbiamo già appurato che questo minipc soffre di gravi bug sulla gestione energetica PCIe (il famoso crash in stato `D3cold`). C'è il rischio latente che l'operazione di "rescan" a caldo del bus PCI per riattivare la scheda possa causare instabilità o fallire il reinizializzamento a causa del BIOS immaturo. L'unico modo per confermarlo è testare fisicamente lo script `gpu_on.sh` la prima volta.
3. **Persistenza al Riavvio (Boot State)**: Dobbiamo decidere se, al riavvio fisico di Proxmox, la scheda debba essere ACCESA (stato default per usarla subito) o SPENTA (massimo risparmio energetico automatico). Per questa configurazione, imposteremo che **al boot la GPU viene rimossa automaticamente** tramite udev, per poi essere attivata manualmente tramite lo script quando serve.

---

## 2. Fasi di Implementazione

### Fase 1: Regola udev (Spento di Default al Boot)
Manteniamo la regola udev in modo che la GPU non consumi energia ad ogni avvio del server, finché non viene esplicitamente richiamata.

**File**: `/etc/udev/rules.d/99-remove-nvidia.rules`
```text
# Rimuove la GPU e l'Audio NVIDIA al boot per risparmiare energia
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x03[0-9]*", ATTR{remove}="1"
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x040300", ATTR{remove}="1"
```

### Fase 2: Creazione dello Script di Spegnimento (`gpu_off.sh`)
Questo script controllerà lo stato della VM 2500 (la VM gaming del piano precedente). Se è spenta, procede alla disconnessione della GPU dal bus PCI.

**File**: `/root/scripts/gpu_off.sh`
```bash
#!/bin/bash
VM_ID=2500

# Controllo se la VM è accesa
VM_STATUS=$(qm status $VM_ID | grep -o 'running')
if [ "$VM_STATUS" == "running" ]; then
    echo "ERRORE: La VM $VM_ID è accesa! Spegnere la VM prima di disabilitare la GPU."
    exit 1
fi

echo "Sgancio la GPU NVIDIA dal bus PCI..."
# Gli indirizzi 03:00.0 e 03:00.1 saranno verificati dinamicamente prima del deploy
if [ -d /sys/bus/pci/devices/0000:03:00.0 ]; then
    echo 1 > /sys/bus/pci/devices/0000:03:00.0/remove
fi
if [ -d /sys/bus/pci/devices/0000:03:00.1 ]; then
    echo 1 > /sys/bus/pci/devices/0000:03:00.1/remove
fi

echo "GPU disabilitata (Power Off Logico)."
```

### Fase 3: Creazione dello Script di Accensione (`gpu_on.sh`)
Questo script richiederà al kernel di rinegoziare i dispositivi PCI. Trovando la porta connessa, la GPU riapparirà e il driver `vfio-pci` la prenderà automaticamente in carico (come configurato in `/etc/modprobe.d/vfio.conf`).

**File**: `/root/scripts/gpu_on.sh`
```bash
#!/bin/bash

echo "Forzo la scansione del bus PCI per risvegliare la GPU NVIDIA..."
echo 1 > /sys/bus/pci/rescan
sleep 2

# Verifica del successo
lspci -nn | grep -i nvidia
if [ $? -eq 0 ]; then
    echo "GPU risvegliata e pronta per l'uso."
else
    echo "ERRORE: GPU non trovata. Il BIOS potrebbe aver bloccato il risveglio PCIe."
fi
```

### Fase 4: Applicazione tramite Script di Installazione
Per semplificare il deployment e mantenere traccia dei comandi, è stato creato uno script di automazione locale nella repository:
`mgm-gpu/install_gpu_mgmt.sh`

Questo script si collega via SSH a `10.10.10.21` (PVE2) e automatizza:
1. La copia degli script `gpu_on.sh` e `gpu_off.sh` in `/root/scripts/`.
2. La creazione della regola udev e del file di blacklist.
3. L'aggiornamento dell'initramfs.

Per applicare la configurazione, basta eseguire dal Mac (all'interno del progetto k8s-lab):
```bash
bash mgm-gpu/install_gpu_mgmt.sh
```
Una volta terminato, il nodo dovrà essere riavviato (quando le condizioni del cluster lo permettono) per rendere effettiva l'esclusione della GPU al boot.

---

## 3. Checklist di Verifica (Test-Driven)

| Step | Azione / Comando | Risultato Atteso |
|---|---|---|
| 1 | Riavvio del nodo PVE2. Esecuzione `lspci \| grep nvidia` | Nessun dispositivo NVIDIA presente. Consumo ridotto. |
| 2 | Esecuzione `./gpu_on.sh` | La GPU appare in lspci, agganciata a `vfio-pci`. Nessun Kernel Panic. |
| 3 | Avvio VM 2500 (`qm start 2500`) e successivo spegnimento | La VM funziona e rilascia la GPU correttamente allo spegnimento. |
| 4 | Esecuzione `./gpu_off.sh` | La GPU scompare di nuovo dal bus. Il sistema rimane stabile. |

---

## 4. Disaster Recovery (Kernel Panic al Boot)

> [!CAUTION]
> **Rischio KVM IP e Video Output**: Se il KVM IP è collegato alla GPU NVIDIA, lo spegnimento della porta causato dalla regola `udev` disabiliterà l'output video. In caso di Kernel Panic al boot, il KVM IP andrà a schermo nero prima di mostrare l'errore. Per il recupero è necessario collegare temporaneamente un monitor all'uscita video della scheda madre integrata (iGPU AMD) e una tastiera fisica.

Se l'aggiornamento dell'initramfs causa un blocco (kernel panic) durante l'avvio, è possibile ripristinare il sistema senza utilizzare chiavette USB Live tramite la console initramfs:

1. **Interrompere l'avvio**: Riavvia la macchina e, nel menu del bootloader (GRUB o systemd-boot), premi `e` per modificare i parametri. Aggiungi in fondo alla riga che inizia con `linux` il parametro: `break=top` (poi premi `Ctrl+X` o `F10` per avviare).
2. **Disattivare le regole in RAM**: Il sistema si fermerà in una console busybox prima che `udev` parta. Esegui:
   ```bash
   rm /etc/udev/rules.d/99-remove-nvidia.rules
   rm /etc/modprobe.d/blacklist-nvidia-power.conf
   exit
   ```
   Digitando `exit`, il sistema riprenderà ad avviarsi normalmente.
3. **Ripristino Permanente**: Una volta entrato in Proxmox (via SSH o KVM), elimina definitivamente i file e ricrea l'initramfs pulito:
   ```bash
   rm /etc/udev/rules.d/99-remove-nvidia.rules
   rm /etc/modprobe.d/blacklist-nvidia-power.conf
   update-initramfs -u -k all
   ```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Revisione del piano per approccio dinamico a script.
- **Ultima Azione Completata**: Aggiornamento del piano con vincoli e script di accensione/spegnimento.
- **Prossimo Passo Operativo**: Attesa di conferma sui vincoli per procedere alla realizzazione pratica tramite ansible o comandi diretti.
- **Blocchi/Decisioni Pendenti**: Autorizzazione a procedere.
