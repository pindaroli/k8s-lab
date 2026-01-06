import yaml
import sys

# Read the file content
with open('talos-config/controlplane.yaml', 'r') as f:
    content = f.read()

# The user stripped the top, so it starts with 'spec: "version...'
# Use yaml.safe_load to parse the structure. Since it's invalid top-level yaml in some sense if keys are missing but let's try.
# Or just manually extract the string.
try:
    data = yaml.safe_load(content)
    # If the user edit left it as valid yaml with a root key 'spec'
    if isinstance(data, dict) and 'spec' in data:
        # The value of spec is the big string
        real_yaml = data['spec']
        with open('talos-config/controlplane.yaml', 'w') as f_out:
            f_out.write(real_yaml)
        print("Success: Extracted spec string to file.")
    else:
        print("Error: Could not find 'spec' key in yaml.")
        # Fallback manual parsing if yaml load fails?
except Exception as e:
    print(f"Error parsing yaml: {e}")
