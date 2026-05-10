---
title: "Piano: Migrazione qBittorrent Incomplete su NVMe"
status: "Materialized"
priority: "High"
tags:
  - "#storage"
  - "#qbittorrent"
  - "#truenas"
---

# Piano di Migrazione: qBittorrent Temporary Storage (HDD -> NVMe)

L'obiettivo è spostare i download incompleti dal pool meccanico `oliraid` allo stripe NVMe `stripe` per migliorare le IOPS e ridurre il carico sui dischi durante il seeding/download contemporaneo.

## 1. Preparazione Storage (Materializzata)
- [x] Creato dataset (via Ansible): `stripe/qb_temp` con **Recordsize: 16K**.
- [x] Configurato owner **1000:1000** nel playbook.
- [x] Creati manifest K8s: `storage/incomplete-dw-pvc.yaml` (PV + PVC).
- [x] Aggiornato `oli-arr-values.yaml` con il nuovo mount point `/data/incomplete`.

## 2. Esecuzione (DA ESEGUIRE)
- [ ] Eseguire `ansible-playbook ansible/playbooks/truenas_nvme_setup.yml`.
- [ ] Eseguire `kubectl apply -f storage/incomplete-dw-pvc.yaml`.
- [ ] Eseguire `helm upgrade oli-arr charts/servarr -f servarr/arr-values.yaml`.
- [ ] Verificare il mount point nel pod.

## 3. Esecuzione Migrazione Fisica (In WebUI)
- [ ] Mettere in **Pausa** i torrent interessati.
- [ ] Eseguire `Set Location` verso `/data/incomplete` (gruppi di 10-20 torrent max).
- [ ] Verificare il cambio di stato da `Moving` a `Paused`.
- [ ] Eseguire `Force Recheck` per validare l'integrità.

## 🛡️ Guardrail & Rischi
- **Saturazione IOPS**: Non migrare tutto il pool `oliraid` in una volta (max 20 torrent per volta).
- **ARC Cache**: Monitoraggio RAM TrueNAS (33GB) durante la fase di copia fisica.
