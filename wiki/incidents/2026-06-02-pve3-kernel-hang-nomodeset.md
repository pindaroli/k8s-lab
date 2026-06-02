# Incident: PVE3 Kernel Hang on Ryzen AI (nomodeset)
**Date**: 2026-06-02
**Status**: RESOLVED (Boot parameter patched persistently via systemd-boot)
**Resolution Date**: 2026-06-02
**Severity**: High (Node unreachable, boot hang, and cluster quorum failure)

## 🔍 Diagnosis
Durante l'upgrade in-place del nodo **PVE3** (basato su CPU AMD Ryzen AI Strix) a Proxmox VE 9.2 (kernel `7.0.6-2-pve`), la console OOB è andata offline e lo switch non mostrava alcuna attività di link sulla scheda 10G. Collegando uno schermo fisico, si è riscontrato un blocco completo del kernel (kernel hang / schermo nero) subito dopo il caricamento, dovuto a un'incompatibilità del driver grafico `amdgpu` con il Kernel 7.x durante l'inizializzazione del Kernel Mode Setting (KMS).

È stato necessario un intervento manuale alla console fisica per forzare l'avvio temporaneo inserendo il parametro `nomodeset`.

### Il Secondo Blocco (Mancata Persistenza)
Al riavvio successivo, il nodo si è bloccato nuovamente. L'analisi ha rivelato che la modifica permanente effettuata in `/etc/default/grub` (seguita da `update-grub`) era stata completamente ignorata.

### Root Cause
1. **Incompatibilità KMS**: Il kernel PVE 7.x fallisce l'inizializzazione grafica sulla CPU AMD Ryzen AI Strix in mancanza del parametro `nomodeset`.
2. **Bootloader Mismatch**: Il sistema PVE3 è avviato in modalità UEFI tramite **systemd-boot** (gestito da `proxmox-boot-tool`), mentre GRUB non è attivo. Qualsiasi modifica in `/etc/default/grub` non ha alcun effetto pratico sul boot del sistema.

---

## 🛠️ Planned Resolution (Manual)
Per risolvere in modo permanente, i parametri del kernel devono essere configurati nella sorgente corretta per `systemd-boot`.

### Passaggi eseguiti su PVE3:
1. Accesso in SSH al canale di servizio OOB (`192.168.100.31`).
2. Modifica del file `/etc/kernel/cmdline` aggiungendo il parametro `nomodeset` alla fine dell'unica riga:
   ```text
   root=ZFS=rpool/ROOT/pve-1 boot=zfs nomodeset
   ```
3. Refresh delle partizioni EFI tramite lo strumento ufficiale:
   ```bash
   proxmox-boot-tool refresh
   ```
4. Esecuzione del reboot del nodo.

---

## ✅ Resolution Summary
- **Applied by**: Antigravity & User
- **Timestamp**: 2026-06-02T08:48:00+02:00
- **Action**: Aggiunto `nomodeset` in `/etc/kernel/cmdline` e rinfrescate le partizioni EFI.
- **Verification**:
  - Il nodo si è riavviato autonomamente in modalità headless (senza alcun intervento allo schermo).
  - Il comando `cat /proc/cmdline` ha confermato il corretto caricamento in memoria:
    `initrd=\EFI\proxmox\7.0.6-2-pve\initrd.img-7.0.6-2-pve root=ZFS=rpool/ROOT/pve-1 boot=zfs nomodeset`
  - Il cluster Corosync si è ricomposto automaticamente raggiungendo il quorum con PVE1 (`pvecm status` → Quorate: Yes).

---

## 🛡️ Future Prevention
- **Bootloader Awareness**: Sui nodi Proxmox con boot UEFI, verificare sempre lo stato del bootloader tramite `proxmox-boot-tool status` prima di configurare i parametri del kernel.
- **Aggiornamento Policy**: Non utilizzare `/etc/default/grub` come impostazione di default per il tuning del kernel dell'Homelab, in quanto la maggior parte dei nuovi nodi UEFI utilizzerà systemd-boot.

## 🔗 References
- [[Talos_Cluster]]
- [[OPNsense]]
- [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json)
- [todo.md](file:///Users/olindo/prj/k8s-lab/todo.md)
