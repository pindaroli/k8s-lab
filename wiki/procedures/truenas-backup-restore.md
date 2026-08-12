---
title: "Procedura: Backup e Ripristino della Configurazione di TrueNAS"
type: procedure
status: active
certified_for_ai: true
created_at: 2026-08-12
tags:
  - "#procedure"
  - "#storage"
  - "#truenas"
---

# Procedura: Backup e Ripristino della Configurazione di TrueNAS

Questa procedura documenta i passaggi per effettuare il backup a freddo della configurazione di TrueNAS SCALE e il relativo ripristino su nuovo hardware (migrazione bare metal), superando le criticità legate al cambio di controller disco e alla ridenominazione delle interfacce di rete fisiche.

---

## 🛠️ Fase 1: Esportazione e Backup Locale (sul Mac Studio)

Prima di spegnere la VM o il vecchio server TrueNAS, è necessario estrarre i file di configurazione essenziali e salvarli localmente sul Mac Studio.

### A. Backup del database e del seed delle password (CLI)
Il database SQLite di TrueNAS (`freenas-v1.db`) e il seed di crittografia per le password (`pwenc_secret`) si trovano in `/data/`. 

Esegui i seguenti comandi dal terminale del Mac Studio:

1. Crea l'archivio compresso temporaneo direttamente su TrueNAS:
```bash
ssh -o BatchMode=yes olindo@10.10.10.50 "sudo tar -cvf /tmp/truenas-config.tar -C /data freenas-v1.db pwenc_secret"
```

2. Modifica i permessi per renderlo leggibile dall'utente `olindo`:
```bash
ssh -o BatchMode=yes olindo@10.10.10.50 "sudo chmod 644 /tmp/truenas-config.tar"
```

3. Scarica il file sul Mac Studio all'interno della cartella dei backup del progetto:
```bash
scp olindo@10.10.10.50:/tmp/truenas-config.tar /Users/olindo/prj/k8s-lab/backups/truenas-config.tar
```

4. Rimuovi il file temporaneo su TrueNAS:
```bash
ssh -o BatchMode=yes olindo@10.10.10.50 "sudo rm /tmp/truenas-config.tar"
```

### B. Esportazione delle chiavi ZFS per i dataset crittografati (GUI)
Questo passaggio è fondamentale se utilizzi la crittografia nativa ZFS:
1. Accedi alla WebUI di TrueNAS -> **Datasets**.
2. Clicca su **ZFS Encryption** -> **Export All Keys**.
3. Salva il file JSON risultante in un luogo sicuro sul Mac Studio.

### C. Esportazione (Disconnect) dei Pool di Storage (GUI)
Per evitare che il nuovo sistema rilevi i pool come "attivi su un altro sistema" (richiedendo un import forzato):
1. Vai su **Storage**.
2. Clicca su **Export/Disconnect** per il pool `oliraid` e il pool `stripe`.
3. **ATTENZIONE**: **NON** spuntare le opzioni *"Destroy data on this pool"* o *"Delete share configurations"*. Clicca semplicemente su conferma per scollegarli in modo pulito.

---

## 🖥️ Fase 2: Configurazione Hardware UEFI Bare Metal

Prima di avviare il sistema operativo sul nuovo server fisico:
1. Accedi alla schermata di configurazione **BIOS/UEFI** della nuova scheda madre (ASRock X570M Pro4).
2. Naviga nella configurazione dei controller di archiviazione (SATA/Storage Configuration).
3. Assicurati che la modalità SATA sia impostata su **AHCI**.
   * > [!CAUTION]
     > Se la modalità è impostata su *RAID* (es. AMD RAID / NVMe RAID), la scheda madre proverà ad applicare metadati proprietari sui dischi, impedendo a ZFS di riconoscere correttamente le etichette dei dischi e rischiando di corrompere i dati.

---

## 📥 Fase 3: Installazione Pulita e Caricamento Configurazione

1. Effettua un'installazione pulita di TrueNAS SCALE sul nuovo disco di boot bare metal (NVMe 128GB).
2. Dalla console iniziale del server, configura una connettività IP provvisoria (es. `10.10.10.50/24`) per abilitare l'accesso alla GUI.
3. Apri il browser sul Mac Studio e naviga su `https://10.10.10.50`.
4. Vai su **System Settings > General > Manage Configuration**.
5. Clicca su **Upload File** e seleziona il file `truenas-config.tar` salvato sul Mac Studio.
6. Conferma l'upload. Il sistema ripristinerà i file in `/data/` e si **riavvierà automaticamente**.

---

## 🔌 Fase 4: Configurazione Interfacce di Rete tramite Console Setup (Fisica)

Dopo il riavvio, il server risulterà **irraggiungibile via rete** perché il database importato tenta di mappare la configurazione sulle interfacce virtuali non più esistenti (es. `ens18`).

Collega un monitor e una tastiera fisici al server (o usa la console IPMI/OOB) e segui questi passi:

1. Nel menu testuale di **Console Setup**, digita **`1`** (*Configure network interfaces*) e premi **Invio**.
2. Ti verrà proposto di eliminare le interfacce inattive del vecchio database (es. `ens18`, `ens19`). Digita **`y`** (yes) e conferma per ripulire il sistema.
3. Verrà mostrato l'elenco delle schede di rete fisiche realmente presenti (es. `enp1s0f0` per la Intel X710 10G o `eno1` per la porta integrata). Digita il numero della scheda fisica collegata allo switch e premi **Invio**.
4. Alla richiesta `Configure interface for DHCP? (y/n):` digita **`n`** (no) e premi **Invio**.
5. Alla richiesta `Configure IPv4? (y/n):` digita **`y`** (yes) e premi **Invio**.
6. Inserisci l'indirizzo IP statico definitivo nella notazione CIDR:
   `10.10.10.50/24`
7. Alla richiesta `Configure IPv6? (y/n):` digita **`n`** (no) e premi **Invio**.
8. Alla richiesta di conferma per applicare le modifiche e riavviare i servizi di rete, digita **`y`** (yes) e premi **Invio**.

A questo punto la console mostrerà la scritta:
`The web user interface is at: https://10.10.10.50`
E la GUI sarà nuovamente accessibile dal Mac Studio.

---

## 💾 Fase 5: Importazione dei Pool e Decrittografia

1. Accedi alla WebUI di TrueNAS su `https://10.10.10.50` (usando le **vecchie credenziali admin** storiche).
2. Vai su **Storage**.
3. Se i pool non sono stati rilevati automaticamente, clicca su **Import Pool**, seleziona `oliraid` (e poi `stripe`) e conferma.
4. Per sbloccare i dataset crittografati, vai nella sezione **Datasets**, seleziona il pool o dataset bloccato, clicca su **Encryption > Import Key** e carica il file JSON salvato nella Fase 1-B.
