---
title: Migrazione Switch L3 Core — ONTi 10G ➔ Extreme Networks X620-X10
status: active
certified_for_ai: true
created_at: 2026-08-06
---

# Piano Operativo: Migrazione Switch ONTi 10G ➔ Extreme Networks X620-X10

> [!IMPORTANT]
> **Stato Operativo**: **CONFIGURAZIONE SU EXTREME EXOS COMPLETATA CON SUCCESSO ✅**
> Lo switch Extreme Networks X620-X10 (`extreme`) è stato interamente configurato via SSH (`192.168.2.1`), verificato e salvato in memoria (`primary.cfg`).

---

## 1. Obiettivo e Mappatura Fisico/Logica

Sostituzione dello switch L3 Core **ONTi 8-porte 10G SFP+** con lo switch enterprise **Extreme Networks X620-X10** (10-porte 10G), preservando il routing simmetrico L3 con OPNsense e la struttura delle VLAN.

### 📋 Mappatura Porte Configurate su EXOS

- **Porta 1**: Trunk 10G ➔ Switch Horaco (`switch-25g-server` Porta 6/9)
  - Native VLAN 1 (`Default` Untagged)
  - Tagged VLANs: `10` (Server), `20` (Client), `30` (IoT), `99` (OOB)
- **Porta 2**: Access VLAN 10 (`server` Untagged) — Server LAN PVE DAC
- **Porta 3**: Access VLAN 10 (`server` Untagged) — Server LAN PVE1 Port 1 (`enp1s0f0`)
- **Porta 4**: Access VLAN 10 (`server` Untagged) — Server LAN PVE DAC (PVE3 `enp101s0f0`)
- **Porta 5**: Access VLAN 20 (`client` Untagged) — Client LAN PVE1 Port 2 (`enp1s0f1np1`)
- **Porta 6**: Access VLAN 20 (`client` Untagged) — Client LAN PVE DAC (PVE2)
- **Porta 7**: Access VLAN 10 (`server` Untagged) — Server LAN PVE DAC *(Impostata come Porta 2 su richiesta utente)*
- **Porta 8**: Access VLAN 20 (`client` Untagged) — Client LAN PVE DAC *(Impostata come Porta 5 su richiesta utente)*
- **Porte 9 e 10**: Porte di riserva 10G (VLAN 1 Untagged)

---

## 2. Configurazione Verificata sullo Switch Extreme (EXOS)

```exos
# Interfacce Layer 3 SVI
configure vlan Default ipaddress 192.168.2.1 255.255.255.0
enable ipforwarding vlan Default

configure vlan server ipaddress 10.10.10.1 255.255.255.0
enable ipforwarding vlan server

configure vlan client ipaddress 10.10.20.1 255.255.255.0
enable ipforwarding vlan client

enable ipforwarding

# Rotta di Default L3 verso OPNsense
configure iproute add default 192.168.2.254

# DNS Client & Bootprelay (DHCP Relay)
configure dns-client add name-server 192.168.2.254 vr VR-Default
configure bootprelay add 192.168.2.254 vr VR-Default
enable bootprelay ipv4 vlan client
enable bootprelay ipv4 vlan server

# Interfaccia Gestione (Default Transit)
# Configurazione gestita su VLAN 1 (192.168.2.1)
```

---

## 3. Checklist Collaudo Finale (Post-Cutover)

- [x] Configurazione L2/L3 applicata ed approvata via SSH.
- [x] Validazione automatica del file `rete.json` ed adeguamento script (`common.py`, `test_internet.sh`, `test_dns.sh`, `test_network_configs.py`).
- [ ] Swap fisico dei cavi DAC dallo switch ONTi allo switch Extreme.
- [ ] Verifica del link 10G sui LED delle porte 1-8.
- [ ] Test di ping dal Mac Studio verso i Gateway: `192.168.2.1`, `10.10.10.1`, `10.10.20.1`.
