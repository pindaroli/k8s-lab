---
title: "INC-2026-09-02: qBittorrent 5.2.x WebUI Auth Breaking Change & arrstack-mcp Integration"
type: incident
status: archived
certified_for_ai: false
date: 2026-09-02
severity: P3
resolved: true
resolved_at: 2026-09-02T19:58:00Z
tags:
  - "#incident"
  - "#servarr"
  - "#qbittorrent"
  - "#mcp"
---

# INC-2026-09-02: qBittorrent 5.2.x WebUI Auth Breaking Change & arrstack-mcp Integration

## Descrizione dell'Incidente
Durante l'integrazione e il collaudo del server MCP **arrstack-mcp** per l'amministrazione via intelligenza artificiale dello stack [[Servarr]] (Radarr, Lidarr, Prowlarr, qBittorrent), tutti i tool verso le istanze `*arr` hanno risposto con successo (200 OK), mentre qualsiasi chiamata verso **qBittorrent** falliva sistematicamente riportando:
`qBittorrent login failed: no SID cookie returned.`

Contemporaneamente, l'ispezione dei log del container secondario `qbittorrent-exporter` all'interno del pod di qBittorrent evidenziava fallimenti analoghi:
`[ERROR] authentication failed, status code: 204`

## Analisi della Root Cause

L'indagine tecnica approfondita ha isolato due fattori concomitanti introdotti con l'aggiornamento a **qBittorrent v5.2.3** (`lscr.io/linuxserver/qbittorrent:5.2.3_v2.0.13-ls468`):

1. **Assenza di gestione delle variabili d'ambiente per la sicurezza WebUI**:
   - I container qBittorrent di LinuxServer non leggono le variabili d'ambiente `WEBUI_BYPASS_AUTH_SUBNET_WHITELIST_ENABLED` o `WEBUI_AUTH_SUBNET_WHITELIST` definite in `env:` del manifest Helm.
   - Tutte le preferenze relative a CSRF Protection, Host Header Validation e Whitelist Subnet risiedono esclusivamente nel file persistente `/config/qBittorrent/qBittorrent.conf` sotto la sezione `[Preferences]`.
   - Mancando tali impostazioni nel file, qBittorrent bloccava le richieste con verifiche CSRF ed esigeva autenticazione anche dalla subnet locale del cluster e dai proxy interni.

2. **Breaking Change nel nome del Cookie di Sessione (qBittorrent >= 5.2.0)**:
   - Nelle versioni legacy di qBittorrent, l'endpoint `/api/v2/auth/login` rispondeva con corpo `Ok.` e rilasciava un cookie denominato letteralmente `SID`.
   - A partire dalla versione 5.2.0, qBittorrent adotta la risposta `HTTP 204 No Content` e formatta il cookie di sessione includendo la porta di ascolto: `QBT_SID_<PORT>` (nello specifico **`QBT_SID_8080`**).
   - Il codice sorgente di `arrstack-mcp` (`server.py`, riga 343) conteneva il controllo rigido `login.cookies.get("SID")`. Di fronte a `QBT_SID_8080`, il client MCP non riconosceva il cookie e sollevava l'eccezione `no SID cookie returned`, nonostante l'avvenuta autenticazione con esito 204 e cookie valido emesso dal demone.

## Azioni Correttive Adottate

### 1. Risoluzione Dichiarativa Helm (Livello Cluster)
È stato aggiornato il file di configurazione Helm `servarr/arr-values.yaml` aggiungendo un `initContainer` (`qbt-config-security`) al deployment di qBittorrent:

```yaml
qbittorrent:
  initContainers:
    - name: qbt-config-security
      image: busybox:latest
      command:
        - sh
        - -c
        - |
          CONF="/config/qBittorrent/qBittorrent.conf"
          if [ -f "$CONF" ]; then
            echo "Patching qBittorrent.conf security settings..."
            sed -i '/WebUI\\CSRFProtection/d; /WebUI\\HostHeaderValidation/d; /WebUI\\AuthSubnetWhitelist/d' "$CONF"
            sed -i '/\[Preferences\]/a WebUI\\AuthSubnetWhitelist=10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8\nWebUI\\AuthSubnetWhitelistEnabled=true\nWebUI\\CSRFProtection=false\nWebUI\\HostHeaderValidation=false' "$CONF"
            chown 1000:1000 "$CONF"
            echo "qBittorrent.conf patched successfully."
          fi
      volumeMounts:
        - name: config
          mountPath: /config
```
L'upgrade Helm (Revisione 169) ha istanziato il pod `servarr-qbittorrent-5cf794b455-qmngf`, il cui initContainer ha applicato le impostazioni in modo idempotente preservando i permessi `1000:1000`.

### 2. Architettura e Patch dell'MCP Server (Livello Client)
Per eliminare la dipendenza da plugin non tracciati e garantire la robustezza:
- Il codice dell'MCP server è stato consolidato all'interno della repository in `scripts/arrstack-mcp/server.py`.
- È stata applicata una patch dinamica all'helper `_qbt` per ricercare ed accettare qualsiasi cookie contenente il token `SID` (`QBT_SID_*` o `SID`) e per gestire i codici di stato 200/204 in caso di subnet whitelist bypass:

```python
_qbt_sid = login.cookies.get("SID")
_qbt_cookie_name = "SID"
if not _qbt_sid:
    for k, v in login.cookies.items():
        if "SID" in k.upper():
            _qbt_sid = v
            _qbt_cookie_name = k
            break
if not _qbt_sid and (login.status_code in (200, 204) and ("Ok." in login.text or not login.text.strip())):
    _qbt_sid = "BYPASS"
    _qbt_cookie_name = None
elif not _qbt_sid:
    return "qBittorrent login failed: no SID cookie returned."
```

- La configurazione MCP è stata centralizzata nel file standard `~/.gemini/antigravity/mcp_config.json` vincolando la dipendenza `mcp[cli]>=1.0.0,<2.0.0` per preservare la compatibilità con FastMCP v1:

```json
"arrstack-mcp": {
  "command": "/opt/homebrew/bin/uv",
  "args": [
    "run",
    "--with",
    "mcp[cli]>=1.0.0,<2.0.0",
    "--with",
    "httpx",
    "/Users/olindo/prj/k8s-lab/scripts/arrstack-mcp/server.py"
  ],
  "env": {
    "ENABLED_SERVICES": "radarr,lidarr,prowlarr,qbittorrent",
    "RADARR_URL": "https://radarr-internal.pindaroli.org",
    "RADARR_API_KEY": "f506f4dd91674a1a85b98f3a41c92ab9",
    "LIDARR_URL": "https://lidarr-internal.pindaroli.org",
    "LIDARR_API_KEY": "ee6625f51dea47369a65a7ef53637ae1",
    "PROWLARR_URL": "https://prowlarr-internal.pindaroli.org",
    "PROWLARR_API_KEY": "fad287a6fe814e1b885f1ba0a8f95179",
    "QBT_URL": "https://qbittorrent-internal.pindaroli.org",
    "QBT_USER": "admin",
    "QBT_PASS": "Compli61!"
  }
}
```

## Esito e Validazione
Il test eseguito con il codice patchato ha confermato:
- Autenticazione qBittorrent: `HTTP 204 No Content`
- Cookie identificato correttamente: `QBT_SID_8080 = lmScZV5mj3TuEyXf7nKxLfhq2c2y9LM5`
- Interrogazione API `/api/v2/torrents/info`: `HTTP 200 OK` con estrazione in tempo reale di 801 torrent attivi.
- Stato: **RISOLTO**.
