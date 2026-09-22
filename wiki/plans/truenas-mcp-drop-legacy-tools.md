---
title: "Togliere da truenas-master-mcp la zavorra pre-25"
type: plan
status: archived
certified_for_ai: true
created_at: 2026-09-22
tags:
  - "#plan"
  - "#truenas"
  - "#mcp"
---

# Togliere la zavorra pre-25

Su TrueNAS 25.10 e 26 le app sono container Docker (`app.*`). Prima di Electric Eel (24.10) erano chart Helm sul Kubernetes interno di SCALE, e su CORE erano jail. Quei tre modelli non esistono più nel lab. Il piano li toglie dall'interfaccia MCP di `pindaroli/truenas-master-mcp`.

Eseguito su `main` come `1.0.0-alpha.1` (`91c9530`). `v0.2.0` e `tn25` restano su `f2d48df`. Il cluster usa `ghcr.io/pindaroli/truenas-master-mcp:1.0.0-alpha.1`.

Il cluster usa `ghcr.io/pindaroli/truenas-master-mcp:1.0.0-alpha.1`. Il tag `v0.2.0` e il branch `tn25` non si spostano. `kubernetes-mcp` del cluster Talos non c'entra: è un altro server.

## Si toglie

Chart release, la generazione Helm:

- `list_chart_releases`
- `get_chart_release`
- `get_chart_release_resources`

Jails, solo CORE:

- `list_jails`, `get_jail`, `get_jail_by_name`, `create_jail`, `update_jail`, `delete_jail`, `start_jail`, `stop_jail`, `restart_jail`, `clone_jail`
- `list_jail_fstabs` (nel classificatore, non nel catalogo visibile)
- il fallback di `list_apps` / `get_app` che, se `app.query` non torna la forma attesa, chiama `/api/v2.0/jail`

Kubernetes interno a TrueNAS, il k3s tolto in 24.10:

- `get_kubernetes_status`, `get_kubernetes_nodes`, `get_kubernetes_pods`, `get_kubernetes_services`
- i metodi non pubblicati `configure_kubernetes`, `list_kubernetes_backups`, `create_kubernetes_backup`, `restore_kubernetes_backup`

`scale_app`. Imposta le repliche di un chart (`POST /api/v2.0/app/{name}/scale`). In 25 e in 26 non c'è `app.scale`.

## Si tiene

È API di 25.10 e di 26:

- ciclo vita app: `list_apps`, `get_app`, `create_app`, `update_app`, `delete_app`, `start_app`, `stop_app`, `restart_app` (in 26 è `app.redeploy`), `upgrade_app`, `rollback_app`, `get_app_config`, `get_app_upgrade_options`
- catalogo: `list_catalog_items`, `get_catalog`, `get_catalog_trains`, `get_catalog_item`, `refresh_catalogs`, `delete_catalog`
- immagini: `list_docker_images`, `pull_docker_image` (in 26 sono `app.image.*`)
- VM `vm.*` (libvirt, distinte dalle istanze `container.*` / `lxc.*` aggiunte in 26)
- pool, dataset, snapshot, SMB, NFS, iSCSI, utenti, gruppi, servizi, repliche, cloud sync, task rsync, chiavi SSH, certificati, alert, dischi

## Fuori da questo taglio

Presenti o plausibili su 25.10, assenti nell'indice JSON-RPC 26. Non sono zavorra pre-25: toglierli ora toglie funzioni del NAS attuale.

- `list_tftp_services`
- `list_smart_tests`, `create_smart_test`, `delete_smart_test`, `get_smart_config`, `update_smart_config`
- moduli rsync, `system/log`, filtri alert, espansione pool (metodi interni, già rifiutati dal translator con un errore esplicito)

Un secondo piano, a TrueNAS 26 installato, decide questi.

## Codice

1. `src/main.rs`: `list_tools`, `call_tool`, classificatore, testi che citano jail, chart release o il Kubernetes di TrueNAS.
2. `src/server.rs`: gli stessi `#[tool]` e le struct di richiesta.
3. `src/tools.rs`: metodi e struct `Jail`, `KubernetesStatus`. `list_apps` usa solo `app.*`.
4. `src/rest_map.rs`: i rami che rifiutano `jail`, `kubernetes` e `chart/release` restano come rete, con i test già presenti. Si aggiunge lo stesso rifiuto per `app/{id}/scale`.
5. Test di serializzazione di `Jail` e `KubernetesStatus`.
6. `README.md` e `src/lib.rs`: le app sono quelle Docker di SCALE.

Versione `1.0.0-alpha.1` in `VERSION`, `Cargo.toml` e `Cargo.lock`. Il workflow non pubblica `latest` (il tag contiene `-`). Dopo il push si verifica `:1.0.0-alpha.1` su GHCR e che `:latest` resti il digest di `0.2.0`.

Verifica: `cargo fmt --all -- --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test --all-features`.
