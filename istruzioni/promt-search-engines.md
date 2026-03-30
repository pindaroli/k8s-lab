# Obiettivo: Ripristino e Debug Connessione Proxy Xray su OCI per l'ecosistema Servarr

Ciao, dobbiamo riprendere il debugging per ripristinare la funzionalità di ricerca torrent (Search Plugins) su qBittorrent e Prowlarr. 

## Riassunto e Test già effettuati:
Ieri abbiamo eseguito un debug approfondito e abbiamo risolto tutti i problemi software locali. Ecco los stato dell'arte:
1. **Permessi e Sintassi (RISOLTI):** I file `.py` dei search engines sulla share di TrueNAS hanno ora i permessi corretti (`1000:100`) e abbiamo riparato gli errori in `jackett.py` e `tokyotoshokan.py`. Ora qBittorrent carica perfettamente le *capabilities* di ricerca (nova2.py funziona).
2. **Setup Prowlarr nativo (COMPLETATO):** Dato che il plugin "jackett" generico era incompatibile, abbiamo scaricato e configurato il plugin ufficiale `prowlarr.py` per qBittorrent. Abbiamo creato il file `prowlarr.json` inserendo la API Key e puntando direttamente all'IP del Kube (ClusterIP: `10.106.232.123:9696`) per far sì che la regola Iptables `tun2socks` (priority 500) bypassasse la VPN per il traffico interno.
3. **Il blocco Rete Esterna (IL VERO PROBLEMA):** La comunicazione interna funziona (`curl` verso Prowlarr risponde istantaneamente), ma le ricerche reali vanno in TIMEOUT. I log di Prowlarr mostrano che il servizio inizia la ricerca sugli indexer ma rimane appeso all'infinito.
4. **Isolamento del Guasto TCP:** Eseguendo `curl -m 5 https://google.com` dall'interno dei pod `servarr-qbittorrent` e `servarr-prowlarr`, otteniamo un Timeout inesorabile (Exit code 28). Entrambi i pod usano un **Transparent Xray Tunnel (Sidecar)** per la privacy, che intercetta tutto via `tun2socks-gateway` e instrada verso `xray-core`.
5. **Esame della VPS Esterna:** Il server remoto Xray è ospitato su Oracle Cloud (OCI) all'IP `79.72.44.199`. Da un test col Mac locale, la porta 443 TCP è formalmente aperta, ma la connessione proxy interna da Xray Kube verso la VPS cade nel vuoto o viene scartata (i log di xray-core a livello warning sono vuoti, segno che l'handshake e/o lo stream vanno in blackhole o subiscono drop silenziosi).

## Prossimi Passaggi Richiesti:
Abbiamo dedotto che il problema risiede o (A) Nel server Xray remoto su Oracle Cloud che per qualche motivo rigetta il traffico in ingresso (es. chiavi scadute o firewall OCI incastrato), oppure (B) In un problema di Routing Asimmetrico sul firewall OPNsense locale che impedisce ai nodi Talos di fare ritorno dalla VPS.

Oggi ho verificato personalmente la macchina server remota Xray su Oracle. 
**[NOTA PER L'UTENTE: Compila questo spazio spiegando all'AI cosa hai scoperto loggandoti sulla VPS Oracle. Es: "Ho riavviato Xray e ho sistemato UFW", oppure "La VPS è intatta e funziona perfettamente, deve essere OPNsense locale"].**

In base a questi nuovi sviluppi, proponimi i prossimi step (comandi di rete per testare i log di OPNsense, fix del certificato Xray o modifiche ai config.json nei secrets) in modo che possiamo ripristinare la connessione TCP passante, affinché Prowlarr possa estrarre i tracker e sbloccare qBittorrent! 
⚠️ *Ricorda sempre la regola del file GEMINI.md: spiegami cosa fa ogni comando e perché lo esegui prima di lanciarlo.*
