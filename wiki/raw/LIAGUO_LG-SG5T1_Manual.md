# LIANGUO LG-SG5T1(WEB) — 5-Port 2.5GbE Managed Switch

> **Fonte**: Specifiche raccolte da manuals.plus, ServeTheHome, e ricerche web.
> Il manuale ufficiale è disponibile solo su [Manuals+](https://manuals.plus/lianguo/lg-sg5t1-web-5-port-2-5g-managed-switch-instructions).
> Modello alternativo/OEM: **ZX-SWTGW215AS**

---

## 1. Specifiche Tecniche

| Parametro | Valore |
|---|---|
| **Modello** | LG-SG5T1(WEB) |
| **Vendor** | LIANGUO (abbreviato LIAGUO) |
| **Tipo** | Web Managed Switch (L2) |
| **Chipset** | Realtek (famiglia RTL8xxx) |
| **Porte RJ45** | 5 × 2.5GbE |
| **Porte SFP+** | 1 × 10G SFP+ |
| **Switch Capacity** | 45 Gbps |
| **MAC Address Table** | 4K |
| **Forwarding Mode** | Store and Forward |
| **Alimentazione** | DC 12V / 1A (Input: AC 100-240V, 50/60Hz) |
| **Design** | Fanless (silent) |
| **Temperatura operativa** | 0°C – 40°C |

### Standard Supportati
- IEEE 802.3
- IEEE 802.3u
- IEEE 802.3x (Flow Control)
- IEEE 802.3ab (Gigabit Ethernet)
- IEEE 802.3bz (2.5G/5GBASE-T)

## 2. Funzionalità Management (versione WEB)

La versione "(WEB)" supporta:
- **VLAN** (Virtual LAN configuration)
- **QoS** (Quality of Service)
- **Port Aggregation** (Link Aggregation)
- **Port Mirroring**
- **Flow Control**

> ⚠️ **Nota**: Esiste anche una versione **unmanaged** dello stesso switch (senza "(WEB)" nel nome). La versione unmanaged è plug-and-play e non ha interfaccia di gestione web.

## 3. Interfaccia Fisica

### LED Indicators
Ogni porta RJ45 ha due LED:
- **Verde**: Link/attività a 2.5G
- **Giallo**: Link/attività a 10/100/1000M

### Porte
- **5 × RJ45 2.5GbE**: Per dispositivi di rete (server, PC, altri switch)
- **1 × 10G SFP+**: Per uplink ad alta velocità (fibra ottica o DAC)

## 4. Accesso Web Management

| Parametro | Valore |
|---|---|
| **IP di Default** | `192.168.2.1` (verificare etichetta sul fondo) |
| **Username** | `admin` |
| **Password** | `admin` oppure `system` (verificare etichetta) |
| **Protocollo** | HTTP (non HTTPS) |

### Procedura di accesso iniziale:
1. Collegare il PC direttamente a una porta RJ45 dello switch.
2. Impostare IP statico sul PC nella subnet dello switch (es. `192.168.2.100/24`).
3. Aprire il browser e navigare all'IP di default.
4. Effettuare login con le credenziali di default.

## 5. Note Operative

### Salvataggio Configurazione
Le modifiche sono **volatili** sui chipset Realtek. Dopo ogni modifica:
1. Navigare alla sezione **Tools** o **System**.
2. Cliccare **Save** o **Reboot** per rendere la configurazione persistente.
3. Senza salvataggio esplicito, le modifiche vengono perse al riavvio/power cycle.

### Configurazione VLAN (specifica per la nostra infrastruttura)
Per la corretta configurazione VLAN nel contesto dell'homelab GEMINI (vedi [[oob-hardening-validation]]):
- La VLAN deve essere **creata staticamente** nel database VLAN dello switch.
- Le porte Trunk devono avere la VLAN aggiunta come **Tagged**.
- Le porte Access devono avere il **PVID** configurato correttamente.
- **NON** creare SVI (interfacce VLAN IP) su VLAN 99 (OOB).

### Firmware
- Utilizzare solo firmware fornito dal venditore o dal produttore.
- Il chipset è della famiglia Realtek, condiviso con brand come Horaco e Hasivo.
- Verificare il modello esatto prima di aggiornare — firmware errato = brick irreversibile.

### Power Adapter
- **Input**: AC 100-240V, 50/60Hz
- **Output**: DC 12V, 1A
- Assicurarsi che l'alimentatore fornisca potenza stabile per evitare problemi di connettività.

## 6. Identificazione Hardware

Lo switch è venduto anche sotto altri nomi brand (white-label):
- **LIANGUO** LG-SG5T1(WEB)
- **ZX-SWTGW215AS**
- Hardware condiviso con modelli **Horaco** e **Hasivo**

Per identificare la versione esatta, verificare l'etichetta stampata sul fondo del dispositivo.
