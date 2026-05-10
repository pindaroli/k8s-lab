#!/bin/bash

# Create directory
mkdir -p qbittorrent-search-plugins

# Array of URLs
urls=(
"https://gist.githubusercontent.com/scadams/56635407b8dfb8f5f7ede6873922ac8b/raw/f654c10468a0b9945bec9bf31e216993c9b7a961/one337x.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/academictorrents.py"
"https://raw.githubusercontent.com/Cc050511/qBit-search-plugins/main/acgrip.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/ali213.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/anidex.py"
"https://raw.githubusercontent.com/AlaaBrahim/qBitTorrent-animetosho-search-plugin/main/animetosho.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/animeworld.py"
"https://raw.githubusercontent.com/pantyetta/qBittorrent-plugins/master/bangumi.moe.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/btdigg.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/btmirror.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/btmirror2.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/cpasbien.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/dmhy.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/dxdhd.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/ettv.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/extremlymtorrents.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/fitgirl.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/freeleech.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/gamestorrents.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/halivetorrents.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/hdchina.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/hdcmct.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/hdcmctv.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/hdstreet.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/hunterx.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/idope.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/ilcorsaronero.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/isohunt.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/kamept.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/katcr.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/kimcartoon.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/knaben.py"
"https://raw.githubusercontent.com/hectorb96/limetorrents-qbittorrent-plugin/main/limetorrents.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/m1080.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/magnetdl.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/magnetoz.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/masametv.py"
"https://raw.githubusercontent.com/MadeOfMagicAndWires/qBittorrent-search-plugins/master/miobt.py"
"https://raw.githubusercontent.com/Mr-Proxy-source/qbittorrent-searchplugin-movietorrent/main/movietorrent.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/newpct.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/nnmclub.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/ntorrents.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/opencd.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/perfectdark.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/piratethebay.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/psarips.py"
"https://raw.githubusercontent.com/pantyetta/qBittorrent-plugins/master/qbittorrent-search-plugins/pubtorrent.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/rarbg.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/rousi.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/rutracker.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/shanaproject.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/skg.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/solidtorrents.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/sukebei.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/tamilblasters.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/tamilmv.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/thepiratebay.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/thepiratebay2.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/torrentapi.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/torrenting.py"
"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/torrentproject.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/torlock.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/tokyotosho.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/torrentdownloads.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/torrentfunk.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/torrentgalaxy.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/torrentparadise.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/torrentz2.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/tpb_from_to.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/uniondht.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/vertor.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/what_cd.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/ygg.py"
"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/zamunda.py"
"https://raw.githubusercontent.com/hannsen/qbittorrent_search_plugins/master/zooqle.py"
)

successful=0
failed=0

echo "Starting download of qBittorrent search plugins..."

for url in "${urls[@]}"; do
    filename=$(basename "$url")
    echo "Downloading: $filename"

    if curl -s -f -o "qbittorrent-search-plugins/$filename" "$url"; then
        echo "✓ Downloaded: $filename"
        ((successful++))
    else
        echo "✗ Failed: $filename"
        ((failed++))
    fi
done

echo ""
echo "Download complete!"
echo "Successful: $successful"
echo "Failed: $failed"
echo "Total: ${#urls[@]}"
