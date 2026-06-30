---
title: "Piano di Espansione Geometrica oliraid ed Evacuazione Special VDEV in Manutenzione Isolata"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-06-27
completed_at: 2026-06-28
tags:
  - "#plan"
  - "#storage"
---

> [!WARNING]
> **PIANO OBSOLETO / SUPERATO**: Questo piano preliminare è stato superato ed è ora obsoleto. La manutenzione dello storage è stata completata con successo ed archiviata.

# Piano di Espansione Geometrica oliraid ed Evacuazione Special VDEV in Manutenzione Isolata

Questo piano descrive le azioni operative per espandere il vdev `raidz2-0` del pool `oliraid` da 4 a 5 dischi e procedere alla successiva evacuazione dello Special VDEV SSD (spostando i blocchi dati superiori a 64K sugli HDD e mantenendo solo i metadati).

**Data creazione**: 2026-06-26
**Stato**: ⚠️ OBSOLETO / SUPERATO (Archiviato il 2026-06-30)

---

## 📊 Topologia Fisica e Logica Iniziale del Pool `oliraid`

| Classe VDEV | Identificatore Logico | Componenti Fisici (PARTUUID) | Capacità Nominale / Utile | Stato Operativo / Allocazione |
| :--- | :--- | :--- | :--- | :--- |
| **Data (RAID-Z2)** | `raidz2-0` | `sdb1` (d2fb5bec-ade4-d34e-b8dd-0a8f61d6bc04)<br>`sdc1` (2b09fe0c-a406-da45-adac-a4f96fedb86d)<br>`sdd1` (c52fa7bb-c542-b045-b78f-b38e51c17407)<br>`sde1` (a1f9e49d-d276-9a48-a2b3-c2d29028adbd) | 14 TB / 12.7 TiB per HDD | ONLINE (Pronto per l'espansione) |
| **Special (Mirror)** | `mirror-2` | `sdf1` (16d908ce-370a-492b-9a57-34981e6c2558)<br>`sdg1` (43bdb63a-f7a7-4a70-b7e2-869dc5f9beee) | 960 GB / 888 GiB utili | ONLINE (Resilvering completato con successo ✅) / 73.5% allocato (653 GiB) |

---

## 🚨 FASE PRELIMINARE: Isolamento Totale del Sistema e Messa in Sicurezza

Prima di eseguire qualsiasi comando di partizionamento o di espansione, il sistema TrueNAS SCALE deve essere isolato logicamente dalla rete e da tutte le attività locali.

### Procedura di isolamento:
1. **Arresto dei servizi di condivisione**: Disattivare l'avvio automatico e arrestare immediatamente i servizi SMB, NFS e iSCSI.
2. **Arresto dello stack applicativo (Docker)**:
   ```bash
   systemctl stop docker
   ```
3. **Disattivazione dei task pianificati**: Sospendere temporaneamente i task di replica, i backup cloud e gli schemi di snapshot periodici.
4. **Verifica dell'assenza di I/O attivo**:
   ```bash
   lsof /mnt/oliraid
   zpool iostat oliraid 1 5
   ```
   L'output di `zpool iostat` deve mostrare operazioni di I/O prossime allo zero.

---

## 💾 FASE A: Espansione del RAID-Z2 da 4 a 5 Dischi

L'espansione del vdev `raidz2-0` viene eseguita integrando la partizione del nuovo HDD da 16 TB (modello Seagate ST16000NM001G-2KK103, provvisoriamente `/dev/sdi`).

### 1. Preparazione e partizionamento del nuovo disco (`/dev/sdi`)
La partizione di swap viene eliminata e viene creata una singola partizione ZFS primaria allineata a 1 MiB (inizio al settore 2048), più una partizione riservata alla fine del disco (replicando il layout nativo di TrueNAS/OpenZFS) usando `sgdisk` in modalità non interattiva per evitare problemi di calcolo manuale sui bordi.

```bash
# Pialla completamente le vecchie firme GPT
sudo sgdisk --zap-all /dev/sdi

# Crea la partizione principale "zfs" partendo dal settore 2048 e lasciando 8MB liberi alla fine
sudo sgdisk -n 1:2048:-8M -t 1:BF01 -c 1:"zfs" /dev/sdi

# Crea la piccola partizione riservata negli ultimi 8MB
sudo sgdisk -n 9:0:0 -t 9:BF07 -c 9:"Reserved" /dev/sdi

# Ricarica la tabella nel kernel
sudo partprobe /dev/sdi

# Bonifica eventuali firme exFAT/ext4 preesistenti all'interno della nuova partizione per non bloccare l'attach di ZFS
sudo wipefs -a /dev/sdi1
```

Per ottenere il `PARTUUID` persistente (NOTA: usare `sgdisk` rigenera un nuovo UUID, ignorare i vecchi):
```bash
export NEW_PARTUUID=$(blkid -s PARTUUID -o value /dev/sdi1)
echo "Il PARTUUID persistente da utilizzare è: ${NEW_PARTUUID}"
```

### 2. Esecuzione del comando `zpool attach` per l'espansione
Una volta completato il resilvering del vdev speciale e verificata la salute globale del pool:
```bash
zpool attach oliraid raidz2-0 /dev/disk/by-partuuid/${NEW_PARTUUID}
```

### 3. Monitoraggio
```bash
zpool status oliraid
```
Il pool torna allo stato ONLINE al termine dell'operazione.

### 4. Impatto matematico sulla parità e ridistribuzione dei blocchi
- **Geometria precedente (4 dischi)**: $2:2$ (2 dati, 2 parità). Efficienza dello spazio: $50\%$.
- **Geometria espansa (5 dischi)**: $3:2$ (3 dati, 2 parità). Efficienza dello spazio: $60\%$.
- Per ridistribuire uniformemente i dati esistenti sulla nuova larghezza a 5 dischi e sbloccare la nuova efficienza del 60%, si esegue la riscrittura dei blocchi con `zfs rewrite`.

---

## 🧹 FASE B: Evacuazione dello Special VDEV

Lo Special VDEV mirror di SSD ospita circa 653 GB di dati a causa della precedente policy `special_small_blocks=1M`. Con la policy impostata a `64K`, l'obiettivo è migrare i blocchi dati superiori a 64 KiB verso gli HDD, mantenendo solo i metadati e i file minori di 64 KiB sugli SSD.

### 1. Eliminazione snapshot per prevenire Space Amplification
La riscrittura in-place senza eliminare le snapshot manterrebbe i vecchi blocchi sugli SSD, causando saturazione. Eliminiamo ricorsivamente tutte le snapshot del dataset target prima di avviare la riscrittura:
```bash
zfs destroy -r oliraid/arrdata@%
```

### 2. Esecuzione di `zfs rewrite`
Una riscrittura ricorsiva globale su tutto il dataset `oliraid/arrdata`:
```bash
zfs rewrite -rvx /mnt/oliraid/arrdata
```
I blocchi di dimensioni superiori a 64K verranno riscritti sugli HDD, mentre i metadati rimarranno sullo Special VDEV.

---

## 📋 Piano Operativo "Zero-Risk" (Passo-Passo)

### Sotto-piano A: Espansione del RAID-Z2 da 4 a 5 Dischi

#### Passo A.1: Arresto dei servizi e isolamento di TrueNAS
- **Azione**: Accedere alla WebUI di TrueNAS, andare in *System Settings -> Services* e disattivare l'avvio automatico e arrestare i servizi SMB, NFS e iSCSI.
- **CLI**: Arrestare lo stack dei container:
  ```bash
  systemctl stop docker
  ```
- **Verifica**: Verificare che nessun processo acceda al pool:
  ```bash
  lsof /mnt/oliraid
  ```
  L'output deve essere vuoto.

#### Passo A.2: Convalida dello stato di salute del pool
- **Azione**: Verificare lo stato del pool:
  ```bash
  zpool status oliraid
  ```
- **Verifica**: Lo stato deve essere `ONLINE`, no scan/resilver attivo, errori di CKSUM a 0 per tutti i dischi.

#### Passo A.3: Preparazione fisica e partizionamento di `/dev/sdi`
- **Comandi**:
  ```bash
  sudo sgdisk --zap-all /dev/sdi
  sudo sgdisk -n 1:2048:-8M -t 1:BF01 -c 1:"zfs" /dev/sdi
  sudo sgdisk -n 9:0:0 -t 9:BF07 -c 9:"Reserved" /dev/sdi
  sudo partprobe /dev/sdi
  ```
- **Bonifica firme residue (Variante)**: Se il disco conteneva filesystem come exFAT (il cui magic number a offset 2048 può bloccare l'attach di ZFS), bonificare la partizione:
  ```bash
  sudo wipefs -a /dev/sdi1
  ```
- **Risoluzione udev (Variante TrueNAS)**: Se il link non compare in `/dev/disk/by-partuuid/`, forzare l'aggiornamento o riavviare il nodo (TrueNAS middleware può mantenere in stato busy il device):
  ```bash
  sudo udevadm trigger && sudo udevadm settle
  # Se ancora assente, riavviare TrueNAS (sudo reboot)
  ```
- **Verifica**:
  Recuperare il `PARTUUID` aggiornato:
  ```bash
  export NEW_PARTUUID=$(blkid -s PARTUUID -o value /dev/sdi1)
  echo "PARTUUID rilevato: ${NEW_PARTUUID}"
  ```

#### Passo A.4: Avvio dell'espansione geometrica
- **Comando**:
  ```bash
  zpool attach oliraid raidz2-0 /dev/disk/by-partuuid/${NEW_PARTUUID}
  ```
- **Verifica**:
  ```bash
  zpool status oliraid
  ```
  Il nuovo disco deve apparire sotto `raidz2-0` e la riga `expand` deve mostrare il progresso della copia dello stripe.

#### Passo A.5: Monitoraggio protetto fino al completamento
- **Azione**: Usare `tmux` per monitorare l'avanzamento ed evitare disconnessioni di rete (la variabile `TERM` previene errori "missing or unsuitable terminal" su emulatori come Ghostty):
  ```bash
  TERM=xterm-256color tmux new -s monitor_espansione
  watch -n 10 "zpool status oliraid | grep -A 8 -i 'expand'"
  ```
  *(Premere Ctrl+B e poi D per scollegarsi. Per ricollegarsi: `TERM=xterm-256color tmux attach -t monitor_espansione`).*
- **Verifica finale**: La sezione `expand` deve scomparire, il pool deve tornare `ONLINE`. Verificare l'aumento di capacità:
  ```bash
  zpool list -v oliraid
  ```

---

### Sotto-piano B: Evacuazione dello Special VDEV e Ribilanciamento Parità

#### Passo B.1: Verifica della proprietà del dataset
- **Comando**:
  ```bash
  zfs set special_small_blocks=64K oliraid/arrdata
  ```
- **Verifica**: Confermare l'ereditarietà:
  ```bash
  zfs get -r special_small_blocks oliraid/arrdata
  ```

#### Passo B.2: Purga preventiva e totale delle snapshot
- **Comando**:
  ```bash
  zfs destroy -r oliraid/arrdata@%
  ```
- **Verifica**: Verificare che non ci siano snapshot residue:
  ```bash
  zfs list -t snapshot -r oliraid/arrdata
  ```
  L'output deve essere: `no datasets available`.

#### Passo B.3: Esecuzione della riscrittura globale
- **Comandi**:
  ```bash
  TERM=xterm-256color tmux new -s evacuazione_rebalance
  zfs rewrite -rvx /mnt/oliraid/arrdata
  ```
  *(Premere Ctrl+B e poi D per scollegarsi).*
- **Verifica in tempo reale**:
  ```bash
  watch -n 10 "zpool list -v oliraid"
  ```
  Verificare la riduzione progressiva della colonna `ALLOC` per `mirror-2` (special) sotto i 653 GB e l'aumento della colonna `ALLOC` di `raidz2-0`.

#### Passo B.4: Verifica finale e ripristino dei servizi
- **Comandi**:
  ```bash
  zpool scrub oliraid
  zpool status oliraid
  ```
  Lo scrub deve completarsi con 0 errori.
  Riattivare lo stack applicativo:
  ```bash
  systemctl start docker
  ```
  Abilitare e riavviare i servizi SMB, NFS e iSCSI dalla WebUI di TrueNAS SCALE.

---

## Relazioni
- Riguarda: [[TrueNAS]] (pool `oliraid`, vdev `special`)
- Impatta temporaneamente: [[Servarr]], [[Tdarr]], PBS
- Documentazione storage: [[Storage_Registry]]
