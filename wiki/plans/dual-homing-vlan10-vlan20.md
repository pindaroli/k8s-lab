---
title: "Dual-homing VLAN 10 e VLAN 20"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-25
tags:
  - "#plan"
  - "#network"
  - "#extreme"
  - "#truenas"
  - "#talos"
---

# Dual-homing VLAN 10 e VLAN 20

Rendere VLAN `server` (VID 10) e VLAN `client` (VID 20) due domini L2 separati, con i servizi TrueNAS, Docker e Traefik in ascolto su un indirizzo per VLAN. Un solo default gateway per host. Le ACL arrivano per ultime e servono a impedire il percorso asimmetrico, non ad accelerare il traffico.

Dati letti il 25 settembre 2026 dallo switch Extreme, da TrueNAS, dai tre Proxmox e dal cluster. `rete.json` non si usa per i cavi. Non eseguito.

## Principi

- Il multicast non attraversa le VLAN. Il TCP sulla stessa VLAN non passa dalla SVI.
- Un client usa solo l'indirizzo della propria VLAN.
- La seconda scheda ha solo la rotta connessa della sua subnet. Nessun secondo default.
- MetalLB annuncia ogni VIP solo sull'interfaccia di quella VLAN. Il VIP API `10.10.20.55` resta uno, sulla VLAN 20.
- `kubectl` e `talosctl` vedono i control plane su `10.10.20.141–143`. `validSubnets` tiene l'InternalIP su `10.10.20.0/24`. Gli indirizzi `10.10.10.141–143` servono solo all'NFS.
- Le modifiche Extreme sono playbook Ansible sul gruppo `switches`, modulo `extreme.exos`, come in `ansible/playbooks/configure_vlan_port9_trunk.yml`. Il file di policy si carica come file: `edit policy` non va dentro `exos_config`.

## Stato di partenza

- SVI: `10.10.10.1/24` su VLAN server, `10.10.20.1/24` su VLAN client. IP forwarding acceso. Nessuna ACL. Default dello switch: `192.168.2.254` sulla VLAN Default. Internet esce da OPNsense. Il traffico fra le due VLAN lo instrada lo switch, non OPNsense. DNS Unbound e DHCP Kea hanno OPNsense come destinazione (`192.168.2.254`), non come router interno.
- Porte 1–4 access untagged VLAN server: PVE3 `enp5s0f0` (porta 1), PVE1 `nic1` (porta 2), PVE2 `enp1s0f0np0` (porta 3), TrueNAS `enp1s0f0np0` `10.10.10.50` (porta 4, MAC `8c:fd:18:f7:f5:92`).
- Porte 5–7 access untagged VLAN client: PVE3 `enp5s0f1` (porta 5, Talos `.143` e Ollama), PVE1 `nic2` (porta 6, Talos `.141`), PVE2 `enp1s0f1np1` (porta 7, Talos `.142`).
- Porta 8: access untagged VLAN client, link 10 Gbit/s, nessun MAC e nessun vicino EDP. Non è il secondo DAC di TrueNAS: `enp1s0f1np1` ha `Link detected: no`. Non si cancella dalla VLAN client.
- Porte 9 e 10: trunk (untagged VID 1, taggate 10, 20, 30, 40, 99).
- Proxmox: `vmbr10` con `10.10.10.11`, `.21`, `.31`, default `10.10.10.1`. `vmbr20` su, senza IPv4. OOB `192.168.100.11` e `.21` su; su PVE3 `nic0` `192.168.100.31` è down.
- Talos: una sola NIC su `vmbr20`, `10.10.20.141–143`. NFS verso `10.10.10.50` passa dalle SVI. Pod CIDR Flannel `10.244.0.0/16`.
- MetalLB L2. Pool `10.10.20.56–60` senza interfaccia, in `metallb/metallb-complete.yaml`. Live: Traefik `10.10.20.56`, Postgres `10.10.20.57`. Il Service Traefik ha già `externalTrafficPolicy: Local` in `traefik/traefik-values.yaml` ed è un DaemonSet.
- Tdarr (`10.10.20.61`, manifest in `tdarr/k8s/`, non un values Helm) è fuori da questa migrazione e va spento: scale a zero del Deployment e rimozione del LoadBalancer, così il pool non resta appeso alle due schede.
- Docker su TrueNAS in ascolto su `0.0.0.0` (Jellyfin 8096, qBittorrent 8080/6881/30661, Prowlarr 9696, Homepage 3000, webhook 9000, Scrutiny 31054/31055). MinimServer è `network_mode: host` ([[minimserver-truenas-migration]]). Traefik lo raggiunge via Endpoints `10.10.10.50:9790`.
- DNS dei client: Unbound su OPNsense, nomi `*.pindaroli.org`. Playbook `ansible/playbooks/opnsense/opnsense_sync_dns.yml`.
- Il Mac è `10.10.20.100`, gateway `10.10.20.1`. Sul trunk della sua porta ci sono la VLAN 20 nativa e le VLAN 1 e 99 taggate. Non ha un'interfaccia sulla VLAN 10.

## Indirizzi nuovi

Fuori dall'ARP dello switch al momento della lettura. Si riservano su Kea prima di assegnarli.

- TrueNAS VLAN 20: `10.10.20.50/24` su `enp1s0f1np1`, senza gateway. `10.10.10.50/24` resta.
- Nodi, seconda vNIC: `10.10.10.141/24`, `.142/24`, `.143/24`, senza gateway.
- Traefik VLAN 10: `10.10.10.56`. Il pool `10.10.10.56–60` non è in auto-assign. `10.10.20.56` si inchioda nel values, così un upgrade non lo sposta.

## Regime

- Dalla VLAN 20, TrueNAS e Docker si chiamano su `10.10.20.50`, Traefik su `10.10.20.56`. Dalla VLAN 10, `10.10.10.50` e `10.10.10.56`. Stesse IngressRoute: guardano l'`Host`, non il VIP.
- Il Mac non entra nella VLAN 10. I servizi li usa sulla VLAN 20, a L2. La UI Proxmox (`10.10.10.11`, `.21`, `.31`) resta raggiungibile solo instradando `10.10.20.1` → `10.10.10.1`, ed è un'eccezione da decidere prima del deny totale.
- Un pod verso il Mac (`10.10.20.100`) esce da `eth0`. Flannel maschera il source con `10.10.20.141–143`. La risposta è L2 sulla VLAN 20. L'ACL sulla SVI non lo vede. Sul Mac il firewall deve accettare quei tre indirizzi di nodo; l'IP `10.244.x.x` non compare.
- OPNsense vede solo il traffico verso internet (default dello switch `192.168.2.254`), più DNS e DHCP di cui è destinazione.
- L'NFS dei nodi verso `10.10.10.50` esce da `eth1`, a L2, porte Extreme 1–3 verso la porta 4.
- `ohnet.subnet=10.10.20.0` annuncia l'SSDP solo sulla VLAN 20. La porta 9790 resta in ascolto anche su `10.10.10.50`.

## Fase 1 — Trovare il DAC

Si porta su `enp1s0f1np1` senza indirizzo. Si legge la FDB per `8c:fd:18:f7:f5:93`. Quella porta, se non è già access untagged VLAN client, lo diventa con un playbook e `save configuration primary`. Le porte 1–4 non si modificano. La porta 8 non si toglie dalla VLAN client.

Rollback: `ip link set enp1s0f1np1 down`.

## Fase 2 — TrueNAS sulla VLAN 20

Indirizzo statico `10.10.20.50/24`. Il default resta `10.10.10.1` su `enp1s0f0np0`.

Tunable solo su `enp1s0f0np0` e `enp1s0f1np1`: `arp_ignore=1`, `arp_announce=2`, `rp_filter=1`. Non su `all`: con i bridge Docker scarta traffico inoltrato.

Docker e l'HTTP di MinimServer, già su `0.0.0.0`, rispondono anche su `.50`. NFS accetta la subnet `10.10.20.0/24` negli export. SMB non si forza con `bind interfaces only`: il middleware di SCALE riscrive gli auxiliary parameters.

`10.10.10.50` continua a rispondere per tutta la fase. Rollback: indirizzo giù e interfaccia down.

## Fase 3 — Seconda vNIC Talos

Su ogni VM (`1300` su PVE1, `2300` su PVE2, `3200` su PVE3) una virtio su `vmbr10`. I bridge Proxmox non cambiano.

Patch solo sulla scheda nuova e su kubelet, un nodo alla volta. Non si riscrive `eth0` né il VIP `10.10.20.55`.

- `machine.kubelet.nodeIP.validSubnets`: `10.10.20.0/24`.
- `eth1`: `10.10.10.141/24` (`.142`, `.143`), dhcp spento, nessuna rotta di default.

I pod che escono ancora con source `10.10.20.14x` verso `10.10.10.50` si sistemano in fase 5, prima delle ACL.

Rollback: togliere la patch di `eth1` e la vNIC `net1`.

## Fase 4 — MetalLB e Traefik

Verificare i nomi `eth0` e `eth1` sul nodo dopo la fase 3. Lo speaker MetalLB è in host network e usa quei nomi.

- Pool `10.10.20.56–60`: `L2Advertisement` con `interfaces: [eth0]`. Traefik inchiodato a `10.10.20.56`. Postgres `10.10.20.57` resta su questa VLAN.
- Pool `10.10.10.56–60`, `autoAssign: false`, advertisement con `interfaces: [eth1]`.
- Nello stesso `service` di `traefik/traefik-values.yaml`, `additionalServices.vlan10`: LoadBalancer, annotazioni `metallb.universe.tf/address-pool` e `metallb.universe.tf/loadBalancerIPs: 10.10.10.56`, `externalTrafficPolicy: Local`. Stessi pod. Senza Local la risposta al VIP della VLAN 10 può uscire da `eth0`.
- Tdarr spento, come sopra, prima di vincolare le interfacce.

Rollback: cancellare il Service VLAN 10 e togliere il vincolo di interfaccia sull'advertisement VLAN 20.

## Fase 5 — DNS e backend

Unbound, non CoreDNS. La vista della VLAN 20 restituisce `10.10.20.50` per ciò che vive su TrueNAS e `10.10.20.56` per Traefik. La vista della VLAN 10 restituisce `10.10.10.50` o `10.10.10.56`.

Gli Endpoints che inoltrano da Traefik a `10.10.10.50` si aggiornano prima del filtro. Un client sulla VLAN 20 che entra da `10.10.20.56` deve trovare un backend su `10.10.20.50`, oppure un backend raggiunto dal nodo con source `10.10.10.14x`. Un client sulla VLAN 10 entra da `10.10.10.56` e parla con `10.10.10.50` a L2.

Finché un backend resta `10.10.10.50` e il pacchetto parte da `10.10.20.14x`, quel flusso passa ancora dalla SVI. È lecito solo fino alla fase 6.

## Fase 6 — ACL

Dopo il collaudo L2. Ingress sulla SVI `client` e sulla SVI `server`. Il L2 sulla stessa VLAN non le vede. Internet verso `192.168.2.254` non entra nel match.

Il deny è il traffico di servizio che ha già un sostituto L2: client VLAN 20 verso `10.10.10.50` e verso `10.10.10.141–143`; client VLAN 10 verso `10.10.20.56` e `10.10.20.50`.

Non si nega l'intera coppia di `/24` finché non è deciso cosa deve ancora attraversare le SVI. Candidati: il Mac verso la UI Proxmox `10.10.10.11/21/31`, e qualunque pod il cui source resti `10.10.20.14x` verso un indirizzo della VLAN 10.

Rollback: `configure access-list delete` delle due policy dalle VLAN.

## Collaudo

- `dig` dalla VLAN 20 restituisce `10.10.20.50` / `10.10.20.56`; da `10.10.10.11` restituisce `10.10.10.50` / `10.10.10.56`.
- `traceroute` verso l'IP della propria VLAN è un solo hop. Verso l'IP dell'altra VLAN, dopo le ACL, la sessione non si apre e il contatore di drop sale.
- `ss` su TrueNAS: su `10.10.10.50` nessuna sessione con peer `10.10.20.0/24`; su `10.10.20.50` solo peer di quella subnet.
- `talosctl pcap` porta 2049: niente su `eth0`, il flusso su `eth1` verso `10.10.10.50`.
- FDB: `8c:fd:18:f7:f5:93` sulla porta identificata in fase 1, VLAN client.
- Un control point sulla VLAN 20 vede MinimServer come `http://10.10.20.50:9790`.
- Un pod sul nodo raggiunge il Mac e sul Mac la sessione risulta da `10.10.20.141`, `.142` o `.143`.
