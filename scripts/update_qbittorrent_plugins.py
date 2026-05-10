import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# --- CONFIGURAZIONE ---
WIKI_URL = "https://github.com/qbittorrent/search-plugins/wiki/Unofficial-search-plugins"
DEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "downloads", "plugins")
# ----------------------

def convert_to_raw_url(url):
    """
    Converte un link GitHub standard in un link Raw se necessario.
    Esempio: github.com/user/repo/blob/master/file.py -> raw.githubusercontent.com/user/repo/master/file.py
    """
    parsed = urlparse(url)
    if 'github.com' in parsed.netloc and '/blob/' in parsed.path:
        new_path = parsed.path.replace('/blob/', '/', 1)
        return f"https://raw.githubusercontent.com{new_path}"
    return url

def download_plugins():
    # Crea la directory di destinazione
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
        print(f"📂 Cartella creata: {DEST_DIR}")

    print(f"🔍 Recupero wiki: {WIKI_URL}...")
    try:
        response = requests.get(WIKI_URL, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Errore nel caricamento della pagina: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    # Trova la prima tabella (Plugins for Public Sites)
    table = soup.find('table')
    if not table:
        print("❌ Tabella dei plugin non trovata nella pagina!")
        return

    rows = table.find_all('tr')[1:] # Salta l'header
    print(f"📊 Trovati {len(rows)} potenziali plugin nella tabella pubblica.")

    count = 0
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 5:
            continue

        # Il nome del motore è nella prima colonna (o estratto dal file)
        engine_name = cols[0].get_text(strip=True)

        # Il link di download è nella quinta colonna (indice 4)
        link_tag = cols[4].find('a')
        if not link_tag:
            continue

        download_url = link_tag.get('href')
        if not download_url:
            continue

        # Gestione link relativi
        download_url = urljoin(WIKI_URL, download_url)

        # Conversione in RAW per GitHub
        raw_url = convert_to_raw_url(download_url)

        # Nome file
        filename = os.path.basename(urlparse(raw_url).path)
        if not filename.endswith('.py'):
            filename = f"{engine_name.lower().replace(' ', '_')}.py"

        dest_path = os.path.join(DEST_DIR, filename)

        # Download effettivo
        try:
            print(f"📥 Scaricando: {engine_name} ({filename})...", end=' ', flush=True)
            plugin_res = requests.get(raw_url, timeout=10)
            plugin_res.raise_for_status()

            with open(dest_path, 'wb') as f:
                f.write(plugin_res.content)
            print("DONE.")
            count += 1
        except Exception as e:
            print(f"ERRORE: {e}")

    print(f"\n✅ Completato! {count} plugin scaricati in {DEST_DIR}")

if __name__ == "__main__":
    download_plugins()
