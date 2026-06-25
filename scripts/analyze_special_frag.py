#!/usr/bin/env python3
"""
ZFS Special VDEV Fragmentation Analyzer
Connette via SSH a TrueNAS, esegue zdb -mm oliraid 2 ed analizza la frammentazione dei metaslab.
"""
import subprocess
import re
import sys

def main():
    # SSH Command to run on TrueNAS using expect wrapper for password
    ssh_cmd = [
        "expect", "-c", """
        set timeout 60
        spawn ssh -o StrictHostKeyChecking=no olindo@10.10.10.50 "sudo -S /usr/sbin/zdb -mm oliraid 2"
        expect {
            "password:" {
                send "REDACTED_SECRET\\r"
                exp_continue
            }
            "password for olindo:" {
                send "REDACTED_SECRET\\r"
                exp_continue
            }
            eof
        }
        """
    ]

    print("Running zdb on TrueNAS (could take 10-20 seconds)...")
    process = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    # Parse the output
    metaslabs = []
    current_ms = None
    current_free = None

    for line in stdout.splitlines():
        # Match metaslab declaration line
        ms_match = re.search(r'metaslab\s+(\d+)\s+.*?\s+free\s+([0-9\.\w]+)', line)
        if ms_match:
            current_ms = int(ms_match.group(1))
            current_free = ms_match.group(2)
            continue

        # Match fragmentation line
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

    if not metaslabs:
        print("Error: No metaslabs parsed. Output was:")
        print(stdout[:1000])
        sys.exit(1)

    # Analyze data
    frags = [m["frag"] for m in metaslabs]
    avg_frag = sum(frags) / len(frags)
    max_frag = max(frags)
    min_frag = min(frags)

    max_ms = [m for m in metaslabs if m["frag"] == max_frag]
    min_ms = [m for m in metaslabs if m["frag"] == min_frag]

    low_frag = [m for m in metaslabs if m["frag"] < 30]
    med_frag = [m for m in metaslabs if m["frag"] >= 30 and m["frag"] <= 60]
    high_frag = [m for m in metaslabs if m["frag"] > 60]

    print("\n" + "="*50)
    print("      SPECIAL VDEV (MIRROR-2) FRAGMENTATION ANALYSIS")
    print("="*50)
    print(f"Total Metaslabs Checked: {len(metaslabs)}")
    print(f"Average Fragmentation  : {avg_frag:.2f}%")
    print(f"Minimum Fragmentation  : {min_frag}% (Metaslab(s): {', '.join(str(m['id']) for m in min_ms)})")
    print(f"Maximum Fragmentation  : {max_frag}% (Metaslab(s): {', '.join(str(m['id']) for m in max_ms)})")
    print("-"*50)
    print("Distribution by Fragmentation Level:")
    print(f"  - Low (< 30%)        : {len(low_frag)} metaslabs ({len(low_frag)/len(metaslabs)*100:.1f}%)")
    print(f"  - Medium (30% - 60%) : {len(med_frag)} metaslabs ({len(med_frag)/len(metaslabs)*100:.1f}%)")
    print(f"  - High (> 60%)       : {len(high_frag)} metaslabs ({len(high_frag)/len(metaslabs)*100:.1f}%)")
    print("="*50)

if __name__ == "__main__":
    main()
