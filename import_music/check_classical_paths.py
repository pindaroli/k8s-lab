import sqlite3
import os

POP_DB = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"

def main():
    if not os.path.exists(POP_DB):
        print(f"[!] Pop DB non trovato a {POP_DB}")
        return

    conn = sqlite3.connect(POP_DB)
    cur = conn.cursor()

    # Cerca tracce che abbiano 'classical' nel percorso
    cur.execute("SELECT id, title, path FROM items")
    items = cur.fetchall()

    classical_items = []
    for item_id, title, path in items:
        path_str = ""
        if isinstance(path, bytes):
            path_str = path.decode('utf-8', 'ignore')
        else:
            path_str = str(path)

        if 'classical' in path_str.lower():
            classical_items.append((item_id, title, path_str))

    print(f"[*] Verificate {len(items)} tracce in Pop/Rock DB.")
    if classical_items:
        print(f"[!] Trovate {len(classical_items)} tracce con 'classical' nel percorso:")
        for item_id, title, path_str in classical_items[:20]:
            print(f"  ID: {item_id} | Titolo: {title} | Path: {path_str}")
        if len(classical_items) > 20:
            print(f"  ... e altre {len(classical_items) - 20} tracce.")
    else:
        print("[+] Nessuna traccia con percorsi contenenti 'classical' trovata nel DB Pop/Rock.")

    conn.close()

if __name__ == "__main__":
    main()
