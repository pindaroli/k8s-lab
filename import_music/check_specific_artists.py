import sqlite3
import os

POP_DB = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"

def main():
    if not os.path.exists(POP_DB):
        print(f"[!] Pop DB non trovato a {POP_DB}")
        return

    conn = sqlite3.connect(POP_DB)
    cur = conn.cursor()

    cur.execute("SELECT id, albumartist, album FROM albums ORDER BY albumartist")
    albums = cur.fetchall()

    print(f"[*] Totale album nel DB Pop/Rock: {len(albums)}\n")
    print("Elenco completo degli album ordinati per artista:")
    print("--------------------------------------------------")
    for alb_id, artist, album in albums:
        print(f"ID {alb_id:03d} | Artista: {artist} | Album: {album}")

    conn.close()

if __name__ == "__main__":
    main()
