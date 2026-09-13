---
title: "Arricchimento Naming Multi-Versione FileBot Normalizer (Edizione, Sorgente e Gruppo)"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-13
tags:
  - "#servarr"
  - "#filebot"
  - "#normalizer"
  - "#jellyfin"
  - "#kubernetes"
  - "#helm"
---

# Arricchimento Naming Multi-Versione FileBot Normalizer (Edizione, Sorgente e Gruppo)

## 🎯 Obiettivo del Piano
Estendere la formula di rinomina automatica di **FileBot AMC** (`normalize-video.sh`) per gestire in modo nativo e robusto le versioni multiple dello stesso film in `/media/movies/`.

L'obiettivo è prevenire sovrascritture accidentali dovute a `--conflict override` quando coesistono release della stessa risoluzione (es. due 1080p, uno WEB-DL con audio italiano e uno WEBRip originale), permettendo a **Jellyfin** di raggruppare i file nella scheda film ed esporre all'utente un menu a tendina chiaro e descrittivo.

---

## 🏗️ Analisi Tecnica e Architettura del Naming

### Formula Attuale (v1.3.0)
```groovy
--def "movieFormat={n} ({y}) [tmdbid-{id}]/{n} ({y}) [tmdbid-{id}] - [{vf} {vc}]"
```
* **Criticità**: Release con medesima risoluzione e codec (es. `1080p HEVC`) generano nomi target identici al carattere.
* Con `--conflict override`, l'ultima release elaborata sovrascrive l'hardlink della precedente.

### Nuova Formula (v1.4.0)
```groovy
--def "movieFormat={n} ({y}) [tmdbid-{id}]/{n} ({y}) [tmdbid-{id}]{ ' [' + edition + ']' } - [{ any{source + ' '}{''} }{vf} {vc}]{ ' [' + group + ']' }"
```

#### Regole Semantiche Groovy:
1. **Edizione (`{ ' [' + edition + ']' }`)**: se presente nel titolo della release (es. `Director's Cut`, `Extended`, `Theatrical`, `Unrated`), viene inserita. Se assente, viene omessa senza lasciare spazi o parentesi vuote.
2. **Sorgente (`{ any{source + ' '}{''} }`)**: estrae il tipo di supporto (es. `BluRay`, `WEB-DL`, `WEBRip`, `Remux`). Se non rilevabile, prosegue senza alterare il formato.
3. **Risoluzione & Codec (`{vf} {vc}`)**: garantisce la specifica tecnica (es. `1080p HEVC`, `2160p x265`).
4. **Release Group (`{ ' [' + group + ']' }`)**: traccia il gruppo autore del mux/encode (es. `Paso77`, `GalaxyRG265`, `NAHOM`), garantendo l'unicità anche a parità di sorgente e risoluzione.

---

## 🛠️ Piano di Intervento

### Fase 1: Repository `pindaroli-arr-helm`
1. Aggiornare `custom-docker-images/custom-normalizer/normalize-video.sh` con la nuova formula Groovy.
2. Incrementare `custom-docker-images/custom-normalizer/VERSION` a `1.4.0`.
3. Aggiornare `charts/servarr/files/trigger-job.sh` con l'immagine `ghcr.io/pindaroli/custom-normalizer:1.4.0`.
4. Incrementare la versione del chart `servarr` in `charts/servarr/Chart.yaml` a `1.9.8`.
5. Effettuare commit e push su GitHub per attivare la build automatica su GHCR.

### Fase 2: Repository `k8s-lab`
1. Allineare `scripts/kubernetes/yaml/job-normalizzation-template.yaml` alla versione `1.4.0`.
2. Eseguire l'upgrade Helm del chart `servarr` nel namespace `arr`:
   `helm upgrade --install servarr charts/servarr -f ../k8s-lab/servarr/arr-values.yaml -n arr`
3. Eseguire il rollout restart del deployment `servarr-qbittorrent` per ricaricare la ConfigMap montata.

### Fase 3: Validazione Test-Driven
1. Lanciare l'ingestion della release secondaria `The.Village.2004.1080p.WEBRip.DDP5.1.x265.10bit-GalaxyRG265[TGx]`.
2. Verificare che FileBot crei il file distinto:
   `/media/movies/The Village (2004) [tmdbid-6947]/The Village (2004) [tmdbid-6947] - [WEBRip 1080p HEVC] [GalaxyRG265].mkv`.
3. Verificare su TrueNAS che il file precedente Paso77 sia intatto e che i file video presenti nella cartella siano ora due.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: **COMPLETATO CON SUCCESSO** ✅
- **Ultima Azione Completata**: Ingestion test di The Village GalaxyRG265 completata con successo con container 1.4.0: entrambi i file (Paso77 e GalaxyRG265) coesistono perfettamente in `/media/movies/The Village (2004) [tmdbid-6947]/`.
- **Prossimo Passo Operativo**: Nessuno.
- **Blocchi/Decisioni Pendenti**: Nessuno. Lavori conclusi.
