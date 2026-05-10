#!/bin/bash

# Create directory if it doesn't exist
mkdir -p qbittorrent-search-plugins

# Array of additional plugin URLs from different repositories
urls=(
# LightDestory's Collection
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/academictorrents.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/bitsearch.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/bt4g.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/btetree.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/cloudtorrents.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/filemood.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/glotorrents.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/ilcorsaronero.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/kickasstorrents.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/limetorrents.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/rockbox.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/snowfl.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/solidtorrents.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/torrentdownload.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/torrentfunk.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/yourbittorrent.py"

# BurningMop's Collection
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/bitsearch.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/calidadtorrent.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/divxtotal.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/dontorrent.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/esmeraldatorrent.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/mypornclub.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/naranjatorrent.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/pediatorrent.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/solidtorrents.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/therarbg.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/tomadivx.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/torrenflix.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/torrentbytes.py"
"https://raw.githubusercontent.com/BurningMop/qBittorrent-Search-Plugins/main/torrentdownloads.py"

# d3cim's Collection
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/bt4g.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/btetree.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/btmulu.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/foxcili.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/glotorrents.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/kickass_torrent.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/magnetdl.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/mejor.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/nyaasi.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/oxtorrent.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/solidtorrents.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/torrentdownload.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/torrentfunk.py"
"https://raw.githubusercontent.com/d3cim/qbittorrent-search-plugins/main/torrentgalaxy.py"

# Other individual plugins
"https://raw.githubusercontent.com/galaris/BTDigg-qBittorrent-plugin/main/btdig.py"
"https://raw.githubusercontent.com/HazukiShiro/qBittorrent-Search-Plugins/master/sumotorrent.py"
"https://raw.githubusercontent.com/la55u/qBit-IPT-plugin/main/ipt.py"
"https://raw.githubusercontent.com/Laiteux/YggAPI-qBittorrent-Search-Plugin/main/yggapi.py"
"https://raw.githubusercontent.com/v1k45/1337x-qBittorrent-search-plugin/master/leetx.py"
)

successful=0
failed=0
skipped=0

echo "Starting download of additional qBittorrent search plugins..."

for url in "${urls[@]}"; do
    filename=$(basename "$url")
    filepath="qbittorrent-search-plugins/$filename"

    # Check if file already exists
    if [ -f "$filepath" ]; then
        echo "⚠️  Skipped: $filename (already exists)"
        ((skipped++))
        continue
    fi

    echo "Downloading: $filename"

    if curl -s -f -o "$filepath" "$url"; then
        echo "✓ Downloaded: $filename"
        ((successful++))
    else
        echo "✗ Failed: $filename"
        ((failed++))
    fi
done

echo ""
echo "Additional plugins download complete!"
echo "Successful: $successful"
echo "Failed: $failed"
echo "Skipped (already exists): $skipped"
echo "Total attempted: ${#urls[@]}"
