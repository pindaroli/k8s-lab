---
title: "Traefik Alone Reverse Proxy su TrueNAS (Porta 8443)"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-19
tags:
  - "#traefik"
  - "#truenas"
  - "#docker"
  - "#dns"
  - "#tls"
---

# Traefik Alone Reverse Proxy su TrueNAS (Porta 8443)

Questo piano definisce l'integrazione di un'istanza leggera di Traefik v3 su TrueNAS SCALE (`10.10.10.50`) per esporre i servizi Docker autonomi su porta HTTPS dedicata (`8443`) con certificati TLS validi (`*.pindaroli.org` via Cloudflare DNS-01) e record dedicati su OPNsense Unbound con suffisso `-alone.pindaroli.org`, preservando al 100% la configurazione nativa di TrueNAS.

> [!CAUTION]
> **PROTOCOLLO DI ESECUZIONE (STRICT PHASING & TEST-DRIVEN)**
> L'esecuzione è suddivisa in fasi sequenziali. Per ogni singola fase, eseguire le relative azioni e verificare con successo i test prima di procedere.

---

## 🏗️ FASE 1: Configurazione DNS su OPNsense Unbound
Registrazione degli Host Overrides locali per risolvere i domini "alone" direttamente sull'IP di TrueNAS (`10.10.10.50`), garantendo la risoluzione locale anche a cluster K8s/Proxmox spento.

### Azioni
1. Creazione record Unbound in OPNsense (*Services -> Unbound DNS -> Overrides*):
   - `homepage-alone.pindaroli.org` -> `10.10.10.50`
   - `jellyfin-alone.pindaroli.org` -> `10.10.10.50`
   - `qbittorrent-alone.pindaroli.org` -> `10.10.10.50`
   - `prowlarr-alone.pindaroli.org` -> `10.10.10.50`
   - `webhook-alone.pindaroli.org` -> `10.10.10.50`

### 🛑 CHECKPOINT FASE 1
- [ ] Verifica `dig @192.168.2.254 <servizio>-alone.pindaroli.org +short` risponde con `10.10.10.50`.

---

## 🔐 FASE 2: Preparazione Directory e Credenziali su TrueNAS
Configurazione dello storage persistente per Traefik e inserimento del token Cloudflare per la challenge DNS-01.

### Azioni
1. Creazione directory `/mnt/stripe/truenas-docker/traefik` su TrueNAS.
2. Inizializzazione file `acme.json` con permessi rigidi:
   ```bash
   touch /mnt/stripe/truenas-docker/traefik/acme.json
   chmod 600 /mnt/stripe/truenas-docker/traefik/acme.json
   ```
3. Aggiunta variabile `CF_DNS_API_TOKEN` nel file `/mnt/stripe/truenas-docker/.env` estraendo il segreto da `secrets-sops/cloudflare-token.enc.yaml`.

### 🛑 CHECKPOINT FASE 2
- [ ] Directory `traefik` e file `acme.json` (permessi 600) presenti.
- [ ] Variabile `CF_DNS_API_TOKEN` verificata in `.env`.

---

## 🐳 FASE 3: Aggiornamento Docker Compose e Deploy Traefik
Attivazione del container Traefik v3 e configurazione del routing dichiarativo tramite labels sui servizi esistenti.

### Azioni
1. Aggiornamento `/mnt/stripe/truenas-docker/docker-compose.yaml`:
   - Aggiunta servizio `traefik:v3.3` con binding porte `8443:8443` e `8088:8088`.
   - Aggiunta labels con Host(`*-alone.pindaroli.org`) su `homepage`, `jellyfin`, `qbittorrent`, `prowlarr`, `webhook-normalizer`.
2. Esecuzione `docker compose up -d` in `/mnt/stripe/truenas-docker/`.

### 🛑 CHECKPOINT FASE 3
- [ ] Container `traefik` attivo e in stato healthy/running.
- [ ] Log Traefik confermano avvio e attesa richieste su `:8443` e `:8088`.

---

## 📜 FASE 4: Validazione TLS e Handshake HTTPS
Verifica dell'avvenuta generazione del certificato Let's Encrypt wildcard `*.pindaroli.org` e del corretto funzionamento delle rotte.

### Azioni
1. Ispezione log ACME di Traefik per confermare la convalida Cloudflare DNS-01.
2. Esecuzione curl TLS senza `-k` su tutti gli endpoint standalone su porta `8443`.
3. Verifica redirect HTTP `8088` -> HTTPS `8443`.

### 🛑 CHECKPOINT FASE 4
- [ ] `curl -Iv https://jellyfin-alone.pindaroli.org:8443` restituisce HTTP 200/302 con certificato Let's Encrypt valido.
- [ ] `curl -I http://homepage-alone.pindaroli.org:8088` restituisce HTTP 301 verso `https://...:8443`.

---

## 🖥️ FASE 5: Integrazione Homepage Dashboard e Documentazione
Allineamento della dashboard per una navigazione pulita e intuitiva a cluster spento.

### Azioni
1. Aggiornamento configurazione servizi in `/mnt/stripe/truenas-docker/homepage/services.yaml` con i nuovi URL `https://*-alone.pindaroli.org:8443`.
2. Restart container `homepage`.
3. Verifica visiva da browser di `https://homepage-alone.pindaroli.org:8443`.
4. Allineamento cheatsheet e documentazione homelab.

### 🛑 CHECKPOINT FINALE
- [ ] Dashboard Homepage funzionante su `https://homepage-alone.pindaroli.org:8443` con lucchetto verde.
- [ ] Tutti i link della dashboard portano ai rispettivi servizi su porta 8443 con certificato SSL valido.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Pianificazione / Approvazione Utente
- **Ultima Azione Completata**: Aggiornato il naming a suffisso `-alone.pindaroli.org` su artifact e wiki plan.
- **Prossimo Passo Operativo**: Ottenere approvazione dell'utente e procedere alla Fase 1 (DNS OPNsense).
- **Blocchi/Decisioni Pendenti**: In attesa di approvazione per avviare la Fase 1.
