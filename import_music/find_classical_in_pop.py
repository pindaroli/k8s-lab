import sqlite3
import os
import sys

POP_DB = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"
CLASSICAL_DB = "/Users/olindo/prj/k8s-lab/import_music/import_classical/classical_musiclibrary.db"

def main():
    delete_mode = "--delete" in sys.argv

    if not os.path.exists(POP_DB):
        print(f"[!] Pop DB non trovato a {POP_DB}")
        return
    if not os.path.exists(CLASSICAL_DB):
        print(f"[!] Classical DB non trovato a {CLASSICAL_DB}")
        return

    # Connessione ai DB
    conn_pop = sqlite3.connect(POP_DB)
    conn_class = sqlite3.connect(CLASSICAL_DB)

    pop_cur = conn_pop.cursor()
    class_cur = conn_class.cursor()

    # Recupera tutti gli album classici con il loro MusicBrainz Album ID, titolo e percorso (ricavato da items)
    try:
        class_cur.execute("""
            SELECT a.id, a.albumartist, a.album, a.mb_albumid, i.path
            FROM albums a
            LEFT JOIN items i ON i.album_id = a.id
            GROUP BY a.id
        """)
        classical_albums = class_cur.fetchall()
    except sqlite3.OperationalError as e:
        print(f"[!] Errore nel leggere Classical DB: {e}")
        return

    try:
        pop_cur.execute("""
            SELECT a.id, a.albumartist, a.album, a.mb_albumid, i.path
            FROM albums a
            LEFT JOIN items i ON i.album_id = a.id
            GROUP BY a.id
        """)
        pop_albums = pop_cur.fetchall()
    except sqlite3.OperationalError as e:
        print(f"[!] Errore nel leggere Pop DB: {e}")
        return

    # Costruiamo set di MBID classici e titoli
    class_mbids = {}
    class_titles = {}
    for c_id, artist, title, mbid, path in classical_albums:
        if mbid and mbid.strip():
            class_mbids[mbid.strip()] = (artist, title, path)
        if title:
            # Normalizzazione minima del titolo per confronto
            norm_title = title.lower().strip()
            class_titles[norm_title] = (artist, title, path)

    print(f"[*] Caricati {len(classical_albums)} album dal DB Classica.")
    print(f"[*] Caricati {len(pop_albums)} album dal DB Pop/Rock.")
    print("\n--- Analisi Overlap (Album presenti in entrambi i DB) ---")

    duplicates = []

    for p_id, artist, title, mbid, path in pop_albums:
        matched = False
        reason = ""
        matched_class_info = None

        mbid_key = mbid.strip() if mbid else None
        if mbid_key and mbid_key in class_mbids:
            matched = True
            reason = f"MBID Match ({mbid_key})"
            matched_class_info = class_mbids[mbid_key]
        else:
            norm_title = title.lower().strip() if title else ""
            if norm_title and norm_title in class_titles:
                matched = True
                reason = "Title Match"
                matched_class_info = class_titles[norm_title]

        if matched:
            duplicates.append({
                'pop_id': p_id,
                'pop_artist': artist,
                'pop_album': title,
                'pop_path': path,
                'class_artist': matched_class_info[0],
                'class_album': matched_class_info[1],
                'class_path': matched_class_info[2],
                'reason': reason
            })

    if not duplicates:
        print("[+] Nessun album duplicato/classico trovato all'interno del DB Pop/Rock.")
        return

    print(f"[!] Trovati {len(duplicates)} album potenzialmente duplicati/classici nel DB Pop/Rock:\n")

    total_files_to_remove = 0
    pop_album_ids_to_delete = []

    for item in duplicates:
        # Decodifica dei percorsi beets (memorizzati come byte string)
        pop_path_bytes = item['pop_path']
        pop_path_str = ""
        if isinstance(pop_path_bytes, bytes):
            pop_path_str = pop_path_bytes.decode('utf-8', 'ignore')
        else:
            pop_path_str = str(pop_path_bytes)

        class_path_bytes = item['class_path']
        class_path_str = ""
        if isinstance(class_path_bytes, bytes):
            class_path_str = class_path_bytes.decode('utf-8', 'ignore')
        else:
            class_path_str = str(class_path_bytes)

        print(f"• POP: {item['pop_artist']} - {item['pop_album']} ({item['reason']})")
        print(f"  Path POP: {pop_path_str}")
        print(f"  Path CLASSICAL: {class_path_str}")

        # Verifica se il path POP esiste
        if os.path.exists(pop_path_str):
            print(f"  Status: [ESISTE FISICAMENTE]")
            pop_album_ids_to_delete.append((item['pop_id'], pop_path_str))
        else:
            print(f"  Status: [Non trovato sul disco, solo a DB]")
            pop_album_ids_to_delete.append((item['pop_id'], None))

    print("\n--------------------------------------------------")
    print(f"Riepilogo: {len(pop_album_ids_to_delete)} album da rimuovere dal DB Pop e dal disco.")

    if delete_mode:
        print("\n[⚠️] ESECUZIONE ELIMINAZIONE ATTIVA...")
        for alb_id, p_path in pop_album_ids_to_delete:
            # 1. Rimuovi fisicamente i file se il path esiste
            if p_path and os.path.exists(p_path):
                print(f"[*] Rimozione fisica cartella: {p_path}")
                # Rimozione ricorsiva sicura per evitare disastri
                if "/Volumes/arrdata/media/music_backup/" in p_path:
                    import shutil
                    try:
                        shutil.rmtree(p_path)
                        print(f"  [OK] Cartella rimossa.")
                    except Exception as e:
                        print(f"  [ERRORE] Impossibile rimuovere la cartella: {e}")
                else:
                    print(f"  [⚠️ WARNING] Cartella fuori dal range di sicurezza: {p_path}. Rimozione saltata.")

            # 2. Rimuovi dal database
            # Dobbiamo rimuovere sia l'album sia gli items (le singole tracce) associati
            try:
                pop_cur.execute("DELETE FROM items WHERE album_id = ?", (alb_id,))
                pop_cur.execute("DELETE FROM albums WHERE id = ?", (alb_id,))
                conn_pop.commit()
                print(f"  [OK] Album ID {alb_id} rimosso dal DB Pop.")
            except Exception as e:
                print(f"  [ERRORE] Impossibile aggiornare il DB per ID {alb_id}: {e}")

        print("\n[+] Operazione di bonifica completata.")
    else:
        print("\n[ℹ️] Questa era una simulazione (DRY-RUN).")
        print("[ℹ️] Per eseguire l'eliminazione reale, avvia lo script con l'opzione: python3 find_classical_in_pop.py --delete")

    conn_pop.close()
    conn_class.close()

if __name__ == "__main__":
    main()
