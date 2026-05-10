#!/usr/bin/env python3
"""
Inietta la configurazione del disco per Postgres in talos-config/controlplane.yaml.
"""
import sys
import os

# Configurazione percorsi
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
config_file = os.path.join(PROJECT_ROOT, 'talos-config/controlplane.yaml')

# Indentation matches the existing 'machine:' children (4 spaces)
new_config = """    disks:
        - device: /dev/sdb
          partitions:
            - mountpoint: /var/mnt/postgres
"""

def main():
    # Salva il CWD originale
    original_cwd = os.getcwd()
    try:
        # Spostati nella root del progetto
        os.chdir(PROJECT_ROOT)

        if not os.path.exists(config_file):
            print(f"Error: {config_file} not found")
            sys.exit(1)

        with open(config_file, 'r') as f:
            lines = f.readlines()

        # Check if disk config is already present to avoid duplication
        for line in lines:
            if "mountpoint: /var/mnt/postgres" in line:
                print("Config already present")
                return

        # Inject 'disks' section immediately after 'machine:' line
        output_lines = []
        for line in lines:
            output_lines.append(line)
            if line.strip() == "machine:":
                output_lines.append(new_config)

        with open(config_file, 'w') as f:
            f.writelines(output_lines)

        print(f"Successfully injected disk config into {config_file}")
    finally:
        # Ripristina CWD
        os.chdir(original_cwd)

if __name__ == "__main__":
    main()
