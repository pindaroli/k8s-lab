#!/bin/bash
# Manually check OPNsense API for Host Overrides

# Load secrets (hacky grep from secrets file or hardcoded for test)
# Since we are in the agent, I will use the vault Decrypt to get the values just for this ephemeral script or ask user?
# Better: use the vars/secrets.yml via ansible-vault view? No, that requires interactivity.
# I will try to use the raw credentials I have in context or ask ansible to print them? 
# I will use a simple python script that imports secret file? 
# Simplest: Inline the credentials here since I know them (User provided them in Step 206).
# WAIT: The User provided them, I can use them.
# WARNING: I should avoiding outputting them in clear text artifacts if possible.
# But this file is created in the workspace.
# I will create a python script that decrypts the vault using the password file and runs the request.

# Actually, I can just use ansible to debug the searchHostOverride.

cat <<EOF > ansible/debug_api.yml
---
- name: Debug OPNsense API
  hosts: localhost
  connection: local
  bcome: no
  vars:
    opnsense_url: "https://192.168.2.254"
    api_key: "{{ opnsense_api_key }}"
    api_secret: "{{ opnsense_api_secret }}"
  
  vars_files:
    - "vars/secrets.yml"

  tasks:
    - name: Search Host Overrides
      uri:
        url: "{{ opnsense_url }}/api/unbound/settings/searchHostOverride"
        method: POST
        user: "{{ api_key }}"
        password: "{{ api_secret }}"
        force_basic_auth: yes
        validate_certs: no
        body_format: json
        body:
          current: 1
          rowCount: 100
        return_content: yes
      register: search_result

    - name: Show Results
      debug:
        msg: "{{ search_result.json }}"
EOF

ansible-playbook ansible/debug_api.yml
