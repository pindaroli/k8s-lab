#!/bin/bash
# Script per configurare l'automount nativo (autofs) di macOS per i dataset TrueNAS (Classical e Media).
# Richiede privilegi di amministratore (sudo) per modificare i file in /etc/.

set -e

echo "=== Configurazione Automount (autofs) per TrueNAS Library ==="

# 1. Verifica/Aggiunta della mappa diretta in /etc/auto_master
echo "[*] Verifica della configurazione in /etc/auto_master..."
if grep -q "^/-[[:space:]]*auto_nas" /etc/auto_master; then
    echo "[+] Mappa diretta auto_nas gia' presente in /etc/auto_master."
else
    echo "[*] Aggiunta della mappa diretta auto_nas a /etc/auto_master..."
    echo "/-                  auto_nas" | sudo tee -a /etc/auto_master
fi

# 2. Creazione/Aggiornamento del file di mappa /etc/auto_nas
echo "[*] Creazione/Aggiornamento del file di mappa /etc/auto_nas..."
sudo tee /etc/auto_nas << 'EOF'
/Volumes/classical  -rw,nosuid,nodev,resvport,tcp,soft,intr,noatime 10.10.10.50:/mnt/oliraid/arrdata/classical
/Volumes/media      -rw,nosuid,nodev,resvport,tcp,soft,intr,noatime 10.10.10.50:/mnt/oliraid/arrdata/media
EOF

echo "[*] Impostazione dei permessi corretti per /etc/auto_nas..."
sudo chmod 644 /etc/auto_nas

# 3. Ricaricamento del servizio autofs
echo "[*] Ricaricamento di autofs per applicare le modifiche..."
sudo automount -vc

echo ""
echo "[+] Configurazione completata con successo!"
echo "[i] Informazioni importanti:"
echo "    - '/Volumes/classical' punta a truenas:/mnt/oliraid/arrdata/classical"
echo "    - '/Volumes/media' punta a truenas:/mnt/oliraid/arrdata/media"
echo "    - I dischi si monteranno al volo in background non appena proverai ad accedervi."
echo "    - Se non li usi per un po', macOS li smontera' automaticamente per prevenire blocchi."
echo ""
EOF
