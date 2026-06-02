# Guida Offline: Sblocco Porta 2 Emulex CN1200E (Modalità NIC) tramite UEFI Shell

Questa guida ti permetterà di operare in autonomia e senza connessione a internet direttamente sulla console fisica del mini PC.

> [!WARNING]
> **REQUISITO FONDAMENTALE**: Hai bisogno di una tastiera e un monitor collegati direttamente al mini PC PVE3.

---

## 1. Avvio della Shell UEFI tramite Ventoy

1. **Inserisci la chiavetta USB Ventoy** nel mini PC PVE3 (a PC spento).
2. **Accendi il mini PC** e premi ripetutamente il tasto del menu di Boot (di solito `F11`, `F12`, `F8` o `Canc` sui mini PC).
3. Seleziona la chiavetta USB dall'elenco (potrebbe chiamarsi "UEFI: USB" o simile).
4. Arriverai al **menu principale di Ventoy** (schermata azzurra).
5. Premi il tasto **`F2`** sulla tastiera per entrare nella modalità *Localboot / Browse*.
6. Naviga tra le cartelle fino a trovare il file **`shellx64.efi`** che hai copiato prima, selezionalo e premi **Invio**.
7. Apparirà una schermata nera con scritte in giallo e bianco. Se appare un countdown ("Press ESC in X seconds to skip startup.nsh"), **premi ESC**.
8. Ti troverai davanti al prompt dei comandi UEFI: `Shell>` (o `FS0:\>`).

---

## 2. Identificazione della Scheda Emulex

Ora sei nel "terminale hardware" della scheda madre. Attenzione al layout della tastiera (se è USA, il trattino `-` potrebbe trovarsi vicino allo zero).

1. Digita il seguente comando e premi Invio:
   ```text
   drivers
   ```
2. Apparirà una lunga lista a colonne. Cerca la riga che contiene una dicitura simile a **`Emulex SCSI Pass Thru Driver`**, **`Elxcli301a0`** oppure **`Emulex FCoE/NIC`**.
3. Guarda la primissima colonna a sinistra di quella riga: ci sarà un numero esadecimale (ad esempio `A9`, `1B`, `2C`, `A2`).
4. **Appuntati questo numero**: è il tuo **`DRIVER_ID`**.

---

## 3. Identificazione della Porta 2

1. Digita il seguente comando e premi Invio:
   ```text
   drvcfg
   ```
2. Apparirà un'altra lista. Scorri e cerca le righe che hanno il tuo **`DRIVER_ID`** nella prima colonna.
3. Se hai due porte sulla scheda, vedrai due righe per quel `DRIVER_ID`. Accanto, nella terza o quarta colonna, ci sarà una voce che inizia con `Ctrl: ` seguita da un altro codice esadecimale (es. `Ctrl: B6` e `Ctrl: B7`).
4. Di norma, la Porta 1 ha il codice più basso (es. `B6`) e la Porta 2 ha quello più alto (es. `B7`).
5. **Appuntati il codice della Porta 2**: è il tuo **`CTRL_ID`**.

---

## 4. Ingresso nel Menu di Configurazione Emulex

1. Digita questo comando usando i due codici che ti sei appuntato prima (sostituisci i valori dell'esempio con i tuoi veri) e premi Invio:
   ```text
   drvcfg -s <DRIVER_ID> <CTRL_ID>
   ```
   *(Esempio: se il Driver ID è A9 e il Ctrl ID è B7, digita: `drvcfg -s A9 B7`)*

2. Magia! Lo schermo si pulirà e si aprirà il **menu nativo interno** della scheda Emulex.

---

## 5. Modifica della Personalità (da CNA a NIC)

Ora usa le **frecce della tastiera** per muoverti nel menu:

1. Seleziona **`Controller Configuration`** e premi Invio.
2. Seleziona **`Adapter Personality Configuration`** (o voce molto simile) e premi Invio.
3. Troverai un'opzione che indica la modalità attuale (probabilmente è su `FCoE`, `CNA`, o `UMC`).
4. Evidenzia l'opzione e premi **Invio**. Ti si aprirà una lista a tendina.
5. Scegli **`NIC`** e premi Invio per confermare.
6. Premi il tasto indicato in fondo allo schermo per salvare (spesso è **`F10`** per *Save and Exit*). Se chiede "Are you sure?", conferma con `Y` o Invio.
7. Continua a premere `ESC` fino a quando non torni al prompt nero `Shell>`.

---

## 6. Il "Cold Boot" (FONDAMENTALE)

Affinché l'ASIC Emulex salvi le impostazioni in modo permanente nella NVRAM, il server deve essere privato completamente della corrente. **Un riavvio normale NON basta.**

1. Dalla shell, spegni il mini PC tenendo premuto fisicamente il tasto di accensione (oppure digita `reset` se vuoi che si riavvii e spegnilo al volo).
2. **STACCA LO SPINOTTO DELL'ALIMENTATORE** dal mini PC (oppure togli la spina dal muro).
3. **Attendi almeno 30 secondi esatti**. (Questo permette ai condensatori di scaricarsi e alla scheda Emulex di spegnersi totalmente, abbandonando i vecchi registri).
4. Togli la chiavetta USB Ventoy.
5. Ricollega l'alimentatore.
6. Riaccendi il mini PC e lascia avviare Proxmox regolarmente.

## 7. Verifica Finale
Al termine del riavvio, il link sulla Porta 2 dello switch si accenderà e Proxmox potrà finalmente negoziare la connessione 10G senza più loop di "Optics faulted".
