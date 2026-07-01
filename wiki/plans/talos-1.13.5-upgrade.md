---
status: archived
certified_for_ai: false
superseded_by: [[kubernetes-upgrade-1.34-1.36]]
---
# Piano Operativo di Upgrade Infrastrutturale: Talos Linux da v1.12.0 a v1.13.5 su Architettura Bare-Metal Proxmox VE

L'aggiornamento di un cluster Kubernetes iperconvergente basato su Talos Linux richiede una pianificazione ingegneristica rigorosa e una comprensione profonda degli strati architetturali sottostanti. Questa necessità è amplificata in scenari in cui i nodi Control Plane ospitano direttamente i workload applicativi, operando con la direttiva `allowSchedulingOnControlPlanes: true`, e gestiscono storage stateful montato su volumi a blocchi aggiuntivi, come nel caso del disco `/dev/sdb` dedicato al mount `/var/mnt/postgres`. 

Il presente documento costituisce il piano operativo definitivo per l'esecuzione della Fase 1, ovvero l'aggiornamento del sistema operativo Talos Linux dalla versione 1.12.0 alla release stabile 1.13.5, garantendo l'assenza di disservizi (zero-downtime), il mantenimento del quorum del datastore distribuito etcd, la preservazione inalterata dei dati sui mount personalizzati e la corretta transizione delle configurazioni di sistema. 

La Fase 2, relativa all'avanzamento di versione del control plane Kubernetes, viene definita a livello architetturale come iterazione successiva.

## 1. Analisi Architetturale delle Breaking Changes e Modifiche al Config Schema

La transizione verso la release 1.13 di Talos Linux introduce alterazioni fondamentali nel motore di configurazione, nelle API di gestione del ciclo di vita e nelle policy di sicurezza del kernel. La mancata assimilazione di queste modifiche strutturali può tradursi in fallimenti di decodifica dei manifest o regressioni operative durante il riavvio dei nodi. L'analisi seguente contestualizza le variazioni critiche introdotte dalla release 1.13.5 rispetto alla topologia e alle configurazioni attualmente in uso.

L'evoluzione più impattante riguarda l'infrastruttura di erogazione degli aggiornamenti, che abbandona le storiche routine in favore della nuova **LifecycleService API**. Questo nuovo strato di orchestrazione espone le operazioni di installazione e aggiornamento tramite un'interfaccia singola e coerente, supportando nativamente il reporting del progresso in tempo reale e operazioni parallele. L'implementazione di questa API rende formalmente deprecate le chiamate di aggiornamento legacy (basate su `MachineService.Upgrade`), portando alla conseguente deprecazione di parametri da riga di comando quali `--force`, `--insecure`, `--preserve` e `--stage`, i quali verranno definitivamente rimossi in Talos 1.18. 
È imperativo notare che, sebbene deprecato a livello di parser CLI per le nuove implementazioni, il flag `--preserve` continua a essere onorato in retrocompatibilità. Nelle architetture moderne di Talos, la preservazione della partizione EPHEMERAL è divenuta il comportamento predefinito durante un aggiornamento di versione, tuttavia, per massima sicurezza procedurale e per rendere esplicito l'intento di non inizializzare i volumi, la direttiva verrà mantenuta nei comandi di questo piano.

Un'ulteriore revisione architetturale che richiede attenzione riguarda il formato serializzato delle configurazioni per i componenti core di Kubernetes. Nello specifico, per le risorse di configurazione avanzata quali `EtcdConfigs`, `KubeletConfigs`, `ControllerManagerConfigs`, `SchedulerConfigs` e `APIServerConfigs`, il formato sottostante in Protobuf è stato modificato da `map<string,string>` a `map<string,message>`. Questa alterazione rappresenta una breaking change formale per gli operatori che generano o iniettano configurazioni tramite tool di templating esterni o manipolazioni raw del JSON/YAML. Sebbene le direttive esistenti definite nel formato `v1alpha1` vengano gestite dal layer di compatibilità di Talos durante la traduzione, qualsiasi automazione GitOps che interagisce direttamente con l'API di configurazione delle macchine dovrà essere allineata al nuovo schema.

Per quanto concerne le feature di sicurezza del nodo, le configurazioni `machine.features.rbac` e `machine.features.apidCheckExtKeyUsage`, attualmente abilitate nel cluster di origine, sono state bloccate in modo rigido al valore `true` a livello di codice sorgente di Talos. Qualora queste chiavi vengano dichiarate esplicitamente nel MachineConfig in tentativi futuri di disabilitazione, il motore di configurazione le ignorerà silenziosamente, garantendo che le policy di autorizzazione basate sui ruoli e i controlli estesi sull'utilizzo delle chiavi crittografiche non possano essere elusi. Allo stesso modo, le ottimizzazioni di rete definite a livello di sistema operativo subiscono una ristrutturazione logica: la storica chiave `machine.sysctls`, precedentemente impiegata per definire parametri come `net.ipv4.tcp_rmem` e `net.core.rmem_max`, è stata dichiarata deprecata in favore del nuovo documento strutturato `SysctlConfig`. I valori preesistenti continueranno a essere applicati durante questa fase di aggiornamento per garantire la continuità del TCP tuning, ma si raccomanda una migrazione della sintassi nel prossimo ciclo di refactoring delle configurazioni.

Un impatto diretto sulla topologia del cluster in esame deriva dalla nuova gestione dei manifest di bootstrap. L'infrastruttura analizzata disabilita il demone CoreDNS nativo (`cluster.coreDNS.disabled: true`) in favore di un'implementazione personalizzata in Alta Affidabilità fornita tramite `inlineManifests`. A partire dalla versione 1.13, Talos ha introdotto l'approccio **inventory-backed server-side apply** per l'applicazione di tali manifesti. Questo meccanismo traccia crittograficamente l'inventario degli oggetti creati nel cluster; se un manifesto inline dovesse essere modificato o rimosso dalla configurazione della macchina in futuro, Talos provvederà al purging automatico delle risorse Kubernetes orfane tramite il comando `talosctl upgrade-k8s`, eliminando la necessità di interventi manuali di pulizia. Il backfill di questo inventario per le risorse già presenti avviene in maniera completamente automatica e trasparente.

Infine, il livello del kernel Linux beneficia di un profondo hardening e di ottimizzazioni di compilazione. Talos 1.13 utilizza un kernel generato tramite il compilatore Clang e ottimizzato con ThinLTO (Link-Time Optimization), una tecnica che riduce i colli di bottiglia nel context-switching e migliora marginalmente le prestazioni computazionali generali. Sul fronte della sicurezza attiva, il parametro kernel `proc_mem.force_override=never` è ora abilitato di default, impedendo scritture non autorizzate nella memoria dei processi protetti attraverso il filesystem virtuale `/proc/PID/mem`, un vettore comunemente sfruttato per iniezioni di codice nocivo.

| Categoria di Modifica | Stato in Talos v1.12.0 | Implementazione in Talos v1.13.5 | Impatto Diretto e Note Operative |
| :--- | :--- | :--- | :--- |
| **API di Upgrade** | `MachineService.Upgrade` con gestione flag manuale. | `LifecycleService.Upgrade` con streaming log nativo. | Flag come `--preserve` sono deprecati ma onorati. Preservazione dati garantita. |
| **Formato Configurazione** | `map<string,string>` per extraArgs di etcd/kubelet. | `map<string,message>` per i medesimi componenti. | Breaking change per tool esterni; il layer di compatibilità gestisce la sintassi YAML esistente. |
| **Inline Manifests** | Client-side apply convenzionale (sovrascrittura). | Inventory-backed Server-Side Apply. | Gestione automatizzata del ciclo di vita per il CoreDNS custom; nessuna azione richiesta. |
| **Feature Security Flags** | `rbac` e `apidCheckExtKeyUsage` opzionali. | Hardcoded a `true` a livello di sistema. | I tentativi di disabilitazione futuri nel file di configurazione verranno ignorati. |
| **Kernel Sysctls** | Gestiti tramite chiave `.machine.sysctls`. | Deprecati in favore del documento `SysctlConfig`. | Le ottimizzazioni TCP (es. `net.core.rmem_max`) restano attive, ma necessitano futura migrazione sintattica. |

## 2. Allineamento e Upgrade dei Client di Gestione su macOS

L'interazione con l'API di Talos e con il Control Plane di Kubernetes presuppone una stretta sincronizzazione crittografica e di versione tra i binari client eseguiti sulla workstation dell'operatore e i demoni residenti sui nodi. L'aggiornamento dei client su macOS deve precedere categoricamente qualsiasi operazione sul cluster.

Talos applica una policy di tolleranza ristretta per le discordanze di versione tra il client `talosctl` e il server; è fortemente raccomandato che la versione del client corrisponda esattamente alla versione del sistema operativo target (v1.13.5). Parallelamente, lo strumento `kubectl` deve conformarsi alla policy ufficiale di Kubernetes che ammette un disallineamento massimo di una versione minore (skew policy).

```bash
# 1. Aggiornamento degli indici dei repository locali di Homebrew
brew update

# 2. Upgrade del client Talos tramite il tap ufficiale di Sidero Labs.
brew upgrade siderolabs/tap/talosctl

# 3. Upgrade del client Kubernetes per il controllo del cluster
brew upgrade kubernetes-cli

# 4. Validazione tassativa delle versioni installate
talosctl version --client
kubectl version --client --output=yaml
```

Solo al raggiungimento della certezza crittografica che i binari locali siano stati elevati alle versioni richieste, sarà possibile stabilire il canale di comunicazione mTLS con il Virtual IP dell'API Server (`10.10.20.55`) o con i singoli IP dei nodi di Control Plane.

## 3. FASE 1 - Esecuzione Tecnica dell'Upgrade di Talos OS

### 3.1. Sintesi dell'Immagine Installer tramite Talos Image Factory

Poiché il cluster risiede su un hypervisor Proxmox VE (basato su KVM/QEMU), è imperativo includere il pacchetto `siderolabs/qemu-guest-agent` all'interno dell'immagine del sistema operativo. I moduli aggiuntivi per il networking storage NVMe (`nvme-tcp`, `nvme-fabrics`) sono inclusi nativamente nei pacchetti kernel standard di Talos.

La generazione dell'immagine installer per la versione target v1.13.5 richiede la creazione di uno Schematic e la sua sottomissione alle API della Talos Image Factory.

```bash
# Definizione della struttura dello Schematic
cat > qemu-schematic.yaml << 'EOF'
customization:
  systemExtensions:
    officialExtensions:
      - siderolabs/qemu-guest-agent
EOF

# Sottomissione alle API della Factory e parsing dello Schematic ID
SCHEMATIC_ID=$(curl -sX POST \
  --data-binary @qemu-schematic.yaml \
  https://factory.talos.dev/schematics \
  -H "Content-Type: application/yaml" | jq -r .id)

# Esposizione dell'URL dell'immagine risultante
echo "L'URL dell'immagine installer per il cluster è:"
echo "factory.talos.dev/installer/${SCHEMATIC_ID}:v1.13.5"
```
> **Nota Operativa (ID Generato)**: Lo Schematic ID registrato in data odierna per `qemu-guest-agent` è:
> `ce4c980550dd2ab1b17bbf2b08801c7eb59418eafe8f279833297925d67c7515`
> URL Immagine Definitivo: `factory.talos.dev/installer/ce4c980550dd2ab1b17bbf2b08801c7eb59418eafe8f279833297925d67c7515:v1.13.5`

L'URL generato sostituirà l'immagine preesistente.

### 3.2. Controlli Diagnostici Pre-Rollout (Pre-flight Checks)

Prima di instradare il comando di spegnimento a qualsivoglia nodo, è matematicamente necessario validare la sanità dei datastore e l'instradamento di rete. I seguenti comandi diagnostici devono essere eseguiti e convalidati contro uno dei nodi (es. `10.10.20.141`).

| Obiettivo Diagnostico | Comando Operativo | Criterio di Validazione |
| :--- | :--- | :--- |
| **Allineamento Nodi K8s** | `kubectl get nodes -o wide` | I tre nodi (`talos-cp-01`, 02, 03) devono riportare lo status `Ready`. |
| **Sanità Workloads** | `kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded` | L'output deve risultare vuoto, a garanzia dell'assenza di pod in stato di blocco o `CrashLoopBackOff`. |
| **Quorum etcd** | `talosctl -n 10.10.20.141 etcd members` | La lista deve comprendere esattamente 3 membri con lo status "Started". |
| **Allarmi etcd** | `talosctl -n 10.10.20.141 etcd alarm list` | L'output deve essere vuoto. |
| **Backup etcd** | `talosctl -n 10.10.20.141 etcd snapshot etcd-backup-pre-upgrade.db` | Generazione avvenuta con successo del file binario locale. |
| **Routing KubePrism** | `talosctl -n 10.10.20.141 get endpoints` | Il bilanciatore locale TCP sulla porta 7445 deve mostrare connessioni stabili. |
| **Replicazione CNPG** | `kubectl cnpg status <nome-cluster-pg> -n <namespace>` | Il referto deve attestare esplicitamente "Cluster in healthy state". |

### 3.3. Procedura di Rolling Upgrade e Gestione dello Storage

Il comando `talosctl upgrade` scarica il nuovo OS, espelle i workload, invia lo spegnimento pulito a tutti i demoni (assicurando il flush dei dati di PostgreSQL sul disco `/dev/sdb`) e riavvia la macchina tramite kexec. La direttiva esplicita `--preserve=true` garantisce che la partizione EPHEMERAL e il volume aggiunto in configurazione tramite custom mount (`/dev/sdb` su `/var/mnt/postgres`) non vengano intaccati.

L'aggiornamento deve procedere nodo per nodo, attendendo la convergenza totale del cluster prima di passare alla macchina successiva.

#### Fase Operativa: Nodo 1 (talos-cp-01 - 10.10.20.141)
```bash
# Avvio dell'aggiornamento OS sul primo nodo
talosctl upgrade --nodes 10.10.20.141 \
                 --image factory.talos.dev/installer/${SCHEMATIC_ID}:v1.13.5 \
                 --preserve=true
```
Attendere circa 3-5 minuti. Prima di procedere, eseguire i **Controlli di Verifica Post-Upgrade**:
```bash
# 1. Conferma dell'aggiornamento OS
talosctl -n 10.10.20.141 version

# 2. Reinserimento del nodo nel pool di schedulazione
kubectl get nodes 10.10.20.141 -o wide

# 3. Convergenza del Quorum etcd
talosctl -n 10.10.20.142 etcd members

# 4. Integrità del Custom Mount per PostgreSQL
talosctl -n 10.10.20.141 get mounts | grep postgres

# 5. Stabilizzazione del Database Stateful
kubectl cnpg status postgres-main -n cnpg-system
```
*L'operatore NON DEVE PROSEGUIRE fino a che l'output di CNPG non indichi fermamente "Cluster in healthy state".*

#### Fase Operativa: Nodo 2 (talos-cp-02 - 10.10.20.142)
Accertata la convergenza, la procedura viene reiterata sul secondo asse.
```bash
# Avvio dell'aggiornamento OS sul secondo nodo
talosctl upgrade --nodes 10.10.20.142 \
                 --image factory.talos.dev/installer/${SCHEMATIC_ID}:v1.13.5 \
                 --preserve=true
```
Applicare lo stesso ciclo di validazione Post-Upgrade descritto per il Nodo 1.

#### Fase Operativa: Nodo 3 (talos-cp-03 - 10.10.20.143)
```bash
# Avvio dell'aggiornamento OS sul terzo nodo
talosctl upgrade --nodes 10.10.20.143 \
                 --image factory.talos.dev/installer/${SCHEMATIC_ID}:v1.13.5 \
                 --preserve=true
```
Conclusi i controlli Post-Upgrade anche sul terzo nodo, si effettua una validazione globale finale interrogando l'API VIP (`10.10.20.55`) o i singoli nodi.

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: FASE 2 - Upgrade Kubernetes (Pianificazione)
- **Ultima Azione Completata**: Upgrade Talos OS v1.13.5 completato su tutti e 3 i nodi e validazione globale superata con successo (incluso backup Velero `post-talos-upgrade-2026-07-01-0013`).
- **Prossimo Passo Operativo**: Ottenere il piano da Gemini DeepSearch per la Fase 2 (K8s v1.34.1 -> v1.36.2) e materializzarlo.
- **Blocchi/Decisioni Pendenti**: In attesa dei risultati di Gemini DeepSearch.
