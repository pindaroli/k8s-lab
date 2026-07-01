#!/usr/bin/env python3
"""
ZFS Special VDEV Comprehensive Diagnostics Tool
Esegue un'analisi approfondita dello Special VDEV (mirror-2) nel pool oliraid:
- Spazio ed allocazione
- Stato SMART dei dischi fisici membri
- Statistiche di I/O Realtime
- Mapping logico della policy dei dataset
- Frammentazione fine dei metaslab (zdb)
"""
import subprocess
import re
import sys
import os

TEMP_DIR = "/Users/olindo/.gemini/antigravity/scratch"
TEMP_EXPECT_PATH = os.path.join(TEMP_DIR, "run_diagnostics.exp")
TEMP_SH_PATH = os.path.join(TEMP_DIR, "remote_diag.sh")

def create_payload_scripts():
    os.makedirs(TEMP_DIR, exist_ok=True)

    # 1. Creiamo lo script Bash pulito che girerà su TrueNAS
    # Su TrueNAS/FreeBSD non serve readlink per smartctl, digerisce bene i gptid.
    sh_content = """#!/bin/sh
echo "===LIST==="
zpool list -v oliraid

echo "===STATUS==="
zpool status -P oliraid

echo "===IOSTAT==="
zpool iostat -vy oliraid 1 1

echo "===LISTZFS==="
zfs list -r -H -o name,recordsize,special_small_blocks oliraid

echo "===SMART==="
for disk in $(zpool status -P oliraid | awk '/special/ {flag=1; next} /logs/ {flag=0} /cache/ {flag=0} flag && /\\/dev\\// {print $1}' | sort -u); do
    echo "===SMART:$disk==="
    smartctl -i -H -A "$disk"
done

echo "===ZDB==="
/usr/sbin/zdb -mm oliraid 2
"""
    with open(TEMP_SH_PATH, "w") as f:
        f.write(sh_content)
    os.chmod(TEMP_SH_PATH, 0o755)

    # 2. Creiamo lo script Expect che carica ed esegue il payload
    expect_content = f"""#!/usr/bin/expect -f
set timeout 120
match_max 1000000
# Disabilitiamo l'eco a schermo per non inquinare l'output di Python
log_user 0

set host "10.10.10.50"
set user "olindo"
set pass "REDACTED_SECRET"
set sh_path "{TEMP_SH_PATH}"

# STEP A: Copia lo script sul server in modo silente
spawn scp -o StrictHostKeyChecking=no -q $sh_path $user@$host:/tmp/remote_diag.sh
expect {{
    "*assword:*" {{ send "$pass\\r"; exp_continue }}
    "yes/no" {{ send "yes\\r"; exp_continue }}
    eof
}}

# STEP B: Esegui lo script con Sudo
# sudo -S legge la password da stdin, niente prompt visibili che rompono il parsing
# log_user 1 PRIMA dello spawn: se SSH usa key-auth, *assword:* non appare mai
# e senza questo lo script cattura output vuoto silenziosamente.
log_user 1
spawn ssh -o StrictHostKeyChecking=no $user@$host "echo '$pass' | sudo -S sh /tmp/remote_diag.sh"
expect {{
    "yes/no" {{ send "yes\\r"; exp_continue }}
    "*assword:*" {{
        send "$pass\\r"
        exp_continue
    }}
    eof {{
        # Fine esecuzione
    }}
    timeout {{
        puts stderr "TIMEOUT: Connessione SSH o esecuzione comandi fallita."
        exit 1
    }}
}}
"""
    with open(TEMP_EXPECT_PATH, "w") as f:
        f.write(expect_content)
    os.chmod(TEMP_EXPECT_PATH, 0o755)

def main():
    create_payload_scripts()

    # Assicuriamoci che paths standard siano disponibili per subprocess
    env = os.environ.copy()
    common_paths = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    current_path = env.get("PATH", "")
    for p in common_paths:
        if p not in current_path:
            current_path = f"{p}:{current_path}"
    env["PATH"] = current_path

    print("Connecting to TrueNAS and gathering diagnostics (could take 15-20 seconds)...")

    process = subprocess.Popen(
        ["expect", "-f", TEMP_EXPECT_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )

    stdout, stderr = process.communicate()

    # Gestione degli errori
    if process.returncode != 0 or "TIMEOUT" in stderr:
        print(f"\n[!] Errore critico di connessione o esecuzione. Codice: {process.returncode}")
        print(f"STDERR:\n{stderr.strip()}")
        # Pulizia prima di uscire
        if os.path.exists(TEMP_EXPECT_PATH):
            os.remove(TEMP_EXPECT_PATH)
        if os.path.exists(TEMP_SH_PATH):
            os.remove(TEMP_SH_PATH)
        sys.exit(1)

    # Pulizia
    if os.path.exists(TEMP_EXPECT_PATH):
        os.remove(TEMP_EXPECT_PATH)
    if os.path.exists(TEMP_SH_PATH):
        os.remove(TEMP_SH_PATH)

    # Split the output by sections
    sections = re.split(r'===([A-Z0-9:]+)===', stdout)

    space_output = ""
    status_output = ""
    iostat_output = ""
    list_output = ""
    smart_output = ""
    zdb_output = ""

    for i in range(1, len(sections), 2):
        sec_name = sections[i]
        sec_content = sections[i+1]

        if sec_name == "LIST":
            space_output = sec_content
        elif sec_name == "STATUS":
            status_output = sec_content
        elif sec_name == "IOSTAT":
            iostat_output = sec_content
        elif sec_name == "LISTZFS":
            list_output = sec_content
        elif sec_name == "SMART":
            smart_output = sec_content
        elif sec_name == "ZDB":
            zdb_output = sec_content

    # 1. Parse space allocation
    special_space = "Unknown"
    for line in space_output.splitlines():
        # Match mirror-2 (or mirror-X) space stats using regex to be robust
        match = re.search(r'mirror-\d+\s+([0-9\.\w]+)\s+([0-9\.\w]+)\s+([0-9\.\w]+)\s+\S+\s+\S+\s+(\S+)\s+(\S+)', line)
        if match:
            size, alloc, free, frag, cap = match.groups()
            special_space = f"size: {size:>4} | alloc: {alloc:>4} ({cap:>5}) | free: {free:>4} | frag: {frag:>4}"
            break
        # Fallback check
        parts = line.strip().split()
        if len(parts) >= 8 and parts[0].startswith("mirror-"):
            special_space = f"size: {parts[1]:>4} | alloc: {parts[2]:>4} ({parts[7]:>5}) | free: {parts[3]:>4} | frag: {parts[6]:>4}"
            break

    # 2. Parse SMART data
    smart_data = {}
    smart_blocks = re.split(r'===SMART:(\S+)===', smart_output)
    for i in range(1, len(smart_blocks), 2):
        disk_path = smart_blocks[i]
        block_text = smart_blocks[i+1]

        model = "Unknown"
        serial = "Unknown"
        health = "Unknown"
        temp = "N/A"
        life = "N/A"
        realloc = "N/A"
        crc = "0"

        for line in block_text.splitlines():
            if "Device Model:" in line or "Model Number:" in line:
                model = line.split(":", 1)[1].strip()
            elif "Serial Number:" in line:
                serial = line.split(":", 1)[1].strip()
            elif "overall-health self-assessment test result:" in line:
                health = line.split(":", 1)[1].strip()
            elif "SMART Health Status:" in line:
                health = line.split(":", 1)[1].strip()

            # Attributes parsing
            parts = line.strip().split()
            if len(parts) >= 10:
                attr_id = parts[0]
                attr_name = parts[1]
                raw_val = parts[9]
                value = parts[3]

                if attr_id == "5" or attr_name == "Reallocated_Sector_Ct":
                    realloc = raw_val
                elif attr_id == "194" or attr_name == "Temperature_Celsius":
                    temp = raw_val
                elif attr_id == "199" or attr_name == "UDMA_CRC_Error_Count" or attr_name == "CRC_Error_Count":
                    crc = raw_val
                elif attr_id == "245" or attr_name == "Percent_Life_Remaining" or attr_name == "Percent_Lifetime_Remaining":
                    life = f"{int(value)}%"
                elif attr_id == "233" or attr_name == "Media_Wearout_Indicator":
                    life = f"{int(value)}%"

        smart_data[disk_path] = {
            "model": model,
            "serial": serial,
            "health": health,
            "temp": temp,
            "life": life,
            "realloc": realloc,
            "crc": crc
        }

    # 3. Parse IOSTAT
    special_io = "Reads:   0 IOPS (   0 ) | Writes:   0 IOPS (   0 )"
    main_io = "Reads:   0 IOPS (   0 ) | Writes:   0 IOPS (   0 )"
    for line in iostat_output.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        if parts[0] == "mirror-2" and len(parts) >= 7:
            special_io = f"Reads: {parts[3]:>3} IOPS ({parts[5]:>5}) | Writes: {parts[4]:>3} IOPS ({parts[6]:>5})"
        elif parts[0] == "raidz2-0" and len(parts) >= 7:
            main_io = f"Reads: {parts[3]:>3} IOPS ({parts[5]:>5}) | Writes: {parts[4]:>3} IOPS ({parts[6]:>5})"

    # 4. Parse Dataset properties and effective policies
    datasets = []
    for line in list_output.splitlines():
        parts = line.strip().split('\t')
        if len(parts) >= 3:
            name = parts[0]
            recsize = parts[1]
            specblocks = parts[2]

            if specblocks in ("-", "none", "0"):
                policy = "Only Metadata"
            else:
                def to_bytes(size_str):
                    if size_str in ("-", "none", "0"):
                        return 0
                    match = re.match(r'^(\d+)([KMG]?)$', size_str, re.IGNORECASE)
                    if not match:
                        return 0
                    num = int(match.group(1))
                    unit = match.group(2).upper()
                    if unit == "K":
                        return num * 1024
                    elif unit == "M":
                        return num * 1024 * 1024
                    elif unit == "G":
                        return num * 1024 * 1024 * 1024
                    return num

                rec_bytes = to_bytes(recsize)
                spec_bytes = to_bytes(specblocks)

                if spec_bytes >= rec_bytes and rec_bytes > 0:
                    policy = "⚠️ ALL DATA ON SSD!"
                else:
                    policy = f"Metadata & Small Files (<= {specblocks})"

            datasets.append({
                "name": name,
                "recsize": recsize,
                "specblocks": specblocks,
                "policy": policy
            })

    # 5. Parse Metaslabs
    metaslabs = []
    current_ms = None
    current_free = None
    for line in zdb_output.splitlines():
        ms_match = re.search(r'metaslab\s+(\d+)\s+.*?\s+free\s+([0-9\.\w]+)', line)
        if ms_match:
            current_ms = int(ms_match.group(1))
            current_free = ms_match.group(2)
            continue

        frag_match = re.search(r'On-disk histogram:\s+fragmentation\s+(\d+)', line)
        if frag_match and current_ms is not None:
            frag = int(frag_match.group(1))
            metaslabs.append({
                "id": current_ms,
                "free": current_free,
                "frag": frag
            })
            current_ms = None
            current_free = None

    # Compute Metaslab stats
    avg_frag = 0.0
    min_frag = 0
    max_frag = 0
    low_frag_count = 0
    med_frag_count = 0
    high_frag_count = 0

    if metaslabs:
        frags = [m["frag"] for m in metaslabs]
        avg_frag = sum(frags) / len(frags)
        max_frag = max(frags)
        min_frag = min(frags)
        low_frag_count = len([m for m in metaslabs if m["frag"] < 30])
        med_frag_count = len([m for m in metaslabs if m["frag"] >= 30 and m["frag"] <= 60])
        high_frag_count = len([m for m in metaslabs if m["frag"] > 60])

    # Print Report
    print("\n" + "="*70)
    print("                 ZFS SPECIAL VDEV COMPREHENSIVE OVERVIEW")
    print("="*70)

    print("\n>>> 1. VDEV SPACE & ALLOCATION (zpool list)")
    print("-" * 70)
    print(f"vdev: mirror-2 | {special_space}")

    print("\n>>> 2. HARDWARE & DISK SMART HEALTH (smartctl)")
    print("-" * 70)
    for disk, info in smart_data.items():
        print(f"- Disk {disk:<9} ({info['model']}, S/N: {info['serial']}):")
        print(f"  HEALTH: {info['health']:<6} | Life: {info['life']:<4} | Temp: {info['temp']:>2}°C | Realloc: {info['realloc']:<2} | CRC Errors: {info['crc']}")

    print("\n>>> 3. REALTIME I/O STATISTICS (zpool iostat)")
    print("-" * 70)
    print(f"- Special VDEV (mirror-2) -> {special_io}")
    print(f"- Main HDD (raidz2-0)     -> {main_io}")

    print("\n>>> 4. DATASET POLICY MAPPING")
    print("-" * 70)
    print(f"{'Dataset':<40} {'RecSize':<8} {'SpecBlocks':<10} {'Effective Policy'}")
    print("-" * 70)
    for ds in datasets:
        # Hide system datasets unless warning to keep output clean, but show main ones
        if ".system" in ds["name"] and "⚠️" not in ds["policy"]:
            continue
        print(f"{ds['name']:<40} {ds['recsize']:<8} {ds['specblocks']:<10} {ds['policy']}")

    print("\n>>> 5. METASLAB FRAGMENTATION SUMMARY (zdb -mm)")
    print("-" * 70)
    if metaslabs:
        print(f"- Checked Metaslabs  : {len(metaslabs)}")
        print(f"- Avg Fragmentation  : {avg_frag:.2f}%")
        print(f"- Min Fragmentation  : {min_frag}%")
        print(f"- Max Fragmentation  : {max_frag}%")
        print(f"- Distribution:")
        print(f"  - Low (< 30%)        : {low_frag_count:>3} metaslabs ({low_frag_count/len(metaslabs)*100:.1f}%)")
        print(f"  - Medium (30% - 60%) : {med_frag_count:>3} metaslabs ({med_frag_count/len(metaslabs)*100:.1f}%)")
        print(f"  - High (> 60%)       : {high_frag_count:>3} metaslabs ({high_frag_count/len(metaslabs)*100:.1f}%)")
    else:
        print("- No metaslabs parsed.")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
