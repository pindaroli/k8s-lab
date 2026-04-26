# Tdarr Node Configuration (Mac Studio)

Questa guida documenta come configurare il **Tdarr Node** sul Mac Studio per sfruttare l'accelerazione hardware Apple (VideoToolbox) per la transcodifica, mantenendo il **Tdarr Server** su Kubernetes.

## 1. Requisiti sul Mac Studio
- **Homebrew** installato.
- **FFmpeg** con supporto Apple Silicon:
  ```bash
  brew install ffmpeg
  ```

## 2. Installazione Binario
Creare la directory e scaricare l'eseguibile per macOS arm64:
```bash
mkdir -p ~/tdarr
cd ~/tdarr
curl -L https://storage.tdarr.io/versions/2.70.01/darwin_arm64/Tdarr_Node.zip -o Tdarr_Node.zip
# Estrazione forzata nella cartella corrente
unzip -o Tdarr_Node.zip -d node
rm Tdarr_Node.zip
```

## 3. Configurazione DNS e Rete (Fondamentale)
Affinché il nodo sul Mac possa comunicare con il Server su Kubernetes, l'hostname `tdarr-internal.pindaroli.org` deve essere risolvibile.

### Modifica a `rete.json`
L'hostname viene gestito centralmente nel file `rete.json`. È stato aggiunto come alias al nodo `traefik-lb`:
```json
{
    "id": "traefik-lb",
    "aliases": [
        ...,
        "tdarr",
        "tdarr-internal"
    ]
}
```

### Sincronizzazione
Dopo ogni modifica a `rete.json`, è necessario sincronizzare OPNsense tramite Ansible:
```bash
ansible-playbook -i ansible/inventory.ini ansible/playbooks/opnsense_sync_dns.yml --vault-password-file ~/.vault_pass.txt
```
Questo comando crea i record DNS in Unbound che puntano al VIP di Traefik (`10.10.20.56`).

## 4. Configurazione del Nodo
Creare o modificare il file `~/tdarr/node/Tdarr_Node_Config.json`:

```json
{
  "nodeName": "MacStudio-Node",
  "serverIP": "tdarr-internal.pindaroli.org",
  "serverPort": "8266",
  "nodeIP": "olindo-macstudio.pindaroli.org",
  "nodePort": "8267",
  "appWindow": false,
  "cronMonitor": false
}
```
*Nota: Assicurarsi che l'hostname olindo-macstudio.pindaroli.org sia risolvibile dal cluster K8s.*

## 4. Gestione Servizio (Alla bisogna)
Per avviare il nodo manualmente quando necessario:
```bash
cd ~/tdarr/node && ./Tdarr_Node
```

## 5. Configurazione Permessi NFS (TrueNAS <-> Mac)
Per permettere al Mac Studio di scrivere sulla share NFS di TrueNAS, seguire questi passaggi:

1. **Verifica UID sul Mac:** Eseguire `id -u` (solitamente `501` o `1000`).
2. **TrueNAS Share Settings:**
   - Impostare **Maproot User** su `root`.
   - Impostare **Maproot Group** su `wheel`.
   - Autorizzare l'IP del Mac (`10.10.20.100`) o la subnet.
3. **Comando di Mount sul Mac:**
   ```bash
   sudo mkdir -p /Volumes/media
   sudo mount -t nfs -o rw,resvport,hard,intr 10.10.10.50:/mnt/oliraid/arrdata/media /Volumes/media
   ```
4. **Test Scrittura:**
   ```bash
   touch /Volumes/media/test_write.txt && rm /Volumes/media/test_write.txt
   ```

## 6. Storage & Path Mapping (CRUCIALE)
Il Mac deve montare le share NFS di TrueNAS negli stessi percorsi (o mappati) del Server.

**Esempio di Mapping nella UI di Tdarr:**
- **Server Path:** `/mnt/media`
- **Node Path:** `/Volumes/media`

Assicurarsi che il Mac abbia i permessi di scrittura sulla share NFS.

## 6. Integrazione Prefect
Una volta configurato, Prefect potrà inviare comandi API al Tdarr Server (K8s) per:
1. Iniziare una Library Scan.
2. Mettere in pausa/avviare il nodo sul Mac.
3. Notificare via Telegram il completamento delle transcodifiche.
