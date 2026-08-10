---
title: "Ansible Extreme EXOS Automation"
last_updated: "2026-08-06"
confidence: "High"
tags:
  - "#ansible"
  - "#network"
  - "#exos"
  - "#extreme"
provenance:
  - "ansible/requirements.yml"
---

# Ansible Extreme EXOS Automation (`extreme.exos`)

La gestione automatizzata degli switch **Extreme Networks EXOS** (inclusa la versione **EXOS 31**) è standardizzata nel repository tramite la Ansible Collection ufficiale **`extreme.exos`**.

---

## 1. Requisiti e Dipendenze

La collection viene gestita in modo dichiarativo tramite il file [`ansible/requirements.yml`](file:///Users/olindo/prj/k8s-lab/ansible/requirements.yml):

```yaml
collections:
  - name: extreme.exos
```

### Installazione
Per installare la collection e aggiornare le dipendenze locali:
```bash
ansible-galaxy collection install -r ansible/requirements.yml
```

---

## 2. Modalità di Connessione e Configurazione

La collection supporta due plugin di connessione principali verso gli switch EXOS v31:

### A. Network CLI (`ansible.netcommon.network_cli`) — Raccomandata via SSH
Utilizza SSH per interagire direttamente con la CLI dello switch.

**Variabili di Inventario (`inventory.ini` / `group_vars`):**
```ini
[switches]
exos-switch-01 ansible_host=192.168.100.100 ansible_user=admin

[switches:vars]
ansible_network_os=extreme.exos.exos
ansible_connection=ansible.netcommon.network_cli
ansible_network_cli_ssh_type=paramiko
ansible_ssh_common_args='-o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o PubkeyAcceptedKeyTypes=+ssh-rsa'
ansible_ssh_pass={{ sops_exos_password }}
```

### B. HTTP API (`ansible.netcommon.httpapi`) — Via REST API EXOS
Utilizza l'interfaccia HTTPS/RESTconf nativa di EXOS v31 per la comunicazione JSON/REST.

**Variabili di Inventario:**
```ini
[switches:vars]
ansible_network_os=extreme.exos.exos
ansible_connection=ansible.netcommon.httpapi
ansible_httpapi_use_ssl=true
ansible_httpapi_validate_certs=false
```

---

## 3. Moduli Principali Inclusi

| Modulo | Descrizione |
| :--- | :--- |
| `extreme.exos.exos_command` | Esegue comandi arbitrari `show` o di controllo e restituisce l'output. |
| `extreme.exos.exos_config` | Gestisce i blocchi di configurazione dichiarativa con supporto a diff e rollback. |
| `extreme.exos.exos_facts` | Raccoglie informazioni hardware, versione firmware EXOS e stato delle interfacce. |
| `extreme.exos.exos_vlans` | Modulo di risorsa per creare e gestire le VLAN ed i tag. |
| `extreme.exos.exos_interfaces` | Modulo di risorsa per gestire lo stato amministrativo delle porte. |
| `extreme.exos.exos_l2_interfaces` | Modulo di risorsa per l'assegnazione delle porte alle VLAN (untagged/tagged). |

---

## 4. Esempio di Playbook

```yaml
---
- name: Backup e Ispezione Switch EXOS
  hosts: switches
  gather_facts: no
  tasks:
    - name: Raccogli i fatti dello switch
      extreme.exos.exos_facts:
        gather_subset: all

    - name: Esegui comando di verifica VLAN
      extreme.exos.exos_command:
        commands:
          - show vlan
      register: vlan_output

    - name: Stampa output VLAN
      ansible.builtin.debug:
        var: vlan_output.stdout_lines
```

---

## Relazioni Architetturali
- Gestisce i dispositivi registrati in: [[Network_Registry]]
- Integrato nella pipeline Ansible del repository under [`ansible/`](file:///Users/olindo/prj/k8s-lab/ansible/).
