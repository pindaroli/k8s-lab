---
title: "Dual-homing VLAN 10 e VLAN 20"
type: plan
status: archived
certified_for_ai: false
obsolete: true
created_at: 2026-09-25
discarded_at: 2026-09-25
superseded_by: "[[truenas-lacp-vlan10]]"
tags:
  - "#plan"
  - "#network"
  - "#extreme"
  - "#truenas"
  - "#talos"
---

# Dual-homing VLAN 10 e VLAN 20

> [!WARNING]
> **Scartato** (2026-09-25). Piano abbandonato, non eseguito. Non usare questo documento per nuove configurazioni.

TrueNAS ha un indirizzo su ciascuna VLAN. I nodi Talos stanno solo sulla VLAN 10, con una sola scheda. Le ACL arrivano per ultime e servono a impedire il percorso asimmetrico, non ad accelerare il traffico.

Dati letti il 25 settembre 2026 dallo switch Extreme, da TrueNAS, dai tre Proxmox e dal cluster. `rete.json` non si usa per i cavi. Non eseguito.

## Principi

- VLAN `server` (VID 10, `10.10.10.0/24`) e VLAN `client` (VID 20, `10.10.20.0/24`) restano due domini L2. Il multicast non le attraversa.
- TrueNAS (UI, NFS, SMB, Docker) risponde su `10.10.10.50` e su `10.10.20.50`. Un solo default, `10.10.10.1`. La seconda scheda ha solo la rotta connessa.
- Talos ha una sola vNIC, su `vmbr10`. Niente seconda scheda, niente `validSubnets` per tenere un indirizzo sull'altra VLAN, niente MetalLB su due interfacce.
- L'identità del nodo, il VIP API e Traefik stanno sulla VLAN 10. `kubectl` e `talosctl` dal Mac (`10.10.20.100`) ci arrivano instradando, in modo simmetrico, attraverso le SVI. Non è il percorso asimmetrico: il nodo non ha una rotta connessa verso la VLAN 20, quindi la risposta torna dalla stessa SVI.
- I pod verso il Mac escono mascherati con l'IP del nodo sulla VLAN 10 e lo switch li instrada verso `10.10.20.100`. Anche questo flusso è simmetrico e va lasciato passare dalle ACL.
- Un client della VLAN 20 usa `10.10.20.50` per TrueNAS e Docker. Non chiama `10.10.10.50`.
- Le modifiche Extreme sono playbook Ansible sul gruppo `switches`, modulo `extreme.exos`, come in `ansible/playbooks/configure_vlan_port9_trunk.yml`. Il file di policy si carica come file: `edit policy` non va dentro `exos_config`.

## Stato di partenza

- SVI: `10.10.10.1/24` su VLAN server, `10.10.20.1/24` su VLAN client. IP forwarding acceso. Nessuna ACL. Default dello switch: `192.168.2.254` sulla VLAN Default. Internet esce da OPNsense. Il traffico fra le due VLAN lo instrada lo switch, non OPNsense. DNS Unbound e DHCP Kea hanno OPNsense come destinazione (`192.168.2.254`), non come router interno.
- Porte 1–4 access untagged VLAN server: PVE3 `enp5s0f0` (porta 1), PVE1 `nic1` (porta 2), PVE2 `enp1s0f0np0` (porta 3), TrueNAS `enp1s0f0np0` `10.10.10.50` (porta 4, MAC `8c:fd:18:f7:f5:92`).
- Porte 5–7 access untagged VLAN client: PVE3 `enp5s0f1` (porta 5, Talos `.143` e Ollama), PVE1 `nic2` (porta 6, Talos `.141`), PVE2 `enp1s0f1np1` (porta 7, Talos `.142`).
- Porta 8: access untagged VLAN client, link 10 Gbit/s, nessun MAC e nessun vicino EDP. Non è il secondo DAC di TrueNAS: `enp1s0f1np1` ha `Link detected: no`. Non si cancella dalla VLAN client.
- Porte 9 e 10: trunk (untagged VID 1, taggate 10, 20, 30, 40, 99).
- Proxmox: `vmbr10` con `10.10.10.11`, `.21`, `.31`, default `10.10.10.1`. `vmbr20` su, senza IPv4. Corosync ha un solo anello su quegli indirizzi di `vmbr10` (`corosync.conf`: `10.10.10.11`, `.21`, `.31`). OOB `192.168.100.11` e `.21` su; su PVE3 `nic0` `192.168.100.31` è down.
- Talos: una sola NIC su `vmbr20`, `10.10.20.141–143`, VIP API `10.10.20.55`. NFS verso `10.10.10.50` passa dalle SVI. Pod CIDR Flannel `10.244.0.0/16`.
- MetalLB L2. Pool `10.10.20.56–60` senza interfaccia, in `metallb/metallb-complete.yaml`. Live: Traefik `10.10.20.56`, Postgres `10.10.20.57`. Il Service Traefik ha già `externalTrafficPolicy: Local` in `traefik/traefik-values.yaml` ed è un DaemonSet.
- Tdarr (`10.10.20.61`, manifest in `tdarr/k8s/`, non un values Helm) è fuori da questa migrazione e va spento: scale a zero del Deployment e rimozione del LoadBalancer.
- Docker su TrueNAS in ascolto su `0.0.0.0` (Jellyfin 8096, qBittorrent 8080/6881/30661, Prowlarr 9696, Homepage 3000, webhook 9000, Scrutiny 31054/31055). MinimServer è `network_mode: host` ([[minimserver-truenas-migration]]). Traefik lo raggiunge via Endpoints `10.10.10.50:9790`.
- DNS dei client: Unbound su OPNsense, nomi `*.pindaroli.org`. Playbook `ansible/playbooks/opnsense/opnsense_sync_dns.yml`.
- Il Mac è `10.10.20.100`, gateway `10.10.20.1`. Sul trunk della sua porta ci sono la VLAN 20 nativa e le VLAN 1 e 99 taggate. Non ha un'interfaccia sulla VLAN 10.

## Indirizzi nuovi

Fuori dall'ARP dello switch al momento della lettura del 25 settembre. Si riservano prima di assegnarli.

- TrueNAS VLAN 20: `10.10.20.50/24` su `enp1s0f1np1`, senza gateway. `10.10.10.50/24` resta.
- Talos, unica scheda, dopo lo spostamento su `vmbr10`: `10.10.10.141/24`, `.142/24`, `.143/24`. Default `10.10.10.1`. VIP API `10.10.10.55`.
- Traefik e Postgres si spostano nel pool `10.10.10.56–60`. Traefik `10.10.10.56`. Postgres `10.10.10.57`. Il pool `10.10.20.56–60` si ritira quando nessun Service lo usa più: un nodo solo sulla VLAN 10 non può annunciare un VIP della VLAN 20.

## Regime

- Dalla VLAN 20, TrueNAS e Docker si chiamano su `10.10.20.50`, a livello 2. Dalla VLAN 10, su `10.10.10.50`, a livello 2. L'NFS dei nodi verso `10.10.10.50` è sullo stesso segmento, porte Extreme 1–3 verso la porta 4.
- Traefik ha un solo VIP, `10.10.10.56`. Il Mac ci arriva da `10.10.20.100` tramite `10.10.20.1`. Andata e ritorno passano dalla SVI. Le IngressRoute non cambiano: guardano l'`Host`.
- `kubectl` e `talosctl` usano `10.10.10.55` e `10.10.10.141–143`. Dal Mac il percorso è lo stesso della UI Proxmox: instradato e simmetrico.
- Un pod verso il Mac esce con source `10.10.10.141`, `.142` o `.143`. Lo switch lo consegna a `10.10.20.100`. La risposta torna al nodo dalla SVI. L'ACL deve lasciar passare questa coppia. Sul Mac il firewall accetta quei tre indirizzi; l'IP `10.244.x.x` non compare.
- Corosync non si tocca: resta l'anello su `10.10.10.11`, `.21`, `.31`. Spostare la vNIC della VM da `vmbr20` a `vmbr10` non cambia gli indirizzi dell'hypervisor.
- OPNsense vede solo il traffico verso internet, più DNS e DHCP di cui è destinazione.
- `ohnet.subnet=10.10.20.0` annuncia l'SSDP solo sulla VLAN 20. La porta 9790 resta in ascolto anche su `10.10.10.50`.

## Fase 1 — Trovare il DAC

Si porta su `enp1s0f1np1` senza indirizzo. Si legge la FDB per `8c:fd:18:f7:f5:93`. Quella porta, se non è già access untagged VLAN client, lo diventa con un playbook e `save configuration primary`. Le porte 1–4 non si modificano. La porta 8 non si toglie dalla VLAN client.

Rollback: `ip link set enp1s0f1np1 down`.

## Fase 2 — TrueNAS sulla VLAN 20

Indirizzo statico `10.10.20.50/24`. Il default resta `10.10.10.1` su `enp1s0f0np0`.

Tunable solo su `enp1s0f0np0` e `enp1s0f1np1`: `arp_ignore=1`, `arp_announce=2`, `rp_filter=1`. Non su `all`: con i bridge Docker scarta traffico inoltrato.

Docker e l'HTTP di MinimServer, già su `0.0.0.0`, rispondono anche su `.50`. NFS accetta la subnet `10.10.20.0/24` negli export. SMB non si forza con `bind interfaces only`: il middleware di SCALE riscrive gli auxiliary parameters.

`10.10.10.50` continua a rispondere per tutta la fase. Rollback: indirizzo giù e interfaccia down.

## Fase 3 — Talos su vmbr10

Si spegne Tdarr prima, così `10.10.20.61` non resta da annunciare.

Su ogni VM (`1300` su PVE1, `2300` su PVE2, `3200` su PVE3) l'unica vNIC passa da `vmbr20` a `vmbr10`. Non se ne aggiunge una seconda. Un nodo alla volta, partendo da un follower, il VIP per ultimo insieme al nodo che lo tiene.

La patch Talos riscrive l'unica interfaccia, perché l'indirizzo cambia VLAN:

- indirizzo `10.10.10.141/24` (`.142`, `.143`);
- default `10.10.10.1`;
- VIP `10.10.10.55` al posto di `10.10.20.55`;
- `machine.kubelet.nodeIP.validSubnets`: `10.10.20.0/24` si toglie. L'InternalIP è `10.10.10.14x`.

Dopo il nodo si aggiornano kubeconfig e talosconfig sul Mac. Flannel rifà i tunnel VXLAN fra i nuovi indirizzi di nodo. L'NFS verso `10.10.10.50` diventa la rotta connessa, senza passare dalla SVI.

Rollback: vNIC di nuovo su `vmbr20` e ripristino degli indirizzi `10.10.20.141–143` con VIP `10.10.20.55`.

## Fase 4 — MetalLB e Traefik sulla VLAN 10

Un solo pool, `10.10.10.56–60`, al posto di `10.10.20.56–60`. L'advertisement non elenca interfacce: il nodo ne ha una sola, ed è sulla VLAN 10.

In `traefik/traefik-values.yaml` il Service esistente si inchioda a `10.10.10.56`, `externalTrafficPolicy: Local` resta. Niente `additionalServices`: non c'è una seconda scheda su cui annunciare `10.10.20.56`. Postgres `10.10.20.57` si sposta a `10.10.10.57` nello stesso pool.

Le IngressRoute restano. I nomi che oggi risolvono `10.10.20.56` passeranno a `10.10.10.56` in fase 5.

Rollback: ripristinare il pool `10.10.20.56–60` e il VIP `10.10.20.56`, dopo che i nodi sono di nuovo sulla VLAN 20.

## Fase 5 — DNS e backend

Unbound, non CoreDNS.

- Dalla VLAN 20, i nomi di ciò che vive su TrueNAS (`jellyfin`, `minimserver`, e gli altri sullo stesso host) restituiscono `10.10.20.50`. I nomi serviti da Traefik restituiscono `10.10.10.56`.
- Dalla VLAN 10, TrueNAS restituisce `10.10.10.50` e Traefik `10.10.10.56`.

Gli Endpoints che inoltrano da Traefik a `10.10.10.50` possono restare: il nodo è sulla stessa VLAN del backend, il source è `10.10.10.14x`, il percorso è L2. Non serve più un backend `10.10.20.50` per il traffico che entra da Traefik.

## Fase 6 — ACL

Dopo il collaudo L2. Ingress sulla SVI `client` e sulla SVI `server`. Il L2 sulla stessa VLAN non le vede. Internet verso `192.168.2.254` non entra nel match.

Si nega il percorso che avrebbe un sostituto e che, con due schede, sarebbe asimmetrico. Con Talos su una sola scheda l'asimmetria non nasce sul nodo: la risposta a un client della VLAN 20 torna dalla SVI. Il deny che resta utile è la VLAN 20 verso `10.10.10.50`, perché quel servizio si chiama su `10.10.20.50`.

Si lascia passare, perché non ha un sostituto sulla VLAN 20:

- Mac e gli altri client `10.10.20.0/24` verso `10.10.10.55`, `10.10.10.56`, `10.10.10.57`, `10.10.10.141–143` (API, Traefik, Postgres, nodi) e verso `10.10.10.11`, `.21`, `.31` (UI Proxmox);
- nodi `10.10.10.141–143` verso `10.10.20.100` (pod verso il Mac) e verso gli altri host della VLAN 20 che i pod devono raggiungere.

Non si nega l'intera coppia di `/24`. Quel deny spegnerebbe `kubectl` dal Mac e i pod verso il Mac.

Rollback: `configure access-list delete` delle policy dalle VLAN.

## Collaudo

- `dig` dalla VLAN 20: TrueNAS e Docker su `10.10.20.50`, Traefik su `10.10.10.56`. Da `10.10.10.11`: TrueNAS su `10.10.10.50`, Traefik su `10.10.10.56`.
- `traceroute` dal Mac a `10.10.20.50` è un solo hop. Verso `10.10.10.56` e `10.10.10.55` passa da `10.10.20.1` e la sessione si apre.
- Dal Mac, `kubectl get nodes` mostra `10.10.10.141–143`. `talosctl` parla con `10.10.10.55`.
- `traceroute` da un nodo a `10.10.10.50` è un solo hop, senza la SVI.
- `ss` su TrueNAS: su `10.10.10.50` nessuna sessione con peer `10.10.20.0/24`; su `10.10.20.50` solo peer di quella subnet.
- Un pod raggiunge il Mac e sul Mac la sessione risulta da `10.10.10.141`, `.142` o `.143`.
- FDB: i MAC delle VM Talos sono sulla VLAN server, porte 1–3. `8c:fd:18:f7:f5:93` è sulla porta del DAC, VLAN client.
- Un control point sulla VLAN 20 vede MinimServer come `http://10.10.20.50:9790`.
- `corosync-cfgtool -s` resta connected su `10.10.10.11`, `.21`, `.31`.
