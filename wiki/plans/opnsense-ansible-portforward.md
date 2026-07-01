---
title: "Automazione Port Forwarding qBittorrent su OPNsense via Ansible"
status: active
certified_for_ai: true
date: 2026-07-01
tags:
  - "#opnsense"
  - "#ansible"
  - "#nat"
  - "#plan"
---

# Piano: Automazione Port Forwarding qBittorrent su OPNsense via Ansible

Questo piano descrive i passaggi per configurare in modo dichiarativo e automatizzato l'inoltro porte (Destination NAT) per qBittorrent (`10.10.20.60:30661`) su OPNsense 26.1.10 utilizzando Ansible.

## 🔍 Analisi e Razionale
L'analisi architetturale ha rivelato che:
1. Il plugin esterno `os-firewall` è obsoleto e incorporato nel core di OPNsense.
2. Le API del Destination NAT sono esposte nativamente sotto `/api/firewall/d_nat`.
3. Le collezioni Ansible comunitarie (come `oxlorg.opnsense`) non hanno ancora un modulo pronto per il "Destination NAT" (Port Forward), ma gestiscono solo Source NAT e 1:1 NAT.
4. Di conseguenza, useremo il modulo nativo `ansible.builtin.uri` per interagire direttamente con gli endpoint REST di OPNsense, integrando la transazionalità (Savepoint/Apply) consigliata.

## 🛠️ Fasi del Piano

### Fase 1: Verifica Endpoints API d_nat
Eseguiremo uno script di test Python locale per verificare quali endpoint del controller `/api/firewall/d_nat` sono attivi su OPNsense 26.1.10.
- Endpoint da testare:
  - `POST /api/firewall/d_nat/searchItem`
  - `GET /api/firewall/d_nat/get`

### Fase 2: Scrittura del Playbook Ansible
Creeremo un playbook Ansible `ansible/playbooks/opnsense_portforward.yml` che esegue:
1. Query delle regole esistenti (`searchItem` o `searchRule`) per verificare se esiste già una regola con la descrizione "qBittorrent P2P" o sulla porta `30661` (idempotenza).
2. Se non esiste, crea un savepoint (`POST /api/firewall/filter/savepoint`).
3. Esegue la chiamata `POST /api/firewall/d_nat/add_rule` inviando il payload JSON con:
   - `interface`: `wan`
   - `protocol`: `TCP/UDP`
   - `destination_net`: `any` o `WAN address`
   - `destination_port`: `30661`
   - `target`: `10.10.20.60`
   - `local-port` (redirect port): `30661`
   - `associated-rule-id`: `pass` (oppure una regola di filtro collegata)
4. Applica le modifiche (`POST /api/firewall/filter/apply`).
5. Effettua un test di connettività di ritorno e cancella il rollback (`POST /api/firewall/filter/cancel_rollback`).

### Fase 3: Esecuzione e Test di Verifica
1. Eseguiremo il playbook Ansible.
2. Monitoreremo i log del firewall e faremo un test di connettività esterna sulla porta `30661` per confermare lo sblocco di qBittorrent.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 1 (Verifica Endpoints API d_nat)
- **Ultima Azione Completata**: Generazione del piano di migrazione e test preliminare delle API Key (successo su `/api/firewall/filter/searchRule`).
- **Prossimo Passo Operativo**: Modificare ed eseguire lo script di test Python `scratch/test_opnsense_nat_api.py` per confermare gli URL esatti del modulo `d_nat`.
- **Blocchi/Decisioni Pendenti**: Attesa del via libera dell'utente per eseguire i test API del modulo `d_nat`.
