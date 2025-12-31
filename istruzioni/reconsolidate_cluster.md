# Guida al Reconsolidamento del Cluster Proxmox

Questa guida contiene le istruzioni passo-passo per ripristinare il corretto funzionamento del cluster Proxmox dopo il cambio degli indirizzi IP di `pve2` (ora `10.10.10.21`) e `pve3` (ora `10.10.10.31`).

## Prerequisiti
- Accesso SSH (`root`) a tutti i nodi: `pve`, `pve2`, `pve3`.
- Assicurati di avere una copia di backup di `/etc/pve/corosync.conf` e `/etc/corosync/corosync.conf` se possibile.

---

## 1. Aggiornamento `/etc/hosts` (Tutti i Nodi)

Esegui questi passaggi su **tutti e tre i nodi** per garantire che la risoluzione dei nomi locale sia corretta.

1.  Apri il file `/etc/hosts`:
    ```bash
    nano /etc/hosts
    ```
2.  Individua le righe relative a `pve2` e `pve3` e aggiornale con i nuovi IP:
    ```text
    10.10.10.21 pve2.pindaroli.org pve2
    10.10.10.31 pve3.pindaroli.org pve3
    ```
    *(Lascia invariato `pve` che dovrebbe essere `10.10.10.11`)*
3.  Salva e chiudi (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

## 2. Aggiornamento Configurazione Cluster (Solo su `pve`)

Collegati al nodo master **`pve`** (10.10.10.11).

### A. Verifica e Forzatura Quorum
Verifica lo stato del cluster:
```bash
pvecm status
```
Se il cluster non ha il quorum (es. vedi "Activity blocking" o nodi offline), forza temporaneamente il quorum aspettato a 1 per poter modificare i file di configurazione (`/etc/pve` diventa scrivibile):
```bash
pvecm expected 1
```

### B. Modifica `corosync.conf`
Modifica il file di configurazione principale del cluster.
1.  Apri il file:
    ```bash
    nano /etc/pve/corosync.conf
    ```
2.  Apporta le seguenti modifiche:
    -   **Incrementa** `config_version` di 1 (es. da `5` a `6`).
    -   Aggiorna `ring0_addr` per i nodi modificati.

    Il file dovrebbe apparire simile a questo (assicurati che `nodeid` e `name` corrispondano alla TUA configurazione reale):
    ```text
    logging {
      debug: off
      to_syslog: yes
    }

    nodelist {
      node {
        name: pve
        nodeid: 1
        ring0_addr: 10.10.10.11
      }
      node {
        name: pve2
        nodeid: 2
        ring0_addr: 10.10.10.21  <-- AGGIORNATO
      }
      node {
        name: pve3
        nodeid: 3
        ring0_addr: 10.10.10.31  <-- AGGIORNATO
      }
    }

    quorum {
      provider: corosync_votequorum
    }

    totem {
      cluster_name: tuo-cluster-name
      config_version: 6          <-- INCREMENTATO
      interface {
        linknumber: 0
      }
      ip_version: ipv4-6
      link_mode: passive
      secauth: on
      version: 2
    }
    ```
3.  Salva e chiudi.

---

## 3. Propagazione delle Modifiche

Poiché il cluster systemfile (`pmxcfs`) potrebbe non essere in grado di sincronizzare i file verso i nodi che hanno cambiato IP (perché corosync sta ancora cercando i vecchi IP), è probabile che tu debba aggiornare manualmente anche gli altri nodi.

### Tentativo Automatico (su `pve`)
Prova a riavviare corosync su `pve`:
```bash
systemctl restart corosync
```
Controlla se gli altri nodi si riconnettono (`pvecm status`). Se rimangono offline o rossi dopo 1-2 minuti, procedi con l'aggiornamento manuale qui sotto.

### Aggiornamento Manuale (su `pve2` e `pve3`)
**SE** la modifica automatica non si è propagata:

1.  Collegati via SSH a **`pve2`** (dovrebbe rispondere sul nuovo IP `10.10.10.21` se la rete è configurata, altrimenti accedi via console o vecchio IP se ancora attivo).
2.  Modifica il file LOCALE (non quello in /etc/pve, ma quello in /etc/corosync):
    ```bash
    nano /etc/corosync/corosync.conf
    ```
3.  Incolla **ESATTAMENTE** lo stesso contenuto che hai salvato su `pve` (inclusi IPs corretti e `config_version` incrementato).
4.  Rilancia il servizio:
    ```bash
    systemctl restart corosync
    ```
5.  Ripeti gli stessi passaggi per **`pve3`** (IP `10.10.10.31`).

---

## 4. Verifica Finale

Torna su `pve` e controlla lo stato:
```bash
pvecm status
```
Dovresti vedere:
-   Tutti i 3 nodi con Status **Online**.
-   Quorum: **OK**.

🎉 Cluster riconsolidato!
