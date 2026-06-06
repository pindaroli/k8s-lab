# GoodTop GT-ST024M — 6-Port 2.5Gb Web Managed Switch

> **Fonte**: Specifiche raccolte da goodtop-tech.com, manuals.plus, eBay listings, e ricerche web.
> Il manuale ufficiale è disponibile solo in formato web su [goodtop-tech.com](https://www.goodtop-tech.com/pages/firmware-and-manual-for-goodtop-products).

---

## 1. Specifiche Tecniche

| Parametro | Valore |
|---|---|
| **Modello** | GT-ST024M |
| **Vendor** | GoodTop |
| **Tipo** | Web Managed Switch (L2) |
| **Chipset** | Realtek RTL8372N |
| **Porte RJ45** | 4 × 2.5GbE |
| **Porte SFP+** | 2 × 10G SFP+ |
| **Backward Compatibility** | 1GbE (auto-negotiation) |
| **Alimentazione** | DC 12V |
| **Consumo (tipico)** | ~12W |
| **Consumo (idle)** | ~1.3W–1.6W |
| **Temperatura operativa** | 0°C – 40°C |
| **Design** | Metal, fanless (silent) |
| **Montaggio** | Fori sul fondo per wall/desk mount |
| **Reset fisico** | ❌ Non presente — solo via Web UI |

## 2. Funzionalità Management

- **VLAN** (IEEE 802.1Q)
- **QoS** (Quality of Service)
- **Link Aggregation** (Static LAG / LACP)
- **Loop Prevention**
- **Port Mirroring**
- **Jumbo Frame** support

## 3. Accesso Web Management

| Parametro | Valore |
|---|---|
| **IP di Default** | `192.168.2.1` |
| **Username** | `admin` |
| **Password** | `admin` |
| **Protocollo** | HTTP (non HTTPS) |

### Procedura di accesso iniziale:
1. Collegare il PC a una porta RJ45 dello switch via cavo Ethernet.
2. Impostare IP statico sul PC nella subnet `192.168.2.x` (es. `192.168.2.100/24`).
3. Aprire il browser e navigare a `http://192.168.2.1`.
4. Effettuare login con `admin` / `admin`.

## 4. Compatibilità SFP+

- Le porte SFP+ supportano moduli **1G**, **2.5G** e **10G**.
- **NON supportano** moduli GPON.
- Compatibilità confermata con moduli BIDI e DAC.

## 5. Firmware e Aggiornamenti

- **Download**: [GoodTop Firmware Page](https://www.goodtop-tech.com/pages/firmware-and-manual-for-goodtop-products)
- **Contatto supporto**: support@goodtop-tech.com

### Procedura di aggiornamento firmware:
> ⚠️ **ATTENZIONE**: Tutti i settaggi vengono persi dopo l'aggiornamento firmware!

1. **Prima dell'update**: Backup configurazione via `Tools > Configuration Backup`.
2. **Pulire i cookie** del browser.
3. **Decomprimere** il file firmware scaricato.
4. **Leggere il manuale** prima dell'aggiornamento.
5. **Non spegnere** lo switch durante l'aggiornamento.
6. **Verificare** che il firmware corrisponda esattamente al modello GT-ST024M. Un firmware errato può causare il brick irreversibile dello switch.

## 6. Note Operative

- Essendo fanless, lo switch dissipa calore attraverso il case metallico. Posizionarlo in un'area con adeguata ventilazione.
- Il reset dello switch è possibile solo tramite interfaccia web (nessun pulsante fisico).
- Le modifiche alla configurazione devono essere salvate esplicitamente (`Tools > Save`) altrimenti vengono perse al riavvio.
