import sys
import os

config_file = 'talos-config/controlplane.yaml'
# Indentation matches the existing 'machine:' children (4 spaces)
new_config = """    disks:
        - device: /dev/sdb
          partitions:
            - mountpoint: /var/mnt/postgres
"""

if not os.path.exists(config_file):
    print(f"Error: {config_file} not found")
    sys.exit(1)

with open(config_file, 'r') as f:
    lines = f.readlines()

# Check if disk config is already present to avoid duplication
for line in lines:
    if "mountpoint: /var/mnt/postgres" in line:
        print("Config already present")
        sys.exit(0)

# Inject 'disks' section immediately after 'machine:' line
output_lines = []
for line in lines:
    output_lines.append(line)
    if line.strip() == "machine:":
        output_lines.append(new_config)

with open(config_file, 'w') as f:
    f.writelines(output_lines)

print("Successfully injected disk config into talos-config/controlplane.yaml")
