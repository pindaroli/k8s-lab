import os

POP_COMP = "/Volumes/arrdata/media/music_backup/Compilations"
CLASS_COMP = "/Volumes/classical/library/Compilations"

def main():
    pop_dirs = []
    if os.path.exists(POP_COMP):
        pop_dirs = [d for d in os.listdir(POP_COMP) if os.path.isdir(os.path.join(POP_COMP, d))]

    class_dirs = []
    if os.path.exists(CLASS_COMP):
        class_dirs = [d for d in os.listdir(CLASS_COMP) if os.path.isdir(os.path.join(CLASS_COMP, d))]

    print(f"[*] Compilazioni in Pop/Rock ({len(pop_dirs)}):")
    for d in sorted(pop_dirs):
        print(f"  - {d}")

    print(f"\n[*] Compilazioni in Classica ({len(class_dirs)}):")
    for d in sorted(class_dirs):
        print(f"  - {d}")

    # Check for direct overlaps
    overlap = set(pop_dirs).intersection(set(class_dirs))
    print(f"\n[*] Overlap diretto in Compilations:")
    if overlap:
        for o in sorted(overlap):
            print(f"  [!] DUPLICATO: {o}")
    else:
        print("  [+] Nessun overlap trovato nelle compilazioni.")

if __name__ == "__main__":
    main()
