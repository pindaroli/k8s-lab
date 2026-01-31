# Troubleshooting Note: Instabilità Thunderbolt Ethernet 10Gb (Mac)

**Problema**: Connessione intermittente su adattatore Thunderbolt Ethernet (Chip Aquantia AQC113).
**Sintomi**: Caduta link ("Interface en10 has gone down"), packet loss sporadico, soprattutto sotto carico o all'avvio.

---

## Soluzioni Applicate & Testate

### 1. Disabilitazione Flow Control (EFFICACE - Eseguito)
**Azione**: Forzato link a 10G full-duplex senza flow-control.
**Esito**: Link più stabile, risolta negoziazione incerta.
**Stato**: **PERSISTENTE (Configurato via GUI)**
- `System Settings` > `Network` > `Thunderbolt Ethernet` > `Hardware`
- Configurazione: `Manually`
- Speed: `10Gbase-T`
- Duplex: `full-duplex` (NON flow-control)

### 2. Disabilitazione AVB/EAV Mode (CONSIGLIATO - Eseguito)
**Azione**: Disabilitata modalità "Audio Video Bridging".
**Motivo**: Può confliggere con switch standard e prioritarizzare traffico in modo anomalo.
**Stato**: **PERSISTENTE (Configurato via GUI)**
- `System Settings` > `Network` > `Thunderbolt Ethernet` > `Hardware` > Toggle `AVB/EAV Mode` OFF.

### 3. Disabilitazione TSO (TCP Segmentation Offload) (IN TEST)
**Azione**: Disabilitato offload segmentazione TCP alla scheda di rete.
**Motivo**: Workaround per bug noto driver Aquantia su macOS che causa packet corruption/drop.
**Comando (Volatile)**:
```bash
sudo sysctl -w net.inet.tcp.tso=0
```
**Per rendere PERSISTENTE (se efficace)**:
Creare file `/etc/sysctl.conf` (o aggiungere riga se esiste):
```text
net.inet.tcp.tso=0
```
*Nota: Richiede permessi di root per la modifica.*

### 4. Monitoraggio Attivo
**Script**: `scripts/monitor_ping.sh`
- Ping continuo verso Gateway.
- Logga su file solo i timeout con timestamp.

---

## Rollback (Se necessario)
1. Rimettere Hardware Configuration su `Automatic` da GUI.
2. Riabilitare TSO: `sudo sysctl -w net.inet.tcp.tso=1`
