---
title: "Piano: Configurazione VM da Gioco su PVE2 (bazzite-nvidia)"
type: plan
status: draft
certified_for_ai: true
created_at: 2026-06-28
tags:
  - "#plan"
  - "#proxmox"
  - "#network"
  - "#gaming"
---

# Piano: Configurazione VM da Gioco su PVE2 (bazzite-nvidia)

> [!IMPORTANT]
> **Nodo Target**: `PVE2` (`10.10.10.21` - Minisforum 795S7)
> **GPU Dedicata**: NVIDIA GeForce RTX 4060 Ti 16GB
> **Sistema Operativo Guest**: Bazzite (variante bazzite-nvidia, basato su Fedora Kinoite, rpm-ostree)
> **Metodo di Controllo**: KVM over IP hardware su VLAN 99 (`192.168.100.22`) collegato direttamente alla GPU.

---

## 1. Analisi dei Vincoli e Decisioni Ingegneristiche

### A. Selezione Bazzite vs SteamOS
SteamOS 3.x supporta stabilmente solo hardware AMD (driver Mesa). Il compositore Gamescope su SteamOS fallisce il rendering su GPU NVIDIA dedicate. **Bazzite** (con l'immagine specifica `bazzite-nvidia`) pre-installa i driver proprietari NVIDIA e patcha Gamescope per funzionare nativamente su Wayland/NVIDIA, rendendola l'unica opzione stabile.

### B. Isolamento hardware: VM vs LXC
Un container LXC costringerebbe ad avere i driver proprietari sull'host Proxmox, impedirebbe l'avvio del kernel immutabile ostree di Bazzite e renderebbe instabile il mapping display per il KVM IP. L'uso di una **VM KVM/QEMU completa con IOMMU PCIe Passthrough (VFIO)** permette di esporre la GPU direttamente alla VM che ne prende il controllo esclusivo sui connettori fisici.

### C. Gestione Energetica e Workaround Firmware
Il firmware BIOS AMI del Minisforum 795S7 (scheda madre BD795i SE) soffre di gravi bug sull'ASPM del link PCIe. I tentativi di transizione dinamica allo stato `D3cold` (spegnimento della GPU a VM offline) causano il crash irreversibile dell'host Proxmox (*Unable to change power state from D3cold to D0, device inaccessible* sfociando in un *CPU BUG soft lockup*).
**Soluzione**: Disabilitazione forzata dello stato di idle profondo della GPU tramite il parametro kernel host:
`vfio-pci.disable_idle_d3=1`
La GPU RTX 4060 Ti rimarrà permanentemente nello stato `D0` (accesa/idle attivo) anche a VM spenta.

### D. Ottimizzazione CPU Pinning (AMD Ryzen 9 7945HX)
Il processore è strutturato su due CCD (Core Complex Dies) da 8 core fisici ciascuno.
Per evitare il degrado delle prestazioni (micro-stuttering) derivante dalla latenza NUMA inter-CCD, la VM sarà confinata a **un singolo CCD (8 core fisici, 16 thread logici)**. I restanti 8 core/16 thread rimarranno ad esclusivo utilizzo dell'host Proxmox.

---

## 2. Fasi di Implementazione

### Fase 1: Configurazione dell'Host Proxmox (PVE2)

#### Step 1.1: Modifica dei parametri del Bootloader
Identificare se PVE2 usa Grub o Systemd-boot (UEFI usa tipicamente systemd-boot).

```bash
# Leggi l'attuale riga di comando del kernel per verifica
cat /proc/cmdline
```

Nel caso di systemd-boot, modificare `/etc/kernel/cmdline` aggiungendo i seguenti parametri in coda alla riga esistente:
`amd_iommu=on iommu=pt pcie_aspm=off pcie_port_pm=off vfio-pci.disable_idle_d3=1`

Se usa GRUB (modifica `/etc/default/grub`):
`GRUB_CMDLINE_LINUX_DEFAULT="quiet amd_iommu=on iommu=pt pcie_aspm=off pcie_port_pm=off vfio-pci.disable_idle_d3=1"`

```bash
# Rigenera la configurazione di avvio (esegui a seconda del bootloader)
proxmox-boot-tool refresh
# oppure se GRUB: update-grub
```

#### Step 1.2: Abilitazione dei moduli VFIO
Aggiungere i moduli necessari a `/etc/modules`:

```bash
cat <<EOF >> /etc/modules
vfio
vfio_iommu_type1
vfio_pci
EOF
```

#### Step 1.3: Isolamento della GPU NVIDIA via Hardware ID
Trovare gli ID PCI del controller grafico e audio NVIDIA:

```bash
lspci -nn | grep -i nvidia
# Risultato tipico:
# 01:00.0 VGA compatible controller [0300]: NVIDIA Corporation AD104 [GeForce RTX 4060 Ti 16GB] [10de:2803] (rev a1)
# 01:00.1 Audio device [0403]: NVIDIA Corporation Device [10de:22be] (rev a1)
```

Creare il file `/etc/modprobe.d/vfio.conf` per associare la scheda a `vfio-pci` fin dall'avvio:

```bash
echo "options vfio-pci ids=10de:2803,10de:22be" > /etc/modprobe.d/vfio.conf
```

Evitare che l'host Proxmox carichi i driver grafici standard:

```bash
cat <<EOF > /etc/modprobe.d/blacklist.conf
blacklist nouveau
blacklist nvidia
blacklist nvidia_drm
blacklist nvidia_modeset
blacklist nvidia_uvm
EOF
```

Rigenerare l'initramfs:

```bash
update-initramfs -u -k all
```

**Riavviare l'host PVE2** per rendere effettive le modifiche.

---

### Fase 2: Creazione e Configurazione della VM Gaming (ID 2500)

Creare una macchina virtuale con le seguenti caratteristiche:

- **ID**: `2500`
- **Machine**: `q35`
- **BIOS**: `OVMF (UEFI)` (aggiungere EFI Disk dedicato su `local-lvm-2tb`)
- **SCSI Controller**: `VirtIO SCSI single`
- **Dischi**: Un disco virtuale da 150GB+ allocato su `local-lvm-2tb`.
- **Rete**: Interfaccia virtuale `VirtIO` collegata al bridge `vmbr20` (VLAN 20).
- **RAM**: `16384 MB` (16 GB), impostando `balloon: 0` (ballooning disabilitato) nel file `.conf`.
- **Display**: `none` (VNC virtuale disabilitato, l'output grafico andrà sul KVM IP fisico).

#### Configurazione CPU Pinning e Affinity
Nel file `/etc/pve/qemu-server/2500.conf`, impostare la topologia per AMD Ryzen:

```text
cpu: host,hidden=1,topoext=on
cores: 16
sockets: 1
numa: 1
```

Per isolare il CCD (core 0-7 fisici e i relativi thread logici 16-23 su Ryzen 7945HX, per un totale di 16 core logici):
Utilizzare un hookscript `/var/lib/vz/snippets/gaming-pinning.sh` per automatizzare il pinning del processo QEMU della VM 2500 sui core 0-7,16-23 tramite `taskset`.

#### Assegnazione PCIe Passthrough della GPU
Configurare l'assegnazione nel file `/etc/pve/qemu-server/2500.conf`:

```text
hostpci0: 0000:01:00,pcie=1,x-vga=1
```
*(Nota: verificare l'indirizzo PCI corretto della RTX 4060 Ti con lspci).*

---

### Fase 3: Installazione di Bazzite ed Integrazione KVM IP

1. Caricare l'immagine ISO `bazzite-nvidia` nel datastore Proxmox.
2. Associare la ISO al lettore CD/DVD virtuale della VM 2500.
3. Collegare fisicamente il dispositivo KVM IP all'uscita HDMI/DisplayPort della RTX 4060 Ti.
4. Avviare la VM `qm start 2500`.
5. Interfacciarsi tramite il KVM IP per visualizzare la console di installazione di Bazzite e completare la procedura guidata su disco.

---

### Fase 4: Registrazione nella Rete del Homelab

#### Step 4.1: Aggiornamento di `rete.json`
Aggiungere la VM gaming e l'extender KVM IP a `rete.json`:

*   **VM Gaming**: ID `bazzite-gaming`, VM ID `2500`, IP statico `10.10.20.35`, VLAN 20.
*   **KVM Extender**: IP `192.168.100.22`, VLAN 99, Stato `Attivo` (collegato fisicamente a GPU PVE2).

#### Step 4.2: Sincronizzazione DNS
Eseguire il playbook Ansible dal Mac Studio per registrare l'alias DNS interno su OPNsense:

```bash
ansible-playbook ansible/playbooks/opnsense_sync_dns.yml
```

---

## 3. Checklist di Verifica e Collaudo

| Step | Oggetto del Test | Comando / Verifica | Risultato Atteso |
|---|---|---|---|
| 1 | Parametri Kernel Host | `cat /proc/cmdline` | Presenza di `vfio-pci.disable_idle_d3=1` |
| 2 | Passthrough VFIO Host | `lspci -nnk -d 10de:` | La GPU NVIDIA mostra `Kernel driver in use: vfio-pci` |
| 3 | Quorum Cluster PVE | `pvecm status` | Quorum acquisito, 3 nodi attivi |
| 4 | Avvio VM | `qm status 2500` | Stato `running` |
| 5 | Output Video | Ispezione visuale da KVM IP | Interfaccia Steam Big Picture fluida a schermo |
| 6 | Risoluzione DNS | `nslookup bazzite-gaming.pindaroli.local` | Risolve a `10.10.20.35` |

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 0 / Stesura del Piano
- **Ultima Azione Completata**: Stesura del piano e integrazione iniziale delle configurazioni
- **Prossimo Passo Operativo**: Attesa di approvazione del piano da parte dell'utente per l'esecuzione
- **Blocchi/Decisioni Pendenti**: Nessuno
