---
title: "FreeRADIUS solo per il Wi-Fi AP11000"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-24
tags:
  - "#plan"
  - "#network"
  - "#security"
  - "#opnsense"
---

# FreeRADIUS solo per il Wi-Fi AP11000

FreeRADIUS (`os-freeradius` 1.10.2) è sul firewall e accetta autenticazioni solo dal Cudy AP11000 (`10.10.20.103`). Il cavo sulla VLAN 20 non usa 802.1X.

## Stato

- Firmware AP verificato: `2.5.13-20260706-091052` (cifratura Enterprise presente).
- Servizio in ascolto su UDP 1812 e 1813. EAP predefinito: PEAP, tunnel interno MSCHAPv2. Accounting su SQLite.
- Client RADIUS unico: `ap11000`, `10.10.20.103/32`.
- Firewall su TRANSIT (`opt4` / `igc1`), prima di «Allow All Transit»:
  - pass UDP 1812-1813 da `10.10.20.103` verso `(self)`
  - block UDP 1812-1813 da chiunque altro verso `(self)`
- Un probe UDP da un host che non è l'AP è stato scartato (contatore della regola di block).
- `olindo`: nessuna `Simultaneous-Use`.
- `patrizia`: `Simultaneous-Use := 1`. Una sessione già aperta produce Access-Reject con «You are already logged in - access denied», disabilita l'utente e invia il messaggio al bot Telegram del lab (`chat_id` 554585346). Lo sblocco è manuale: riabilitare l'utente in Services → FreeRADIUS → Users.
- Password utenti e secret del client `ap11000` stanno in `/conf/config.xml` e quindi nel backup. Il promemoria `/root/freeradius-ap11000-credentials.txt` non è necessario al servizio.
- Token e `chat_id` Telegram stanno in `/conf/config.xml`, sezione `<patriziaLock>` (sorella di `<freeradius>`, non al suo interno). `patrizia_lock.py` legge secret e IP dal client `ap11000` e Telegram da quella sezione. `/usr/local/etc/patrizia_lock.env` è stato rimosso.
- Il taglio dell'SSID `Eternal` a WPA2-Enterprise e l'SSID `Eternal-Device` (WPA3-SAE, stessa password di oggi, VLAN 20, senza RADIUS) si fanno sulla GUI dell'AP. Il server RADIUS è pronto; la GUI Cudy richiede il login amministratore dell'AP.

## Verifica fatta

`radtest` verso `127.0.0.1` con un client temporaneo poi rimosso: `olindo` riceve Access-Accept. Con una riga `radacct` aperta per `patrizia`, il login successivo è Access-Reject, `enabled` passa a 0 e `/var/log/patrizia_lock.log` registra il motivo. Il client `127.0.0.1` non resta in `clients.conf`. Dopo il test `patrizia` è stata riabilitata.

## Dopo una reinstallazione

Il backup di OPNsense riporta utenti, secret del client `ap11000`, la sezione `<patriziaLock>` e le regole firewall. Non riporta gli script né le patch ai template: un upgrade del plugin `os-freeradius` le sovrascrive. Non ricreare `/usr/local/etc/patrizia_lock.env`.

1. Ripristina il backup. Controlla che il plugin `os-freeradius` sia installato.
2. Copia dal repository `ansible/playbooks/scripts/opnsense/freeradius/` in `/usr/local/opnsense/scripts/freeradius/` questi tre file, ed eseguili (`chmod 755`):
   - `patrizia_lock.py`
   - `patrizia_lock.sh`
   - `checkrad-online.sh`
3. Ripristina le patch sui template in `/usr/local/opnsense/service/templates/OPNsense/Freeradius/`. Sono queste, e non i file già generati in `/usr/local/etc/raddb/`:
   - `radiusd.conf`: `checkrad = /usr/local/opnsense/scripts/freeradius/checkrad-online.sh`
   - `queries.conf`, `simul_verify_query`: il filtro utente è `'%{SQL-User-Name}'`, non `'%{User-Name}'`
   - `sites-enabled-inner-tunnel`: dentro `session { }` c'è `sql`; in `Post-Auth-Type REJECT` c'è `patrizia_lock` subito dopo `-sql`
   - `sites-enabled-default`: in `session { }`, se SQLite è attivo, c'è `sql`; in `Post-Auth-Type REJECT` c'è `patrizia_lock` subito dopo `-sql`
4. Ricrea `/usr/local/etc/raddb/mods-enabled/patrizia_lock`. Non ha un template, quindi un reload non lo rigenera:

```
exec patrizia_lock {
    wait = yes
    input_pairs = request
    shell_escape = yes
    program = "/usr/local/opnsense/scripts/freeradius/patrizia_lock.sh %{User-Name} %{Calling-Station-Id} %{reply:Reply-Message}"
    timeout = 3
}
```

5. `/usr/local/sbin/checkrad` è uno script di due righe (`#!/bin/sh` e `exit 1`). L'originale del pacchetto è `/usr/local/sbin/checkrad.stock`. `radiusd.conf` non lo usa: chiama `checkrad-online.sh`, che fa la stessa cosa.
6. Ricarica e riavvia:

```
configctl template reload OPNsense/Freeradius
```

```
configctl freeradius restart
```

Il passo 4 va rifatto dopo il reload se quel comando ha cancellato `mods-enabled/patrizia_lock`.

La configurazione dell'SSID sul Cudy non è in questo backup. Resta sulla GUI dell'AP.

## File sul firewall

- `/usr/local/opnsense/scripts/freeradius/patrizia_lock.sh` — sorgente `ansible/playbooks/scripts/opnsense/freeradius/patrizia_lock.sh`
- `/usr/local/opnsense/scripts/freeradius/patrizia_lock.py` — sorgente `ansible/playbooks/scripts/opnsense/freeradius/patrizia_lock.py`
- `/usr/local/opnsense/scripts/freeradius/checkrad-online.sh` — sorgente `ansible/playbooks/scripts/opnsense/freeradius/checkrad-online.sh` (exit 1: la sessione contata in SQLite resta valida finché non arriva l'Accounting-Stop)
- `/usr/local/sbin/checkrad` sostituito con `exit 1`; l'originale è `/usr/local/sbin/checkrad.stock`
- Patch ai template del plugin, da riapplicare se `os-freeradius` viene aggiornato:
  - `sites-enabled-inner-tunnel`: `session { sql }` e `patrizia_lock` nel Post-Auth-Type REJECT
  - `sites-enabled-default`: `patrizia_lock` nel Post-Auth-Type REJECT
  - `queries.conf`: `simul_verify_query` filtra su `%{SQL-User-Name}`
  - `radiusd.conf`: `checkrad` punta a `checkrad-online.sh`
  - `mods-enabled/patrizia_lock`: exec con `%{reply:Reply-Message}`

## 💾 Stato di Ripristino (AI Save-State)

- **Fase Attiva**: SSID sull'AP
- **Ultima Azione Completata**: Procedura di reinstallazione scritta nel piano. Telegram e secret letti da `config.xml`. `radiusd` in esecuzione.
- **Prossimo Passo Operativo**: Sulla GUI `http://10.10.20.103` impostare `Eternal` su WPA2-Enterprise verso `192.168.2.254:1812` (accounting 1813, secret del client `ap11000`) e aggiungere `Eternal-Device` in WPA3-SAE sulla VLAN 20 nativa, senza RADIUS.
- **Blocchi/Decisioni Pendenti**: Login amministratore dell'AP non disponibile in questa sessione.
