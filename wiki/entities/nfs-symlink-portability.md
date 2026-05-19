---
title: "NFS Symlink Portability Governance"
last_updated: "2026-05-19"
confidence: "High"
tags:
  - "#core"
  - "#storage"
  - "#network"
  - "#active"
provenance:
  - "classical-music-taxonomy-optimization.md"
  - "music-library-governance.md"
---

# NFS Symlink Portability Governance

Questa direttiva definisce gli standard e le convenzioni architetturali per l'uso di collegamenti simbolici (symlinks) all'interno dell'infrastruttura di storage distribuito del progetto GEMINI.

## 🗺️ Il Problema dei Symlink Assoluti in NFS

In un ambiente eterogeneo e distribuito:
1. Lo storage fisico risiede su un server NAS centrale (TrueNAS SCALE/ZFS).
2. I filesystem vengono esportati tramite NFS ad host multipli con ruoli differenti:
   - **Host di Calcolo/Ingestione**: macOS (Mac Studio) che esegue script di taggatura, catalogazione e istanze Beets locali.
   - **Host di Esecuzione/Streaming**: Nodi Kubernetes (Talos) che eseguono i container dei media server (Jellyfin, Navidrome).
3. Se un client crea un symlink usando un percorso **assoluto** (es. `/Volumes/classical/library/Album/01.mp3` che punta a `/Volumes/classical/staging/Album/01.mp3`):
   - Funzionerà esclusivamente sull'host che lo ha creato (macOS), in cui il mountpoint risiede sotto `/Volumes`.
   - Si **romperà sistematicamente** all'interno dei pod Kubernetes, dove NFS monta il medesimo dataset su percorsi completamente differenti (es. `/media/music/classical/` o `/data/`).

---

## 💡 La Soluzione: Symlink Relativi Portabili

Per garantire che un collegamento simbolico rimanga valido e accessibile indipendentemente dal mountpoint locale di ciascun host, viene stabilita la seguente regola d'oro:

> [!IMPORTANT]
> **REGOLA DI PORTABILITÀ**: Tutti i collegamenti simbolici creati all'interno di dataset esportati via NFS **DEVONO** utilizzare percorsi **relativi** (`../`) calcolati a partire dalla directory padre del symlink di destinazione.

Poiché la gerarchia interna dei dataset NFS (es. la distanza relativa tra la cartella `library/` e la cartella `staging/`) rimane costante e identica per tutti i client, l'uso dei percorsi relativi garantisce la portabilità assoluta del filesystem a costo zero.

---

## 📐 L'Algoritmo di Risoluzione e Creazione (Python)

Per implementare programmaticamente questa strategia negli script di migrazione, si utilizza la libreria standard di Python (`os` e `os.path`).

L'algoritmo calcola dinamicamente il cammino relativo tra il file sorgente reale in staging e la cartella destinazione del symlink in library:

```python
import os

def create_portable_symlink(source_real_path, target_symlink_path):
    """
    Crea un symlink relativo altamente portabile su NFS.

    Args:
        source_real_path (str): Il percorso assoluto del file sorgente reale (es. in staging).
        target_symlink_path (str): Il percorso assoluto del symlink da creare (es. in library).
    """
    # 1. Ottieni la directory padre in cui risiederà il symlink
    target_parent_dir = os.path.dirname(target_symlink_path)

    # 2. Assicurati che la directory padre esista
    os.makedirs(target_parent_dir, exist_ok=True)

    # 3. Calcola il percorso relativo dal padre del symlink al file sorgente reale
    relative_source = os.path.relpath(source_real_path, target_parent_dir)

    # 4. Rimuovi un eventuale symlink preesistente per evitare errori
    if os.path.lexists(target_symlink_path):
        os.remove(target_symlink_path)

    # 5. Crea il collegamento simbolico relativo sul filesystem
    os.symlink(relative_source, target_symlink_path)
```

### Esempio Pratico di Risoluzione
Supponiamo che:
* File sorgente reale in staging: `/Volumes/classical/staging/Vladimir Horowitz/Horowitz at Home/01.mp3`
* Percorso symlink in library: `/Volumes/classical/library/Recitals/Vladimir Horowitz/[1989] Horowitz at Home/01 - Horowitz at Home.mp3`
* Directory padre del symlink: `/Volumes/classical/library/Recitals/Vladimir Horowitz/[1989] Horowitz at Home/`

Il calcolo di `os.path.relpath` restituirà:
`../../../../staging/Vladimir Horowitz/Horowitz at Home/01.mp3`

Questo percorso relativo è **perfettamente valido** sia su macOS che su Kubernetes, a prescindere dal prefisso del mountpoint.

---

## 🛡️ Guardrail e Best Practices

1. **Stesso Dataset NFS**: I symlink relativi funzionano a patto che il percorso sorgente e quello di destinazione appartengano allo stesso volume/dataset o siano esportati nello stesso share NFS, in modo che i cammini relativi rimangano validi.
2. **Preservazione dell'Inode (Seeding)**: Non copiare mai i file fisici per riorganizzarli. Il file in `staging` deve rimanere intatto per non compromettere l'indice di seeding del client torrent (qBittorrent).
3. **No Hardlink Cross-Filesystem**: Gli hardlink non possono essere usati cross-filesystem o su export NFS diversi. I symlink relativi rappresentano lo standard universale per questa tipologia di architetture distribuite.
4. **Utilizzo di `os.readlink` per il Re-allineamento**: Quando si risanano o si riorganizzano i symlink, per risalire al file sorgente reale senza cadere in loop di risoluzione, utilizzare `os.readlink` (o `Path.readlink()` in Python 3.9+) per leggere il target originale prima di cancellare il vecchio link.
